"""Helpers de guardado/soft-delete/historial compartidos por los servicios de entidad.

No exponen despacho por nombre de tabla arbitrario: MIGRACION_FASE_1.md §5 es explícito en
que las rutas "genéricas" del contrato REST son abreviatura documental y no deben permitir
seleccionar una tabla libre ni saltarse servicios especializados. Cada entidad (Atencion,
Caso, ...) tiene su propio módulo de servicio con su propia lista de campos permitidos;
estas funciones solo evitan repetir la mecánica de versión/auditoría/soft-delete.
"""

from app.core.time import utc_now_iso

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, authorize
from app.models import Auditoria


def get_active(session: Session, model: type, id_value: str, id_column, *, include_deleted: bool = False):
    stmt = select(model).where(id_column == id_value)
    if not include_deleted:
        stmt = stmt.where(model.eliminado.is_(False))
    record = session.scalar(stmt)
    if record is None:
        raise AppError("NOT_FOUND", "Registro no encontrado.", 404)
    return record


def check_expected_version(record, expected_version: int | None) -> None:
    if expected_version is None:
        raise AppError("EXPECTED_VERSION_REQUIRED", "Debe indicar la versión esperada del registro.", 422)
    if expected_version != record.version:
        raise AppError(
            "VERSION_CONFLICT",
            "El registro fue modificado por otro usuario. Recargue la información.",
            409,
        )


def creation_metadata(usuario: str) -> dict:
    return {"fecha_creacion": utc_now_iso(), "creado_por": usuario}


def mark_updated(record, usuario: str) -> None:
    record.version += 1
    record.fecha_actualizacion = utc_now_iso()
    record.actualizado_por = usuario


def bump_for_update(record, usuario: str, expected_version: int | None, **campos) -> None:
    check_expected_version(record, expected_version)
    for campo, valor in campos.items():
        setattr(record, campo, valor)
    mark_updated(record, usuario)


def apply_soft_delete(record, usuario: str, motivo: str | None) -> None:
    if not motivo or not motivo.strip():
        raise AppError("DELETE_REASON_REQUIRED", "Debe indicar el motivo de eliminación.", 422)
    record.activo = False
    record.eliminado = True
    record.fecha_eliminacion = utc_now_iso()
    record.usuario_eliminacion = usuario
    record.motivo_eliminacion = motivo.strip()


def apply_restore(record) -> None:
    record.activo = True
    record.eliminado = False
    record.fecha_eliminacion = None
    record.usuario_eliminacion = None
    record.motivo_eliminacion = None


def get_history(session: Session, user: AuthenticatedUser, module: str, tabla: str, id_registro: str) -> list[Auditoria]:
    """Base Sistema/ProcessService.gs:151-162 solo exigía permiso del módulo. Hallazgo H3:
    el historial es auditoría y debe exigir también AUDITORIA:read."""
    authorize(user, module, "read")
    authorize(user, "AUDITORIA", "read")
    stmt = (
        select(Auditoria)
        .where(Auditoria.tabla == tabla, Auditoria.id_registro == id_registro)
        .order_by(Auditoria.fecha_hora.desc())
    )
    return list(session.scalars(stmt))
