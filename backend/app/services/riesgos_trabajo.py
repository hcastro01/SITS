"""Caso especializado para Riesgos de trabajo, sin una tabla paralela."""

from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, authorize, can
from app.models import Caso, Persona
from app.services.casos import (
    add_compromiso, add_seguimiento, close_caso, create_caso, is_sensitive_caso,
    list_compromisos, list_seguimientos, sensitive_case_values, update_caso,
)
from app.services.records import get_active, get_history

MODULE = "RIESGOS_TRABAJO"
CASE_TYPE = "RIESGOS_TRABAJO"


def _date(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise AppError("INVALID_DATE", f"{field} debe estar en formato ISO (YYYY-MM-DD).", 422) from exc


def _risk(session: Session, risk_id: str) -> Caso:
    record = get_active(session, Caso, risk_id, Caso.id_caso)
    if record.tipo_caso != CASE_TYPE:
        raise AppError("NOT_FOUND", "Riesgo de trabajo no encontrado.", 404)
    return record


def _authorize_record(session: Session, user: AuthenticatedUser, record: Caso, action: str) -> None:
    authorize(user, MODULE, action, sensitive=is_sensitive_caso(session, record.nivel_sensibilidad))


def create_riesgo(session: Session, user: AuthenticatedUser, *, persona_id: str, fecha_apertura: str,
                  responsable: str | None, estado_caso: str, prioridad: str | None,
                  resultado: str | None, correlation_id: str) -> Caso:
    authorize(user, MODULE, "create")
    person = get_active(session, Persona, persona_id, Persona.id_persona)
    if not person.activo:
        raise AppError("PERSON_NOT_FOUND", "La Persona no se encuentra activa.", 422)
    return create_caso(
        session, user, authorization_module=MODULE, motivo_auditoria="Creación de Riesgo de trabajo",
        correlation_id=correlation_id, id_persona=person.id_persona, colaborador=person.nombre,
        fecha_apertura=_date(fecha_apertura, "fecha_apertura"), responsable=responsable,
        estado_caso=estado_caso, prioridad=prioridad, resultado=resultado, tipo_caso=CASE_TYPE,
    )


def list_riesgos(session: Session, user: AuthenticatedUser, *, nombre: str | None, cedula: str | None,
                 area: str | None, estado: str | None, responsable: str | None, desde: str | None,
                 hasta: str | None, limit: int, offset: int):
    authorize(user, MODULE, "read")
    conditions = [Caso.tipo_caso == CASE_TYPE, Caso.eliminado.is_(False)]
    sensitive_values = sensitive_case_values(session)
    if sensitive_values and not can(user, MODULE, "sensitive"):
        normalized = func.upper(func.trim(Caso.nivel_sensibilidad))
        conditions.append(or_(Caso.nivel_sensibilidad.is_(None), normalized.not_in(sensitive_values)))
    if nombre and nombre.strip(): conditions.append(Persona.nombre.ilike(f"%{nombre.strip()}%"))
    if cedula and cedula.strip(): conditions.append(Persona.cedula == cedula.strip())
    if area and area.strip(): conditions.append(Persona.area == area.strip())
    if estado and estado.strip(): conditions.append(Caso.estado_caso == estado.strip())
    if responsable and responsable.strip(): conditions.append(Caso.responsable == responsable.strip())
    if desde: conditions.append(Caso.fecha_apertura >= _date(desde, "desde"))
    if hasta: conditions.append(Caso.fecha_apertura <= _date(hasta, "hasta"))
    stmt = select(Caso, Persona).join(Persona, Caso.id_persona == Persona.id_persona).where(*conditions)
    total = int(session.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = session.execute(stmt.order_by(Caso.fecha_apertura.desc(), Caso.id_caso.desc()).offset(offset).limit(limit)).all()
    return rows, total


def get_riesgo(session: Session, user: AuthenticatedUser, risk_id: str) -> Caso:
    record = _risk(session, risk_id)
    _authorize_record(session, user, record, "read")
    return record


def update_riesgo(session: Session, user: AuthenticatedUser, risk_id: str, *, expected_version: int,
                  responsable: str | None = None, estado_caso: str | None = None, prioridad: str | None = None,
                  resultado: str | None = None, correlation_id: str) -> Caso:
    record = _risk(session, risk_id)
    _authorize_record(session, user, record, "edit")
    fields = {key: value for key, value in {
        "responsable": responsable, "estado_caso": estado_caso, "prioridad": prioridad, "resultado": resultado,
    }.items() if value is not None}
    if not fields:
        raise AppError("INVALID_INPUT", "Debe indicar al menos un campo para actualizar.", 422)
    return update_caso(
        session, user, risk_id, authorization_module=MODULE, expected_version=expected_version,
        motivo_auditoria="Edición de Riesgo de trabajo", correlation_id=correlation_id, **fields,
    )


def riesgo_seguimientos(session: Session, user: AuthenticatedUser, risk_id: str):
    _risk(session, risk_id)
    return list_seguimientos(session, user, risk_id, authorization_module=MODULE)


def add_riesgo_seguimiento(session: Session, user: AuthenticatedUser, risk_id: str, *, correlation_id: str, **fields):
    _risk(session, risk_id)
    return add_seguimiento(
        session, user, risk_id, authorization_module=MODULE, correlation_id=correlation_id,
        motivo_auditoria="Seguimiento de Riesgo de trabajo", **fields,
    )


def riesgo_compromisos(session: Session, user: AuthenticatedUser, risk_id: str):
    _risk(session, risk_id)
    return list_compromisos(session, user, risk_id, authorization_module=MODULE)


def close_riesgo(session: Session, user: AuthenticatedUser, risk_id: str, *, expected_version: int,
                 fecha_cierre_caso: str | None, responsable: str | None, motivo_cierre: str | None,
                 resultado_final: str | None, correlation_id: str):
    _risk(session, risk_id)
    return close_caso(
        session, user, risk_id, authorization_module=MODULE, expected_version=expected_version,
        correlation_id=correlation_id, motivo_auditoria="Cierre de Riesgo de trabajo",
        fecha_cierre_caso=_date(fecha_cierre_caso, "fecha_cierre_caso"), responsable=responsable,
        motivo_cierre=motivo_cierre, resultado_final=resultado_final,
    )


def riesgo_history(session: Session, user: AuthenticatedUser, risk_id: str):
    _risk(session, risk_id)
    return get_history(session, user, MODULE, "casos", risk_id)
