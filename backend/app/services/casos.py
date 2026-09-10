"""Servicio de Casos y sus hijos (Config.gs:57,58,62,63,64,65 — Fase 1 §4 líneas 91-99).

El cierre actualiza el caso padre y escribe auditoría en la misma transacción de
SQLAlchemy — el flujo crítico que Base Sistema/CaseService.gs:150-151 no podía garantizar
de forma atómica (MIGRACION_FASE_1.md discrepancia D9).
"""

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.time import ecuador_now, utc_now_iso
from app.core.permissions import AuthenticatedUser, authorize
from app.models import Caso, Catalogo, Cierre, Compromiso, Derivacion, Seguimiento
from app.services.audit import log_change
from app.services.records import (
    apply_soft_delete, bump_for_update, check_expected_version, creation_metadata, get_active, mark_updated,
)

CASOS_MODULE = "CASOS"

# H1: allowlist de negocio. codigo_caso lo asigna el servicio; los campos META nunca
# llegan desde el llamador (Base Sistema/ValidationService.gs:28 sí lo permitía).
CAMPOS_CASO = (
    "fecha_apertura", "id_persona", "colaborador", "responsable", "tipo_caso", "subtipo_caso",
    "prioridad", "nivel_sensibilidad", "estado_caso", "tipo_gestion", "tipo_evento", "area",
    "turno", "condicion_laboral", "restriccion", "fecha_inicio_restriccion", "fecha_cierre",
    "motivo_cierre", "resultado", "evidencias",
)
CAMPOS_SEGUIMIENTO = (
    "fecha", "hora", "responsable", "tipo_seguimiento", "canal", "tecnica", "descripcion",
    "resultado", "proxima_accion", "fecha_proxima_accion", "estado", "evidencias",
)
CAMPOS_DERIVACION = (
    "fecha", "area_destino", "responsable_destino", "motivo", "estado", "fecha_respuesta",
    "resultado", "fecha_cierre", "observaciones",
)
CAMPOS_COMPROMISO = (
    "id_seguimiento", "fecha_creacion_compromiso", "responsable", "descripcion", "fecha_limite",
    "estado", "fecha_cumplimiento", "evidencia", "observacion",
)
CAMPOS_CIERRE = (
    "fecha_cierre_caso", "responsable", "motivo_cierre", "resultado_final", "evidencia",
    "requiere_monitoreo", "observacion",
)


def _rechazar_desconocidos(campos: dict, permitidos: tuple[str, ...]) -> None:
    desconocidos = set(campos) - set(permitidos)
    if desconocidos:
        raise AppError("INVALID_FIELD", f"Campos no admitidos: {', '.join(sorted(desconocidos))}.", 422)


def _generar_codigo_caso() -> str:
    """Equivalente a Base Sistema/CaseService.gs:2-5 (caseCode)."""
    year = ecuador_now().year
    return f"CAS-{year}-{uuid4().hex[:10].upper()}"


def sensitive_case_values(session: Session) -> set[str]:
    """Carga una sola vez los códigos/valores marcados como sensibles."""
    rows = session.scalars(
        select(Catalogo).where(
            Catalogo.tipo == "NIVEL_SENSIBILIDAD",
            Catalogo.es_sensible.is_(True),
            Catalogo.eliminado.is_(False),
        )
    )
    return {
        str(value).strip().upper()
        for row in rows
        for value in (row.codigo, row.valor)
        if value and str(value).strip()
    }


def is_sensitive_caso(
    session: Session, nivel_sensibilidad: str | None, *, sensitive_values: set[str] | None = None,
) -> bool:
    """Equivalente a TSAuth.isSensitiveCase (AuthService.gs:60-71).

    Devuelve False mientras NIVEL_SENSIBILIDAD no tenga valores sembrados (hallazgo H2):
    el mecanismo queda listo pero inactivo, igual que en el legacy — aquí documentado en
    vez de silencioso.
    """
    if not nivel_sensibilidad:
        return False
    normalizado = nivel_sensibilidad.strip().upper()
    values = sensitive_values if sensitive_values is not None else sensitive_case_values(session)
    return normalizado in values


def _snapshot(record, campos) -> dict:
    return {campo: getattr(record, campo) for campo in campos}


def create_caso(session: Session, user: AuthenticatedUser, *, motivo_auditoria: str,
                 correlation_id: str, **campos) -> Caso:
    _rechazar_desconocidos(campos, CAMPOS_CASO)
    sensible = is_sensitive_caso(session, campos.get("nivel_sensibilidad"))
    authorize(user, CASOS_MODULE, "create", sensitive=sensible)
    record = Caso(id_caso=str(uuid4()), codigo_caso=_generar_codigo_caso(),
                  **creation_metadata(user.correo), **campos)
    session.add(record)
    session.flush()
    log_change(session, "casos", record.id_caso, "CREATE", {}, _snapshot(record, CAMPOS_CASO),
               user.correo, motivo_auditoria, correlation_id, sensitive_record=sensible)
    return record


