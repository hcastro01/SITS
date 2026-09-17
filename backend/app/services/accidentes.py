"""Accidentes: registros manuales e importación XLSX con confirmación atómica."""
import json
from datetime import date, datetime
from typing import Any, Sequence
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, authorize
from app.models import Accidente, ErrorImportacionAccidente, LoteImportacionAccidente, Persona, User
from app.services.audit import log_change
from app.services.importaciones_ausentismos import leer_xlsx
from app.services.records import check_expected_version, creation_metadata, get_active, mark_updated

MODULE = "ACCIDENTES"
IMPORT_MODULE = "IMPORTACION"
ESTADOS = {"ABIERTO", "EN_SEGUIMIENTO", "CERRADO"}
REQUIRED_HEADERS = ("cedula", "fecha_accidente", "clasificacion", "descripcion")
OPTIONAL_HEADERS = ("estado", "observacion")
ALLOWED_HEADERS = frozenset((*REQUIRED_HEADERS, *OPTIONAL_HEADERS))


def _text(value: Any) -> str | None:
    value = None if value is None else str(value).strip()
    return value or None


def _date(value: Any) -> tuple[str | None, str | None]:
    if isinstance(value, datetime): return value.date().isoformat(), None
    if isinstance(value, date): return value.isoformat(), None
    value = _text(value)
    if not value: return None, "La fecha del accidente es obligatoria."
    try: return date.fromisoformat(value).isoformat(), None
    except ValueError: return None, "La fecha debe tener formato ISO (YYYY-MM-DD)."


def _headers(headers: Sequence[Any]) -> tuple[str, ...]:
    normalized = tuple(str(value).strip() if value is not None else "" for value in headers)
    missing = [value for value in REQUIRED_HEADERS if value not in normalized]
    unknown = sorted(set(normalized) - ALLOWED_HEADERS)
    duplicates = sorted({value for value in normalized if normalized.count(value) > 1})
    if missing or unknown or duplicates:
        details = ([] if not missing else [f"faltan: {', '.join(missing)}"]) + ([] if not unknown else [f"no admitidos: {', '.join(unknown)}"]) + ([] if not duplicates else [f"duplicados: {', '.join(duplicates)}"])
        raise AppError("INVALID_IMPORT_HEADERS", f"Encabezados de Accidentes inválidos ({'; '.join(details)}).", 422)
    return normalized


def analyze(session: Session, user: AuthenticatedUser, headers: Sequence[Any], rows: Sequence[Sequence[Any]]) -> dict:
    authorize(user, IMPORT_MODULE, "create"); authorize(user, MODULE, "create")
    headers = _headers(headers); positions = {name: index for index, name in enumerate(headers)}
    existing = set(session.execute(select(Accidente.persona_id, Accidente.fecha_accidente, Accidente.clasificacion)).tuples())
    batch: set[tuple[str, str, str]] = set(); result = []
    for number, source in enumerate(rows, start=2):
        values = {name: source[index] if index < len(source) else None for name, index in positions.items()}
        raw_cedula = values["cedula"]; cedula = _text(raw_cedula); fecha, date_error = _date(values["fecha_accidente"])
        clasificacion = _text(values["clasificacion"]); descripcion = _text(values["descripcion"]); estado = _text(values.get("estado")) or "ABIERTO"; observacion = _text(values.get("observacion")); errors = []; persona_id = None
        if not cedula: errors.append("La cédula es obligatoria.")
        elif not isinstance(raw_cedula, str): errors.append("La cédula debe estar almacenada como texto para conservar ceros iniciales.")
        else:
            people = session.scalars(select(Persona).where(Persona.cedula == cedula, Persona.activo.is_(True), Persona.eliminado.is_(False))).all()
            if len(people) != 1: errors.append("No existe una Persona activa única para la cédula indicada.")
            else: persona_id = people[0].id_persona
        if date_error: errors.append(date_error)
        if not clasificacion: errors.append("La clasificación es obligatoria.")
        if not descripcion: errors.append("La descripción es obligatoria.")
        if estado not in ESTADOS: errors.append("El estado no es válido.")
        record_state = "ERROR"
        if not errors:
            key = (persona_id, fecha, clasificacion); record_state = "DUPLICADA" if key in existing or key in batch else "VALIDA"; batch.add(key)
        result.append({"fila": number, "cedula": cedula, "persona_id": persona_id, "fecha_accidente": fecha, "clasificacion": clasificacion, "estado_accidente": estado, "descripcion": descripcion, "observacion": observacion, "estado": record_state, "errores": errors})
    valid = sum(row["estado"] == "VALIDA" for row in result); duplicates = sum(row["estado"] == "DUPLICADA" for row in result)
    return {"total_filas": len(result), "filas_validas": valid, "filas_duplicadas": duplicates, "filas_con_error": len(result) - valid - duplicates, "puede_confirmarse": not (len(result) - valid), "filas": result}


