"""Operaciones contextuales de Oficina permitidas por el diseño de Fase 8."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, authorize
from app.models import Atencion, Persona
from app.services.atenciones import create_atencion, soft_delete_atencion, update_atencion
from app.services.records import get_active, get_history

MODULE = "OFICINA"
ATENCIONES_CONTEXT = "OFICINA"


def _serialize(record: Atencion, person: Persona | None = None) -> dict:
    values = {field: getattr(record, field) for field in record.__table__.columns.keys()}
    values["persona"] = person.nombre if person else None
    values["cedula"] = person.cedula if person else None
    values["area_persona"] = person.area if person else None
    values["registrado_por"] = record.creado_por
    return values


def _atencion(session: Session, record_id: str) -> Atencion:
    record = get_active(session, Atencion, record_id, Atencion.id_atencion)
    if record.contexto_operativo != ATENCIONES_CONTEXT:
        raise AppError("NOT_FOUND", "Atención de Oficina no encontrada.", 404)
    return record


def list_atenciones(session: Session, user: AuthenticatedUser, *, nombre: str | None = None,
                    cedula: str | None = None, area: str | None = None, responsable: str | None = None,
                    estado: str | None = None, desde: str | None = None, hasta: str | None = None,
                    limit: int, offset: int) -> dict:
    authorize(user, MODULE, "read")
    conditions = [Atencion.eliminado.is_(False), Atencion.contexto_operativo == ATENCIONES_CONTEXT]
    if nombre and nombre.strip(): conditions.append(Persona.nombre.ilike(f"%{nombre.strip()}%"))
    if cedula and cedula.strip(): conditions.append(Persona.cedula == cedula.strip())
    if area and area.strip(): conditions.append(Persona.area == area.strip())
    if responsable and responsable.strip(): conditions.append(Atencion.responsable == responsable.strip())
    if estado and estado.strip(): conditions.append(Atencion.estado == estado.strip())
    if desde: conditions.append(Atencion.fecha >= desde)
    if hasta: conditions.append(Atencion.fecha <= hasta)
    stmt = select(Atencion, Persona).outerjoin(Persona, Atencion.id_persona == Persona.id_persona).where(*conditions)
    total = int(session.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = session.execute(stmt.order_by(Atencion.fecha.desc(), Atencion.id_atencion.desc()).offset(offset).limit(limit)).all()
    return {"items": [_serialize(record, person) for record, person in rows], "total": total, "limite": limit, "offset": offset}


def create_atencion_oficina(session: Session, user: AuthenticatedUser, *, correlation_id: str, fields: dict) -> dict:
    authorize(user, MODULE, "create")
    values = dict(fields); values.pop("contexto_operativo", None)
    record = create_atencion(session, user, authorization_module=MODULE, contexto_operativo=ATENCIONES_CONTEXT,
                              motivo_auditoria="Creación de Atención de Oficina", correlation_id=correlation_id, **values)
    return _serialize(record, session.get(Persona, record.id_persona) if record.id_persona else None)


def get_atencion_oficina(session: Session, user: AuthenticatedUser, record_id: str) -> dict:
    authorize(user, MODULE, "read"); record = _atencion(session, record_id)
    return _serialize(record, session.get(Persona, record.id_persona) if record.id_persona else None)


def update_atencion_oficina(session: Session, user: AuthenticatedUser, record_id: str, *, expected_version: int,
                            correlation_id: str, fields: dict) -> dict:
    authorize(user, MODULE, "edit"); _atencion(session, record_id)
    values = dict(fields); values.pop("contexto_operativo", None)
    record = update_atencion(session, user, record_id, authorization_module=MODULE, expected_version=expected_version,
                              motivo_auditoria="Edición de Atención de Oficina", correlation_id=correlation_id, **values)
    return _serialize(record, session.get(Persona, record.id_persona) if record.id_persona else None)


def delete_atencion_oficina(session: Session, user: AuthenticatedUser, record_id: str, *, expected_version: int,
                            motivo: str, correlation_id: str) -> dict:
    authorize(user, MODULE, "delete"); _atencion(session, record_id)
    record = soft_delete_atencion(session, user, record_id, authorization_module=MODULE, expected_version=expected_version,
                                   motivo=motivo, correlation_id=correlation_id)
    return _serialize(record, session.get(Persona, record.id_persona) if record.id_persona else None)


def atencion_history(session: Session, user: AuthenticatedUser, record_id: str):
    authorize(user, MODULE, "read"); _atencion(session, record_id)
    return get_history(session, user, MODULE, "atenciones", record_id)
