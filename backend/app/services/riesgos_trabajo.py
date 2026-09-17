"""Caso especializado para Riesgos de trabajo, sin una tabla paralela."""

from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, authorize, can
from app.models import Caso, DestinoFormulario, Documento, EnvioFormulario, Formulario, FormularioDestino, Persona
from app.services.casos import (
    add_compromiso, add_seguimiento, close_caso, create_caso, is_sensitive_caso,
    list_compromisos, list_seguimientos, sensitive_case_values, update_caso,
)
from app.services.records import get_active, get_history
from app.services.dynamic_responses import save_dynamic_response, serialize_response
from app.services.form_builder import get_definition
from app.services.documentos import download_documento, list_documentos, soft_delete_documento, upload_documento

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


def add_riesgo_compromiso(session: Session, user: AuthenticatedUser, risk_id: str, *, correlation_id: str, **fields):
    _risk(session, risk_id)
    return add_compromiso(
        session, user, risk_id, authorization_module=MODULE, correlation_id=correlation_id,
        motivo_auditoria="Compromiso de Riesgo de trabajo", **fields,
    )


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


def _risk_destination(session: Session) -> DestinoFormulario:
    destination = session.scalar(select(DestinoFormulario).where(
        DestinoFormulario.codigo == CASE_TYPE, DestinoFormulario.activo.is_(True),
        DestinoFormulario.eliminado.is_(False),
    ))
    if destination is None:
        raise AppError("FORM_DESTINATION_NOT_FOUND", "No está configurado el destino Riesgos de trabajo.", 422)
    return destination


def riesgo_forms(session: Session, user: AuthenticatedUser, risk_id: str) -> list[dict]:
    record = _risk(session, risk_id)
    _authorize_record(session, user, record, "read")
    destination = _risk_destination(session)
    forms = list(session.scalars(select(Formulario).join(FormularioDestino).where(
        FormularioDestino.id_destino_catalogo == destination.id_destino,
        FormularioDestino.activo.is_(True), FormularioDestino.eliminado.is_(False),
        Formulario.estado == "PUBLICADO", Formulario.activo.is_(True), Formulario.eliminado.is_(False),
    ).order_by(Formulario.nombre)))
    result = []
    for form in forms:
        response = session.scalar(select(EnvioFormulario).where(
            EnvioFormulario.id_formulario == form.id_formulario,
            EnvioFormulario.usuario_respuesta == user.correo,
            EnvioFormulario.contexto_tipo == "CASOS", EnvioFormulario.contexto_id == risk_id,
            EnvioFormulario.id_destino_respuesta == destination.id_destino,
            EnvioFormulario.eliminado.is_(False),
        ).order_by(EnvioFormulario.fecha_respuesta.desc()))
        definition = get_definition(session, form.id_formulario)
        result.append({**(serialize_response(session, response, user=user) if response else {}),
            "id_formulario": form.id_formulario, "nombre": form.nombre, "descripcion": form.descripcion,
            "estado_respuesta": response.estado if response else "PENDIENTE", "total_preguntas": definition["total_preguntas"],
            "permite_multiples_respuestas": form.permite_multiples_respuestas,
            "puede_crear": can(user, "RESPUESTAS", "create") and can(user, MODULE, "create"),
            "id_destino_respuesta": destination.id_destino})
    return result


def save_riesgo_form_response(session: Session, user: AuthenticatedUser, risk_id: str, form_id: str, *, correlation_id: str, **payload):
    record = _risk(session, risk_id)
    _authorize_record(session, user, record, "read")
    destination = _risk_destination(session)
    payload.pop("id_destino_respuesta", None)
    payload["context_type"] = "CASOS"
    payload["context_id"] = risk_id
    return save_dynamic_response(session, user, form_id, correlation_id=correlation_id,
        response_destination_id=destination.id_destino, context_authorization_module=MODULE,
        required_destination_id=destination.id_destino, **payload)


def riesgo_documentos(session: Session, user: AuthenticatedUser, risk_id: str):
    _authorize_record(session, user, _risk(session, risk_id), "read")
    return list_documentos(session, user, tipo_registro="CASOS", id_registro=risk_id, parent_module=MODULE)


def upload_riesgo_documento(session: Session, user: AuthenticatedUser, risk_id: str, *, correlation_id: str, **payload):
    _authorize_record(session, user, _risk(session, risk_id), "edit")
    return upload_documento(session, user, tipo_registro="CASOS", id_registro=risk_id,
        correlation_id=correlation_id, parent_module=MODULE, **payload)


def _risk_document(session: Session, risk_id: str, id_archivo: str) -> Documento:
    _risk(session, risk_id)
    document = get_active(session, Documento, id_archivo, Documento.id_archivo)
    if document.tipo_registro != "CASOS" or document.id_registro != risk_id:
        raise AppError("NOT_FOUND", "Documento de Riesgo de trabajo no encontrado.", 404)
    return document


def download_riesgo_documento(session: Session, user: AuthenticatedUser, risk_id: str, id_archivo: str, *, correlation_id: str = ""):
    _risk_document(session, risk_id, id_archivo)
    return download_documento(session, user, id_archivo, correlation_id=correlation_id, parent_module=MODULE)


def delete_riesgo_documento(session: Session, user: AuthenticatedUser, risk_id: str, id_archivo: str, *, expected_version: int | None, motivo: str, correlation_id: str = ""):
    _risk_document(session, risk_id, id_archivo)
    return soft_delete_documento(session, user, id_archivo, expected_version=expected_version, motivo=motivo,
        correlation_id=correlation_id, parent_module=MODULE)