def _lot_snapshot(lot): return {key: getattr(lot, key) for key in ("nombre_archivo", "estado", "total_filas", "filas_validas", "filas_con_error", "filas_duplicadas", "filas_importadas")}


def analyze_file(session: Session, user: AuthenticatedUser, *, name: str, content: bytes, correlation_id: str):
    authorize(user, IMPORT_MODULE, "create"); authorize(user, MODULE, "create")
    if not name.lower().endswith(".xlsx"): raise AppError("INVALID_XLSX", "El archivo debe tener extensión .xlsx.", 422)
    headers, rows = leer_xlsx(content); analysis = analyze(session, user, headers, rows)
    lot = LoteImportacionAccidente(id_lote=str(uuid4()), nombre_archivo=name, contenido_archivo=content, usuario_id=user.id_usuario, estado="ANALIZADO", filas_importadas=0, **creation_metadata(user.correo))
    for key in ("total_filas", "filas_validas", "filas_con_error", "filas_duplicadas"): setattr(lot, key, analysis[key])
    session.add(lot); session.flush()
    for row in analysis["filas"]:
        if row["estado"] != "VALIDA":
            session.add(ErrorImportacionAccidente(id_error=str(uuid4()), lote_id=lot.id_lote, numero_fila=row["fila"], codigo="DUPLICADO" if row["estado"] == "DUPLICADA" else "VALIDACION", mensaje="Registro duplicado según persona, fecha y clasificación." if row["estado"] == "DUPLICADA" else " ".join(row["errores"]), datos_fila=json.dumps({"cedula": row["cedula"][-4:].rjust(len(row["cedula"]), "*") if row["cedula"] else None, "fecha_accidente": row["fecha_accidente"], "clasificacion": row["clasificacion"]}, ensure_ascii=False), **creation_metadata(user.correo)))
    log_change(session, "lotes_importacion_accidente", lot.id_lote, "IMPORT", {}, _lot_snapshot(lot), user.correo, "Análisis de archivo XLSX", correlation_id)
    return lot, analysis


def confirm_lot(session: Session, user: AuthenticatedUser, lot_id: str, *, correlation_id: str):
    authorize(user, IMPORT_MODULE, "create"); authorize(user, MODULE, "create")
    lot = get_active(session, LoteImportacionAccidente, lot_id, LoteImportacionAccidente.id_lote)
    if lot.estado == "CONFIRMADO": raise AppError("IMPORT_ALREADY_CONFIRMED", "El lote ya fue confirmado.", 409)
    headers, rows = leer_xlsx(lot.contenido_archivo); analysis = analyze(session, user, headers, rows)
    if not analysis["puede_confirmarse"]: raise AppError("IMPORT_NOT_CONFIRMABLE", "El lote tiene errores o duplicados y no puede confirmarse.", 422)
    before = _lot_snapshot(lot)
    try:
        with session.begin_nested():
            for row in analysis["filas"]:
                session.add(Accidente(id_accidente=str(uuid4()), persona_id=row["persona_id"], lote_id=lot.id_lote, fecha_accidente=row["fecha_accidente"], clasificacion=row["clasificacion"], estado=row["estado_accidente"], descripcion=row["descripcion"], observacion=row["observacion"], archivo_fuente=lot.nombre_archivo, registro_fuente=str(row["fila"]), fecha_importacion=lot.fecha_creacion, usuario_importacion=user.correo, **creation_metadata(user.correo)))
            session.flush()
    except IntegrityError as exc: raise AppError("IMPORT_PERSISTENCE_FAILED", "No fue posible confirmar el lote; no se importó ninguna fila.", 409) from exc
    lot.estado = "CONFIRMADO"; lot.filas_importadas = analysis["filas_validas"]; mark_updated(lot, user.correo)
    log_change(session, "lotes_importacion_accidente", lot.id_lote, "IMPORT", before, _lot_snapshot(lot), user.correo, "Confirmación de importación XLSX", correlation_id); return lot


def create(session: Session, user: AuthenticatedUser, *, persona_id: str, fecha_accidente: str, clasificacion: str, descripcion: str, estado: str = "ABIERTO", observacion: str | None = None, correlation_id: str):
    authorize(user, MODULE, "create"); fecha, error = _date(fecha_accidente)
    if error or not session.get(Persona, persona_id): raise AppError("PERSON_NOT_FOUND" if not error else "INVALID_DATE", "La persona no existe." if not error else error, 422)
    if not _text(clasificacion) or not _text(descripcion) or estado not in ESTADOS: raise AppError("INVALID_INPUT", "Clasificación, descripción y estado son obligatorios y válidos.", 422)
    record = Accidente(id_accidente=str(uuid4()), persona_id=persona_id, fecha_accidente=fecha, clasificacion=clasificacion.strip(), descripcion=descripcion.strip(), estado=estado, observacion=_text(observacion), **creation_metadata(user.correo)); session.add(record); session.flush(); log_change(session, "accidentes", record.id_accidente, "CREATE", {}, {"persona_id": persona_id, "fecha_accidente": fecha, "clasificacion": clasificacion, "estado": estado}, user.correo, "Creación manual de accidente", correlation_id); return record


