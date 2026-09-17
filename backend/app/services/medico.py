"""Superficie explícita de Atenciones del Departamento Médico."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, authorize
from app.models import Atencion, Persona
from app.services.atenciones import create_atencion, restore_atencion, soft_delete_atencion, update_atencion
from app.services.documentos import download_documento, list_documentos, soft_delete_documento, upload_documento
from app.services.records import get_active, get_history

MODULE = "ATENCIONES"
CONTEXT = "MEDICO"


def _atencion(session: Session, record_id: str, *, include_deleted: bool = False) -> Atencion:
    record = get_active(session, Atencion, record_id, Atencion.id_atencion, include_deleted=include_deleted)
    if record.contexto_operativo != CONTEXT:
        raise AppError("NOT_FOUND", "Atención médica no encontrada.", 404)
    return record


def _serialize(record: Atencion, person: Persona | None = None) -> dict:
    values = {field: getattr(record, field) for field in record.__table__.columns.keys()}
    values.update(persona=person.nombre if person else None, cedula=person.cedula if person else None,
                  area_persona=person.area if person else None, registrado_por=record.creado_por)
    return values


def list_atenciones(session: Session, user: AuthenticatedUser, *, limit: int, offset: int) -> dict:
    authorize(user, MODULE, "read")
    stmt = select(Atencion, Persona).outerjoin(Persona, Atencion.id_persona == Persona.id_persona).where(
        Atencion.eliminado.is_(False), Atencion.contexto_operativo == CONTEXT,
    )
    total = int(session.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = session.execute(stmt.order_by(Atencion.fecha.desc(), Atencion.id_atencion.desc()).offset(offset).limit(limit)).all()
    return {"items": [_serialize(record, person) for record, person in rows], "total": total, "limite": limit, "offset": offset}


def create(session: Session, user: AuthenticatedUser, *, correlation_id: str, fields: dict) -> dict:
    values = dict(fields); values.pop("contexto_operativo", None)
    record = create_atencion(session, user, authorization_module=MODULE, contexto_operativo=CONTEXT,
                             motivo_auditoria="Creación de Atención médica", correlation_id=correlation_id, **values)
    return _serialize(record, session.get(Persona, record.id_persona) if record.id_persona else None)


def get(session: Session, user: AuthenticatedUser, record_id: str) -> dict:
    authorize(user, MODULE, "read"); record = _atencion(session, record_id)
    return _serialize(record, session.get(Persona, record.id_persona) if record.id_persona else None)


def update(session: Session, user: AuthenticatedUser, record_id: str, *, expected_version: int, correlation_id: str, fields: dict) -> dict:
    authorize(user, MODULE, "edit"); _atencion(session, record_id)
    values = dict(fields); values.pop("contexto_operativo", None)
    record = update_atencion(session, user, record_id, authorization_module=MODULE, expected_version=expected_version,
                              motivo_auditoria="Edición de Atención médica", correlation_id=correlation_id, **values)
    return _serialize(record, session.get(Persona, record.id_persona) if record.id_persona else None)


def delete(session: Session, user: AuthenticatedUser, record_id: str, *, expected_version: int, motivo: str, correlation_id: str) -> dict:
    authorize(user, MODULE, "delete"); _atencion(session, record_id)
    record = soft_delete_atencion(session, user, record_id, authorization_module=MODULE, expected_version=expected_version, motivo=motivo, correlation_id=correlation_id)
    return _serialize(record, session.get(Persona, record.id_persona) if record.id_persona else None)


def restore(session: Session, user: AuthenticatedUser, record_id: str, *, correlation_id: str) -> dict:
    authorize(user, MODULE, "delete"); _atencion(session, record_id, include_deleted=True)
    record = restore_atencion(session, user, record_id, correlation_id=correlation_id)
    return _serialize(record, session.get(Persona, record.id_persona) if record.id_persona else None)


def history(session: Session, user: AuthenticatedUser, record_id: str):
    authorize(user, MODULE, "read"); _atencion(session, record_id)
    return get_history(session, user, MODULE, "atenciones", record_id)


def documents(session: Session, user: AuthenticatedUser, record_id: str):
    _atencion(session, record_id)
    return list_documentos(session, user, tipo_registro="ATENCIONES", id_registro=record_id, parent_module=MODULE)


def upload_document(session: Session, user: AuthenticatedUser, record_id: str, **kwargs):
    _atencion(session, record_id)
    return upload_documento(session, user, tipo_registro="ATENCIONES", id_registro=record_id, parent_module=MODULE, **kwargs)


def download_document(session: Session, user: AuthenticatedUser, record_id: str, document_id: str, **kwargs):
    _atencion(session, record_id)
    return download_documento(session, user, document_id, parent_module=MODULE, **kwargs)


def delete_document(session: Session, user: AuthenticatedUser, record_id: str, document_id: str, **kwargs):
    _atencion(session, record_id)
    return soft_delete_documento(session, user, document_id, parent_module=MODULE, **kwargs)
