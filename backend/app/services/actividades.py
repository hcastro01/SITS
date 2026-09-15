from datetime import date, datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, authorize
from app.core.time import utc_now_iso
from app.models import Actividad, Persona, User
from app.services.audit import log_change
from app.services.records import apply_soft_delete, check_expected_version, creation_metadata, get_active, mark_updated

MODULE = "ACTIVIDADES"
ESTADOS = {"PENDIENTE", "EN_PROCESO", "COMPLETADA"}
TIPOS_FECHA = {"PROGRAMADA", "LIMITE"}
CAMPOS = ("nombre", "descripcion", "responsable_id", "tipo_fecha", "fecha_objetivo", "estado", "persona_id")


def _usuario_activo(session: Session, user_id: str) -> User:
    user = session.get(User, user_id)
    if user is None or user.eliminado or not user.activo or user.estado != "ACTIVO":
        raise AppError("RESPONSABLE_INVALIDO", "El responsable debe ser un usuario activo.", 422)
    return user


def _autor(session: Session, user: AuthenticatedUser) -> User:
    author = session.scalar(select(User).where(func.lower(User.correo) == user.correo.lower()))
    if author is None:
        raise AppError("AUTHOR_NOT_FOUND", "No se encontró el usuario autenticado.", 401)
    return author


def _validate(session: Session, fields: dict, *, partial: bool = False) -> None:
    unknown = set(fields) - set(CAMPOS)
    if unknown:
        raise AppError("INVALID_FIELD", f"Campos no admitidos: {', '.join(sorted(unknown))}.", 422)
    for name in ("nombre", "descripcion"):
        if name in fields and not str(fields[name] or "").strip():
            raise AppError("INVALID_INPUT", f"{name.capitalize()} es obligatorio.", 422)
    if not partial:
        missing = [name for name in ("nombre", "descripcion", "responsable_id", "tipo_fecha", "fecha_objetivo") if name not in fields]
        if missing:
            raise AppError("INVALID_INPUT", "Faltan campos obligatorios.", 422)
    if "responsable_id" in fields:
        _usuario_activo(session, fields["responsable_id"])
    if "persona_id" in fields and fields["persona_id"] is not None and session.get(Persona, fields["persona_id"]) is None:
        raise AppError("PERSON_NOT_FOUND", "La persona relacionada no existe.", 422)
    if "tipo_fecha" in fields and fields["tipo_fecha"] not in TIPOS_FECHA:
        raise AppError("INVALID_DATE_TYPE", "Tipo de fecha no válido.", 422)
    if "estado" in fields and fields["estado"] not in ESTADOS:
        raise AppError("INVALID_STATUS", "Estado no válido.", 422)
    if "fecha_objetivo" in fields:
        try:
            date.fromisoformat(fields["fecha_objetivo"])
        except (TypeError, ValueError):
            raise AppError("INVALID_DATE", "La fecha objetivo no es válida.", 422) from None


def _snapshot(record: Actividad) -> dict:
    return {**{name: getattr(record, name) for name in CAMPOS}, "fecha_finalizacion": record.fecha_finalizacion}


def create_actividad(session: Session, user: AuthenticatedUser, *, motivo_auditoria: str, correlation_id: str, **fields) -> Actividad:
    authorize(user, MODULE, "create")
    fields = {**fields, "estado": fields.get("estado", "PENDIENTE")}
    _validate(session, fields)
    author = _autor(session, user)
    record = Actividad(id_actividad=str(uuid4()), creado_por_id=author.id_usuario, **creation_metadata(user.correo), **fields)
    session.add(record)
    session.flush()
    log_change(session, "actividades", record.id_actividad, "CREATE", {}, _snapshot(record), user.correo, motivo_auditoria, correlation_id)
    return record


def update_actividad(session: Session, user: AuthenticatedUser, activity_id: str, *, expected_version: int | None, motivo_auditoria: str, correlation_id: str, **fields) -> Actividad:
    authorize(user, MODULE, "edit")
    _validate(session, fields, partial=True)
    record = get_active(session, Actividad, activity_id, Actividad.id_actividad)
    check_expected_version(record, expected_version)
    before = _snapshot(record)
    previous = record.estado
    for name, value in fields.items():
        setattr(record, name, value)
    if "estado" in fields:
        if fields["estado"] == "COMPLETADA" and previous != "COMPLETADA": record.fecha_finalizacion = utc_now_iso()
        elif fields["estado"] != "COMPLETADA" and previous == "COMPLETADA": record.fecha_finalizacion = None
    mark_updated(record, user.correo)
    log_change(session, "actividades", activity_id, "UPDATE", before, _snapshot(record), user.correo, motivo_auditoria, correlation_id)
    return record


def soft_delete_actividad(session: Session, user: AuthenticatedUser, activity_id: str, *, expected_version: int | None, motivo: str, correlation_id: str) -> Actividad:
    authorize(user, MODULE, "delete")
    record = get_active(session, Actividad, activity_id, Actividad.id_actividad)
    check_expected_version(record, expected_version)
    before = _snapshot(record)
    apply_soft_delete(record, user.correo, motivo)
    mark_updated(record, user.correo)
    log_change(session, "actividades", activity_id, "DELETE", before, _snapshot(record), user.correo, motivo, correlation_id)
    return record


def is_overdue(record: Actividad) -> bool:
    return record.tipo_fecha == "LIMITE" and record.estado != "COMPLETADA" and date.fromisoformat(record.fecha_objetivo) < datetime.now(ZoneInfo("America/Guayaquil")).date()


def list_actividades(session: Session, user: AuthenticatedUser, *, search: str | None, responsable_id: str | None, estado: str | None, tipo_fecha: str | None, desde: str | None, hasta: str | None, mis_actividades: bool, limit: int, offset: int):
    authorize(user, MODULE, "read")
    stmt = select(Actividad).where(Actividad.eliminado.is_(False))
    if search:
        term = f"%{search.strip()}%"; stmt = stmt.where(or_(Actividad.nombre.ilike(term), Actividad.descripcion.ilike(term)))
    if responsable_id: stmt = stmt.where(Actividad.responsable_id == responsable_id)
    if estado: stmt = stmt.where(Actividad.estado == estado)
    if tipo_fecha: stmt = stmt.where(Actividad.tipo_fecha == tipo_fecha)
    if desde: stmt = stmt.where(Actividad.fecha_objetivo >= desde)
    if hasta: stmt = stmt.where(Actividad.fecha_objetivo <= hasta)
    if mis_actividades: stmt = stmt.where(Actividad.responsable_id == _autor(session, user).id_usuario)
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = session.scalars(stmt.order_by(Actividad.estado == "COMPLETADA", Actividad.fecha_objetivo, Actividad.fecha_creacion.desc()).offset(offset).limit(limit)).all()
    return rows, total