def update_caso(session: Session, user: AuthenticatedUser, id_caso: str, *,
                 expected_version: int | None, motivo_auditoria: str, correlation_id: str, **campos) -> Caso:
    _rechazar_desconocidos(campos, CAMPOS_CASO)
    record = get_active(session, Caso, id_caso, Caso.id_caso)
    sensible_antes = is_sensitive_caso(session, record.nivel_sensibilidad)
    sensible_despues = is_sensitive_caso(session, campos.get("nivel_sensibilidad", record.nivel_sensibilidad))
    authorize(user, CASOS_MODULE, "edit", sensitive=sensible_antes or sensible_despues)
    before = _snapshot(record, CAMPOS_CASO)
    bump_for_update(record, user.correo, expected_version, **campos)
    log_change(session, "casos", id_caso, "UPDATE", before, _snapshot(record, CAMPOS_CASO),
               user.correo, motivo_auditoria, correlation_id, sensitive_record=sensible_despues)
    return record


def soft_delete_caso(session: Session, user: AuthenticatedUser, id_caso: str, *,
                      expected_version: int | None, motivo: str, correlation_id: str) -> Caso:
    record = get_active(session, Caso, id_caso, Caso.id_caso)
    sensible = is_sensitive_caso(session, record.nivel_sensibilidad)
    authorize(user, CASOS_MODULE, "delete", sensitive=sensible)
    check_expected_version(record, expected_version)
    before = _snapshot(record, CAMPOS_CASO)
    apply_soft_delete(record, user.correo, motivo)  # valida el motivo antes de tocar version
    mark_updated(record, user.correo)
    log_change(session, "casos", id_caso, "DELETE", before, _snapshot(record, CAMPOS_CASO),
               user.correo, motivo, correlation_id, sensitive_record=sensible)
    return record


def _ensure_caso_editable(session: Session, user: AuthenticatedUser, id_caso: str) -> tuple[Caso, bool]:
    """Equivalente a CaseService.gs:67-72 (ensureCase)."""
    caso = get_active(session, Caso, id_caso, Caso.id_caso)
    sensible = is_sensitive_caso(session, caso.nivel_sensibilidad)
    authorize(user, CASOS_MODULE, "edit", sensitive=sensible)
    return caso, sensible


def list_seguimientos(session: Session, user: AuthenticatedUser, id_caso: str) -> list[Seguimiento]:
    caso = get_active(session, Caso, id_caso, Caso.id_caso)
    sensible = is_sensitive_caso(session, caso.nivel_sensibilidad)
    authorize(user, CASOS_MODULE, "read", sensitive=sensible)
    authorize(user, "SEGUIMIENTOS", "read", sensitive=sensible)
    return list(session.scalars(
        select(Seguimiento).where(
            Seguimiento.id_caso == id_caso, Seguimiento.eliminado.is_(False),
        ).order_by(Seguimiento.fecha.desc(), Seguimiento.fecha_creacion.desc())
    ))


def list_compromisos(session: Session, user: AuthenticatedUser, id_caso: str) -> list[Compromiso]:
    caso = get_active(session, Caso, id_caso, Caso.id_caso)
    sensible = is_sensitive_caso(session, caso.nivel_sensibilidad)
    authorize(user, CASOS_MODULE, "read", sensitive=sensible)
    authorize(user, "COMPROMISOS", "read", sensitive=sensible)
    return list(session.scalars(
        select(Compromiso).where(
            Compromiso.id_caso == id_caso, Compromiso.eliminado.is_(False),
        ).order_by(Compromiso.fecha_limite.asc(), Compromiso.fecha_creacion.desc())
    ))


