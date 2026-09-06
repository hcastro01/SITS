"""Servicio de Atenciones. Patrón genérico de entidad de proceso simple (Config.gs:56,
Fase 1 §4 línea 90) — Novedades, Recorridos, HallazgosRecorrido y Personas siguen la misma
forma: allowlist explícita de campos (cierra H1), authorize(), expected_version obligatorio
en edición, y una fila de auditoría en la misma transacción.
"""

from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, authorize
from app.models import Atencion
from app.services.audit import log_change
from app.services.records import (
    apply_restore, apply_soft_delete, bump_for_update, check_expected_version,
    creation_metadata, get_active, mark_updated,
)

MODULE = "ATENCIONES"

# Campos de negocio. Los metadatos (activo, eliminado, version, procedencia...) nunca se
# aceptan desde el llamador (hallazgo H1: Base Sistema/ValidationService.gs:28 sí lo permitía).
CAMPOS = (
    "fecha", "hora", "id_persona", "colaborador", "responsable", "tipo_atencion", "motivo",
    "canal", "gestion", "resultado", "requiere_seguimiento", "genera_caso", "observaciones",
    "evidencias", "estado",
)


def _snapshot(record: Atencion) -> dict:
    return {campo: getattr(record, campo) for campo in CAMPOS}


def _rechazar_campos_desconocidos(campos: dict) -> None:
    desconocidos = set(campos) - set(CAMPOS)
    if desconocidos:
        raise AppError("INVALID_FIELD", f"Campos no admitidos: {', '.join(sorted(desconocidos))}.", 422)


def create_atencion(session: Session, user: AuthenticatedUser, *, motivo_auditoria: str,
                     correlation_id: str, **campos) -> Atencion:
    _rechazar_campos_desconocidos(campos)
    authorize(user, MODULE, "create")
    record = Atencion(id_atencion=str(uuid4()), **creation_metadata(user.correo), **campos)
    session.add(record)
    session.flush()
    log_change(session, "atenciones", record.id_atencion, "CREATE", {}, _snapshot(record),
               user.correo, motivo_auditoria, correlation_id)
    return record


def update_atencion(session: Session, user: AuthenticatedUser, id_atencion: str, *,
                     expected_version: int | None, motivo_auditoria: str, correlation_id: str, **campos) -> Atencion:
    _rechazar_campos_desconocidos(campos)
    authorize(user, MODULE, "edit")
    record = get_active(session, Atencion, id_atencion, Atencion.id_atencion)
    before = _snapshot(record)
    bump_for_update(record, user.correo, expected_version, **campos)
    log_change(session, "atenciones", id_atencion, "UPDATE", before, _snapshot(record),
               user.correo, motivo_auditoria, correlation_id)
    return record


def soft_delete_atencion(session: Session, user: AuthenticatedUser, id_atencion: str, *,
                          expected_version: int | None, motivo: str, correlation_id: str) -> Atencion:
    authorize(user, MODULE, "delete")
    record = get_active(session, Atencion, id_atencion, Atencion.id_atencion)
    check_expected_version(record, expected_version)
    before = _snapshot(record)
    apply_soft_delete(record, user.correo, motivo)  # valida el motivo antes de tocar version
    mark_updated(record, user.correo)
    log_change(session, "atenciones", id_atencion, "DELETE", before, _snapshot(record),
               user.correo, motivo, correlation_id)
    return record


def restore_atencion(session: Session, user: AuthenticatedUser, id_atencion: str, *, correlation_id: str) -> Atencion:
    authorize(user, MODULE, "delete")
    record = get_active(session, Atencion, id_atencion, Atencion.id_atencion, include_deleted=True)
    if not record.eliminado:
        raise AppError("NOT_FOUND", "Registro eliminado no encontrado.", 404)
    before = _snapshot(record)
    apply_restore(record)
    record.version += 1
    log_change(session, "atenciones", id_atencion, "RESTORE", before, _snapshot(record),
               user.correo, "Restauración", correlation_id)
    return record
