"""Wrappers contextuales de Producción sobre entidades operativas existentes."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, authorize
from app.models import Atencion, Novedad, Persona, Recorrido
from app.services.atenciones import create_atencion, soft_delete_atencion, update_atencion
from app.services.records import get_active, get_history
from app.services.novedades import novedades
from app.services.recorridos import recorridos

MODULE = "PRODUCCION"
ATENCIONES_CONTEXT = "PRODUCCION"


def _serialize(record, person=None, *, identifier: str) -> dict:
    values = {field: getattr(record, field) for field in record.__table__.columns.keys()
              if field not in {"archivo_fuente", "hoja_fuente", "registro_fuente", "fecha_importacion", "usuario_importacion"}}
    values[identifier] = getattr(record, identifier)
    values["persona"] = person.nombre if person else None
    values["cedula"] = person.cedula if person else None
    values["area_persona"] = person.area if person else None
    values["registrado_por"] = record.creado_por
    return values


def _atencion(session: Session, record_id: str) -> Atencion:
    record = get_active(session, Atencion, record_id, Atencion.id_atencion)
    if record.contexto_operativo != ATENCIONES_CONTEXT:
        raise AppError("NOT_FOUND", "Atención de Producción no encontrada.", 404)
    return record


def _entity(session: Session, model, identifier: str, record_id: str):
    return get_active(session, model, record_id, getattr(model, identifier))


def _list(session: Session, user: AuthenticatedUser, *, model, identifier: str, context: str | None = None,
          nombre: str | None = None, cedula: str | None = None, area: str | None = None,
          responsable: str | None = None, estado: str | None = None, desde: str | None = None,
          hasta: str | None = None, limit: int, offset: int):
    authorize(user, MODULE, "read")
    conditions = [model.eliminado.is_(False)]
    if context:
        conditions.append(model.contexto_operativo == context)
    if nombre and nombre.strip(): conditions.append(Persona.nombre.ilike(f"%{nombre.strip()}%"))
    if cedula and cedula.strip(): conditions.append(Persona.cedula == cedula.strip())
    if area and area.strip(): conditions.append(Persona.area == area.strip())
    if responsable and responsable.strip(): conditions.append(model.responsable == responsable.strip())
    if estado and hasattr(model, "estado") and estado.strip(): conditions.append(model.estado == estado.strip())
    if desde and hasattr(model, "fecha"): conditions.append(model.fecha >= desde)
    if hasta and hasattr(model, "fecha"): conditions.append(model.fecha <= hasta)
    stmt = select(model, Persona).outerjoin(Persona, model.id_persona == Persona.id_persona).where(*conditions)
    total = int(session.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = session.execute(stmt.order_by(model.fecha.desc(), getattr(model, identifier).desc()).offset(offset).limit(limit)).all()
    return {"items": [_serialize(record, person, identifier=identifier) for record, person in rows], "total": total,
            "limite": limit, "offset": offset}


def list_atenciones(session: Session, user: AuthenticatedUser, **filters):
    return _list(session, user, model=Atencion, identifier="id_atencion", context=ATENCIONES_CONTEXT, **filters)


def create_atencion_produccion(session: Session, user: AuthenticatedUser, *, correlation_id: str, fields: dict):
    authorize(user, MODULE, "create")
    fields = dict(fields)
    fields.pop("contexto_operativo", None)
    record = create_atencion(session, user, authorization_module=MODULE, contexto_operativo=ATENCIONES_CONTEXT,
                              motivo_auditoria="Creación de Atención de Producción", correlation_id=correlation_id, **fields)
    return _serialize(record, session.get(Persona, record.id_persona) if record.id_persona else None, identifier="id_atencion")


def get_atencion_produccion(session: Session, user: AuthenticatedUser, record_id: str):
    authorize(user, MODULE, "read"); record = _atencion(session, record_id)
    return _serialize(record, session.get(Persona, record.id_persona) if record.id_persona else None, identifier="id_atencion")


def update_atencion_produccion(session: Session, user: AuthenticatedUser, record_id: str, *, expected_version: int, correlation_id: str, fields: dict):
    authorize(user, MODULE, "edit"); _atencion(session, record_id)
    fields = dict(fields); fields.pop("contexto_operativo", None)
    record = update_atencion(session, user, record_id, authorization_module=MODULE, expected_version=expected_version,
                              motivo_auditoria="Edición de Atención de Producción", correlation_id=correlation_id, **fields)
    return _serialize(record, session.get(Persona, record.id_persona) if record.id_persona else None, identifier="id_atencion")


def delete_atencion_produccion(session: Session, user: AuthenticatedUser, record_id: str, *, expected_version: int, motivo: str, correlation_id: str):
    authorize(user, MODULE, "delete"); _atencion(session, record_id)
    return soft_delete_atencion(session, user, record_id, authorization_module=MODULE, expected_version=expected_version, motivo=motivo, correlation_id=correlation_id)


def _production_entity(service, model, identifier: str, label: str):
    def listing(session: Session, user: AuthenticatedUser, **filters):
        return _list(session, user, model=model, identifier=identifier, **filters)
    def create(session: Session, user: AuthenticatedUser, *, correlation_id: str, fields: dict):
        authorize(user, MODULE, "create")
        record = service.create(session, user, authorization_module=MODULE, motivo_auditoria=f"Creación de {label} de Producción", correlation_id=correlation_id, **fields)
        return _serialize(record, session.get(Persona, record.id_persona) if record.id_persona else None, identifier=identifier)
    def get(session: Session, user: AuthenticatedUser, record_id: str):
        authorize(user, MODULE, "read"); record = _entity(session, model, identifier, record_id)
        return _serialize(record, session.get(Persona, record.id_persona) if record.id_persona else None, identifier=identifier)
    def update(session: Session, user: AuthenticatedUser, record_id: str, *, expected_version: int, correlation_id: str, fields: dict):
        authorize(user, MODULE, "edit"); _entity(session, model, identifier, record_id)
        record = service.update(session, user, record_id, authorization_module=MODULE, expected_version=expected_version,
                                motivo_auditoria=f"Edición de {label} de Producción", correlation_id=correlation_id, **fields)
        return _serialize(record, session.get(Persona, record.id_persona) if record.id_persona else None, identifier=identifier)
    def delete(session: Session, user: AuthenticatedUser, record_id: str, *, expected_version: int, motivo: str, correlation_id: str):
        authorize(user, MODULE, "delete"); _entity(session, model, identifier, record_id)
        return service.soft_delete(session, user, record_id, authorization_module=MODULE, expected_version=expected_version, motivo=motivo, correlation_id=correlation_id)
    return listing, create, get, update, delete


list_recorridos, create_recorrido, get_recorrido, update_recorrido, delete_recorrido = _production_entity(recorridos, Recorrido, "id_recorrido", "Recorrido")
list_novedades, create_novedad, get_novedad, update_novedad, delete_novedad = _production_entity(novedades, Novedad, "id_novedad", "Novedad de planta")


def production_history(session: Session, user: AuthenticatedUser, *, kind: str, record_id: str):
    config = {"atenciones": (Atencion, "id_atencion", "ATENCIONES", "atenciones"), "recorridos": (Recorrido, "id_recorrido", "RECORRIDOS", "recorridos"), "novedades": (Novedad, "id_novedad", "NOVEDADES", "novedades")}[kind]
    model, identifier, _, table = config
    authorize(user, MODULE, "read")
    record = _atencion(session, record_id) if kind == "atenciones" else _entity(session, model, identifier, record_id)
    return get_history(session, user, MODULE, table, record_id)