def add_seguimiento(session: Session, user: AuthenticatedUser, id_caso: str, *,
                     correlation_id: str, motivo_auditoria: str = "Seguimiento", **campos) -> Seguimiento:
    _rechazar_desconocidos(campos, CAMPOS_SEGUIMIENTO)
    caso, sensible = _ensure_caso_editable(session, user, id_caso)
    authorize(user, "SEGUIMIENTOS", "create", sensitive=sensible)
    seguimiento = Seguimiento(id_seguimiento=str(uuid4()), id_caso=id_caso,
                               **creation_metadata(user.correo), **campos)
    session.add(seguimiento)
    session.flush()
    log_change(session, "seguimientos", seguimiento.id_seguimiento, "CREATE", {},
               _snapshot(seguimiento, CAMPOS_SEGUIMIENTO), user.correo, motivo_auditoria,
               correlation_id, sensitive_record=sensible)
    ultimo_anterior = caso.ultimo_seguimiento
    bump_for_update(caso, user.correo, caso.version, ultimo_seguimiento=seguimiento.fecha)
    log_change(session, "casos", id_caso, "UPDATE", {"ultimo_seguimiento": ultimo_anterior},
               {"ultimo_seguimiento": seguimiento.fecha}, user.correo,
               "Actualización por seguimiento", correlation_id, sensitive_record=sensible)
    return seguimiento


def add_derivacion(session: Session, user: AuthenticatedUser, id_caso: str, *,
                    correlation_id: str, motivo_auditoria: str = "Derivación", **campos) -> Derivacion:
    _rechazar_desconocidos(campos, CAMPOS_DERIVACION)
    caso, sensible = _ensure_caso_editable(session, user, id_caso)
    authorize(user, "DERIVACIONES", "create", sensitive=sensible)
    derivacion = Derivacion(id_derivacion=str(uuid4()), id_caso=id_caso,
                             **creation_metadata(user.correo), **campos)
    session.add(derivacion)
    session.flush()
    log_change(session, "derivaciones", derivacion.id_derivacion, "CREATE", {},
               _snapshot(derivacion, CAMPOS_DERIVACION), user.correo, motivo_auditoria,
               correlation_id, sensitive_record=sensible)
    derivacion_anterior = caso.derivacion
    bump_for_update(caso, user.correo, caso.version, derivacion=True)
    log_change(session, "casos", id_caso, "UPDATE", {"derivacion": derivacion_anterior},
               {"derivacion": True}, user.correo, "Actualización por derivación",
               correlation_id, sensitive_record=sensible)
    return derivacion


def add_compromiso(session: Session, user: AuthenticatedUser, id_caso: str, *,
                    correlation_id: str, motivo_auditoria: str = "Compromiso", **campos) -> Compromiso:
    _rechazar_desconocidos(campos, CAMPOS_COMPROMISO)
    _caso, sensible = _ensure_caso_editable(session, user, id_caso)
    authorize(user, "COMPROMISOS", "create", sensitive=sensible)
    campos.setdefault("fecha_creacion_compromiso", utc_now_iso())
    compromiso = Compromiso(id_compromiso=str(uuid4()), id_caso=id_caso,
                             **creation_metadata(user.correo), **campos)
    session.add(compromiso)
    session.flush()
    log_change(session, "compromisos", compromiso.id_compromiso, "CREATE", {},
               _snapshot(compromiso, CAMPOS_COMPROMISO), user.correo, motivo_auditoria,
               correlation_id, sensitive_record=sensible)
    return compromiso


def close_caso(session: Session, user: AuthenticatedUser, id_caso: str, *,
               expected_version: int | None, correlation_id: str,
               motivo_auditoria: str = "Cierre de caso", **campos) -> Cierre:
    """Equivalente a CaseService.gs:124-154 (close). Cierre + actualización del caso padre
    en una sola transacción: si algo falla aquí, no queda un cierre sin reflejar en el
    estado del caso (a diferencia del legacy, sin transacciones reales entre hojas)."""
    _rechazar_desconocidos(campos, CAMPOS_CIERRE)
    caso, sensible = _ensure_caso_editable(session, user, id_caso)
    if (caso.estado_caso or "").strip().upper() == "CERRADO":
        raise AppError("CASE_ALREADY_CLOSED", "El caso ya se encuentra cerrado.", 409)
    cierre = Cierre(id_cierre=str(uuid4()), id_caso=id_caso, **creation_metadata(user.correo), **campos)
    session.add(cierre)
    session.flush()
    log_change(session, "cierres", cierre.id_cierre, "CREATE", {}, _snapshot(cierre, CAMPOS_CIERRE),
               user.correo, motivo_auditoria, correlation_id, sensitive_record=sensible)
    before_caso = _snapshot(caso, CAMPOS_CASO)
    bump_for_update(
        caso, user.correo, expected_version,
        estado_caso="CERRADO",
        fecha_cierre=cierre.fecha_cierre_caso,
        motivo_cierre=cierre.motivo_cierre,
        resultado=cierre.resultado_final or caso.resultado,
    )
    log_change(session, "casos", id_caso, "UPDATE", before_caso, _snapshot(caso, CAMPOS_CASO),
               user.correo, motivo_auditoria, correlation_id, sensitive_record=sensible)
    return cierre
