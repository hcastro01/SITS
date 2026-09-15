"""Análisis puro de la plantilla canónica de ausentismos.

La lectura de un archivo XLSX, el almacenamiento del lote y la confirmación transaccional
pertenecen a bloques posteriores. Este servicio recibe la tabla ya extraída para que las
reglas del contrato sean verificables de forma independiente al lector de archivos.
"""

from datetime import date, datetime
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, authorize
from app.models import Ausentismo, Persona
from app.schemas.ausentismos import AusentismoAnalisis, AusentismoFilaAnalizada

IMPORT_MODULE = "IMPORTACION"
AUSENTISMO_MODULE = "AUSENTISMO"
REQUIRED_HEADERS = ("cedula", "fecha_inicio", "fecha_fin", "tipo_ausentismo", "motivo")
OPTIONAL_HEADERS = ("observacion",)
ALLOWED_HEADERS = frozenset((*REQUIRED_HEADERS, *OPTIONAL_HEADERS))


def _normalizar_encabezados(encabezados: Sequence[Any]) -> tuple[str, ...]:
    normalized = tuple(str(value).strip() if value is not None else "" for value in encabezados)
    duplicates = sorted({value for value in normalized if normalized.count(value) > 1})
    unknown = sorted(set(normalized) - ALLOWED_HEADERS)
    missing = [value for value in REQUIRED_HEADERS if value not in normalized]
    if duplicates or unknown or missing:
        details = []
        if missing:
            details.append(f"faltan: {', '.join(missing)}")
        if unknown:
            details.append(f"no admitidos: {', '.join(unknown)}")
        if duplicates:
            details.append(f"duplicados: {', '.join(duplicates)}")
        raise AppError("INVALID_IMPORT_HEADERS", f"Encabezados de Ausentismo inválidos ({'; '.join(details)}).", 422)
    return normalized


def _texto(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _fecha(value: Any) -> tuple[str | None, str | None]:
    if isinstance(value, datetime):
        return value.date().isoformat(), None
    if isinstance(value, date):
        return value.isoformat(), None
    text = _texto(value)
    if text is None:
        return None, "La fecha es obligatoria."
    try:
        return date.fromisoformat(text).isoformat(), None
    except ValueError:
        return None, "La fecha debe ser válida y estar en formato ISO (YYYY-MM-DD)."


def _filas_existentes(session: Session) -> set[tuple[str, str, str, str]]:
    return set(session.execute(
        select(Ausentismo.persona_id, Ausentismo.fecha_inicio, Ausentismo.fecha_fin, Ausentismo.tipo_ausentismo)
    ).tuples())


def analizar_importacion_ausentismos(
    session: Session,
    user: AuthenticatedUser,
    *,
    encabezados: Sequence[Any],
    filas: Sequence[Sequence[Any]],
) -> AusentismoAnalisis:
    """Valida y previsualiza un lote sin persistirlo.

    Una confirmación posterior debe exigir ``puede_confirmarse`` y repetir la evaluación
    dentro de su transacción para evitar carreras entre análisis y persistencia.
    """
    authorize(user, IMPORT_MODULE, "create")
    authorize(user, AUSENTISMO_MODULE, "create")
    canonical_headers = _normalizar_encabezados(encabezados)
    index = {header: position for position, header in enumerate(canonical_headers)}
    existing_keys = _filas_existentes(session)
    batch_keys: set[tuple[str, str, str, str]] = set()
    result: list[AusentismoFilaAnalizada] = []

    for row_number, source_row in enumerate(filas, start=2):
        values = {header: source_row[position] if position < len(source_row) else None for header, position in index.items()}
        errors: list[str] = []
        raw_cedula = values["cedula"]
        cedula = _texto(raw_cedula)
        tipo = _texto(values["tipo_ausentismo"])
        motivo = _texto(values["motivo"])
        observacion = _texto(values.get("observacion"))
        inicio, inicio_error = _fecha(values["fecha_inicio"])
        fin, fin_error = _fecha(values["fecha_fin"])
        persona_id = None

        if cedula is None:
            errors.append("La cédula es obligatoria.")
        elif not isinstance(raw_cedula, str):
            errors.append("La cédula debe estar almacenada como texto para conservar ceros iniciales.")
        else:
            people = session.scalars(
                select(Persona).where(Persona.cedula == cedula, Persona.activo.is_(True), Persona.eliminado.is_(False))
            ).all()
            if not people:
                errors.append("No existe una Persona activa para la cédula indicada.")
            elif len(people) > 1:
                errors.append("La cédula corresponde a más de una Persona activa.")
            else:
                persona_id = people[0].id_persona
        if inicio_error:
            errors.append(f"fecha_inicio: {inicio_error}")
        if fin_error:
            errors.append(f"fecha_fin: {fin_error}")
        if inicio and fin and fin < inicio:
            errors.append("fecha_fin no puede ser anterior a fecha_inicio.")
        if tipo is None:
            errors.append("tipo_ausentismo es obligatorio.")
        if motivo is None:
            errors.append("motivo es obligatorio.")

        state: str = "ERROR"
        if not errors:
            key = (persona_id, inicio, fin, tipo)
            if key in existing_keys or key in batch_keys:
                state = "DUPLICADA"
            else:
                state = "VALIDA"
            batch_keys.add(key)
        result.append(AusentismoFilaAnalizada(
            fila=row_number, cedula=cedula, persona_id=persona_id, fecha_inicio=inicio, fecha_fin=fin,
            tipo_ausentismo=tipo, motivo=motivo, observacion=observacion, estado=state, errores=tuple(errors),
        ))

    valid = sum(row.estado == "VALIDA" for row in result)
    duplicates = sum(row.estado == "DUPLICADA" for row in result)
    invalid = sum(row.estado == "ERROR" for row in result)
    return AusentismoAnalisis(
        encabezados=canonical_headers, total_filas=len(result), filas_validas=valid,
        filas_duplicadas=duplicates, filas_con_error=invalid,
        puede_confirmarse=not invalid and not duplicates, filas=tuple(result),
    )