def update(session: Session, user: AuthenticatedUser, record_id: str, *, expected_version: int, correlation_id: str, **fields):
    authorize(user, MODULE, "edit")
    allowed = {"clasificacion", "estado", "descripcion", "observacion"}
    if not fields or set(fields) - allowed or ("estado" in fields and fields["estado"] not in ESTADOS) or any(not _text(fields[key]) for key in ("clasificacion", "descripcion") if key in fields):
        raise AppError("INVALID_INPUT", "Los campos de edición no son válidos.", 422)
    record = get_active(session, Accidente, record_id, Accidente.id_accidente); check_expected_version(record, expected_version)
    before = {key: getattr(record, key) for key in allowed}
    for key, value in fields.items(): setattr(record, key, _text(value) if key == "observacion" else value.strip() if isinstance(value, str) else value)
    mark_updated(record, user.correo); log_change(session, "accidentes", record.id_accidente, "UPDATE", before, {key: getattr(record, key) for key in allowed}, user.correo, "Edición de accidente", correlation_id); return record


def list_records(session: Session, user: AuthenticatedUser, *, nombre=None, cedula=None, clasificacion=None, estado=None, desde=None, hasta=None, origen=None, lote_id=None, limit=25, offset=0):
    authorize(user, MODULE, "read"); stmt = select(Accidente, Persona, LoteImportacionAccidente, User).join(Persona, Accidente.persona_id == Persona.id_persona).outerjoin(LoteImportacionAccidente, Accidente.lote_id == LoteImportacionAccidente.id_lote).outerjoin(User, LoteImportacionAccidente.usuario_id == User.id_usuario).where(Accidente.eliminado.is_(False))
    if nombre: stmt = stmt.where(Persona.nombre.ilike(f"%{nombre.strip()}%"))
    if cedula: stmt = stmt.where(Persona.cedula == cedula.strip())
    if clasificacion: stmt = stmt.where(Accidente.clasificacion == clasificacion.strip())
    if estado: stmt = stmt.where(Accidente.estado == estado.strip())
    if desde: stmt = stmt.where(Accidente.fecha_accidente >= desde)
    if hasta: stmt = stmt.where(Accidente.fecha_accidente <= hasta)
    if origen == "IMPORTACION_XLSX": stmt = stmt.where(Accidente.lote_id.is_not(None))
    elif origen: raise AppError("INVALID_ORIGIN", "El origen solicitado no está disponible.", 422)
    if lote_id: stmt = stmt.where(Accidente.lote_id == lote_id)
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    return session.execute(stmt.order_by(Accidente.fecha_accidente.desc(), Accidente.id_accidente.desc()).offset(offset).limit(limit)).all(), total


def get_record(session: Session, user: AuthenticatedUser, record_id: str):
    authorize(user, MODULE, "read"); row = session.execute(select(Accidente, Persona, LoteImportacionAccidente, User).join(Persona, Accidente.persona_id == Persona.id_persona).outerjoin(LoteImportacionAccidente, Accidente.lote_id == LoteImportacionAccidente.id_lote).outerjoin(User, LoteImportacionAccidente.usuario_id == User.id_usuario).where(Accidente.id_accidente == record_id, Accidente.eliminado.is_(False))).first()
    if not row: raise AppError("NOT_FOUND", "Registro no encontrado.", 404)
    return row


def lots(session, user, *, limit, offset):
    authorize(user, IMPORT_MODULE, "read"); authorize(user, MODULE, "read"); stmt = select(LoteImportacionAccidente).where(LoteImportacionAccidente.eliminado.is_(False)); return session.scalars(stmt.order_by(LoteImportacionAccidente.fecha_creacion.desc()).offset(offset).limit(limit)).all(), session.scalar(select(func.count()).select_from(stmt.subquery())) or 0


def lot(session, user, lot_id): authorize(user, IMPORT_MODULE, "read"); authorize(user, MODULE, "read"); return get_active(session, LoteImportacionAccidente, lot_id, LoteImportacionAccidente.id_lote)
def issues(session, user, lot_id, *, limit, offset):
    lot(session, user, lot_id); stmt = select(ErrorImportacionAccidente).where(ErrorImportacionAccidente.lote_id == lot_id, ErrorImportacionAccidente.eliminado.is_(False)); return session.scalars(stmt.order_by(ErrorImportacionAccidente.numero_fila).offset(offset).limit(limit)).all(), session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
