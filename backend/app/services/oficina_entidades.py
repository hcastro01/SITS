"""CRUD contextual de Beneficios, Préstamos y Seguro de Oficina."""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, authorize
from app.models import Beneficio, Persona, Prestamo, Seguro
from app.services.records import get_active, get_history
from app.services.simple_entities import EntityService

MODULE = "OFICINA"


@dataclass(frozen=True)
class OfficeEntity:
    service: EntityService
    choices: dict[str, frozenset[str]]

    def validate(self, fields: dict, *, creating: bool = False) -> None:
        for field, values in self.choices.items():
            if creating and field not in fields:
                raise AppError("INVALID_INPUT", f"Debe indicar {field}.", 422)
            if field not in fields:
                continue
            value = fields[field]
            if value not in values:
                raise AppError("INVALID_VALUE", f"{field} no admite el valor indicado.", 422)


beneficios = OfficeEntity(EntityService(Beneficio, "beneficios", "id_beneficio", MODULE,
    ("fecha", "persona_id", "tipo_beneficio", "tipo_gestion", "descripcion", "observacion", "responsable")),
    {"tipo_beneficio": frozenset({"TIA", "FARMACIA"}), "tipo_gestion": frozenset({"ACTIVACION", "BLOQUEO", "ANULACION"})})
prestamos = OfficeEntity(EntityService(Prestamo, "prestamos", "id_prestamo", MODULE,
    ("fecha", "persona_id", "tipo", "descripcion", "observacion", "responsable")),
    {"tipo": frozenset({"PRESTAMO", "ANTICIPO"})})
seguros = OfficeEntity(EntityService(Seguro, "seguros", "id_seguro", MODULE,
    ("fecha", "persona_id", "tipo_gestion", "descripcion", "observacion", "responsable")),
    {"tipo_gestion": frozenset({"AFILIACION", "ENROLAMIENTO", "COBERTURA", "REEMBOLSO", "PRIMA", "DEPENDIENTE"})})


def _person(session: Session, persona_id: str | None) -> Persona | None:
    if persona_id is None:
        return None
    return get_active(session, Persona, persona_id, Persona.id_persona)


def serialize(entity: OfficeEntity, record, person: Persona | None = None) -> dict:
    values = entity.service.serialize(record)
    values.update({"persona": person.nombre if person else None, "cedula": person.cedula if person else None,
                   "area_persona": person.area if person else None, "registrado_por": record.creado_por})
    return values


def create(session: Session, user: AuthenticatedUser, entity: OfficeEntity, *, correlation_id: str, fields: dict) -> dict:
    authorize(user, MODULE, "create")
    values = dict(fields); entity.validate(values, creating=True)
    _person(session, values.get("persona_id"))
    record = entity.service.create(session, user, authorization_module=MODULE,
        motivo_auditoria=f"Creación de {entity.service.tabla}", correlation_id=correlation_id, **values)
    return serialize(entity, record, _person(session, record.persona_id))


def get(session: Session, user: AuthenticatedUser, entity: OfficeEntity, record_id: str) -> dict:
    authorize(user, MODULE, "read")
    record = get_active(session, entity.service.model, record_id, getattr(entity.service.model, entity.service.id_field))
    return serialize(entity, record, _person(session, record.persona_id))


def update(session: Session, user: AuthenticatedUser, entity: OfficeEntity, record_id: str, *, expected_version: int | None,
           correlation_id: str, fields: dict) -> dict:
    authorize(user, MODULE, "edit")
    values = dict(fields); entity.validate(values)
    if not values:
        raise AppError("INVALID_INPUT", "Debe indicar al menos un campo para actualizar.", 422)
    if "persona_id" in values:
        _person(session, values["persona_id"])
    record = entity.service.update(session, user, record_id, authorization_module=MODULE,
        expected_version=expected_version, motivo_auditoria=f"Edición de {entity.service.tabla}",
        correlation_id=correlation_id, **values)
    return serialize(entity, record, _person(session, record.persona_id))


def delete(session: Session, user: AuthenticatedUser, entity: OfficeEntity, record_id: str, *, expected_version: int | None,
           motivo: str, correlation_id: str) -> dict:
    authorize(user, MODULE, "delete")
    record = entity.service.soft_delete(session, user, record_id, authorization_module=MODULE,
        expected_version=expected_version, motivo=motivo, correlation_id=correlation_id)
    return serialize(entity, record, _person(session, record.persona_id))


def list_records(session: Session, user: AuthenticatedUser, entity: OfficeEntity, *, nombre: str | None, cedula: str | None,
                 area: str | None, responsable: str | None, fecha: str | None, tipo: str | None,
                 tipo_gestion: str | None, limit: int, offset: int) -> dict:
    authorize(user, MODULE, "read")
    model = entity.service.model
    conditions = [model.eliminado.is_(False)]
    if nombre and nombre.strip(): conditions.append(Persona.nombre.ilike(f"%{nombre.strip()}%"))
    if cedula and cedula.strip(): conditions.append(Persona.cedula == cedula.strip())
    if area and area.strip(): conditions.append(Persona.area == area.strip())
    if responsable and responsable.strip(): conditions.append(model.responsable == responsable.strip())
    if fecha: conditions.append(model.fecha == fecha)
    if tipo and hasattr(model, "tipo"): conditions.append(model.tipo == tipo)
    if tipo and hasattr(model, "tipo_beneficio"): conditions.append(model.tipo_beneficio == tipo)
    if tipo_gestion and hasattr(model, "tipo_gestion"): conditions.append(model.tipo_gestion == tipo_gestion)
    stmt = select(model, Persona).outerjoin(Persona, model.persona_id == Persona.id_persona).where(*conditions)
    total = int(session.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = session.execute(stmt.order_by(model.fecha.desc(), getattr(model, entity.service.id_field).desc()).offset(offset).limit(limit)).all()
    return {"items": [serialize(entity, record, person) for record, person in rows], "total": total,
            "limite": limit, "offset": offset}


def history(session: Session, user: AuthenticatedUser, entity: OfficeEntity, record_id: str):
    get(session, user, entity, record_id)
    return get_history(session, user, MODULE, entity.service.tabla, record_id)
