"""Operaciones contextuales de Oficina permitidas por el diseño de Fase 8."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, authorize, can
from app.models import Atencion, Beneficio, DestinoFormulario, Documento, EnvioFormulario, Formulario, FormularioDestino, Persona, Prestamo, Seguro
from app.services.atenciones import create_atencion, soft_delete_atencion, update_atencion
from app.services.documentos import download_documento, list_documentos, soft_delete_documento, upload_documento
from app.services.dynamic_responses import save_dynamic_response, serialize_response
from app.services.form_builder import get_definition
from app.services import oficina_entidades
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


_INTEGRATION_CONTEXTS = {
    "atenciones": (Atencion, "id_atencion", "ATENCIONES", "OFICINA_ATENCIONES", "ATENCIONES"),
    "beneficios": (Beneficio, "id_beneficio", "BENEFICIOS", "BENEFICIOS", "BENEFICIOS"),
    "prestamos": (Prestamo, "id_prestamo", "PRESTAMOS", "PRESTAMOS", "PRESTAMOS"),
    "seguro": (Seguro, "id_seguro", "SEGUROS", "SEGURO", "SEGUROS"),
}


def _office_record(session: Session, kind: str, record_id: str):
    model, identifier, context_type, destination_code, document_type = _INTEGRATION_CONTEXTS[kind]
    record = _atencion(session, record_id) if kind == "atenciones" else get_active(session, model, record_id, getattr(model, identifier))
    return record, context_type, destination_code, document_type


def _office_destination(session: Session, code: str) -> DestinoFormulario:
    destination = session.scalar(select(DestinoFormulario).where(
        DestinoFormulario.codigo == code, DestinoFormulario.activo.is_(True),
        DestinoFormulario.eliminado.is_(False),
    ))
    if destination is None:
        raise AppError("FORM_DESTINATION_NOT_FOUND", "No está configurado el destino de Oficina.", 422)
    return destination


def office_forms(session: Session, user: AuthenticatedUser, *, kind: str, record_id: str) -> list[dict]:
    authorize(user, MODULE, "read"); authorize(user, "FORMULARIOS", "read")
    _, context_type, destination_code, _ = _office_record(session, kind, record_id)
    destination = _office_destination(session, destination_code)
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
            EnvioFormulario.contexto_tipo == context_type, EnvioFormulario.contexto_id == record_id,
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


def save_office_form_response(session: Session, user: AuthenticatedUser, *, kind: str, record_id: str,
                              form_id: str, correlation_id: str, payload: dict):
    authorize(user, MODULE, "create"); authorize(user, "FORMULARIOS", "read"); authorize(user, "RESPUESTAS", "create")
    _, context_type, destination_code, _ = _office_record(session, kind, record_id)
    destination = _office_destination(session, destination_code)
    values = dict(payload)
    for field in ("contexto_tipo", "contexto_id", "id_registro_proceso", "crear_contexto", "id_persona", "id_destino_respuesta"):
        values.pop(field, None)
    mapped = {
        "draft": values.pop("borrador", False), "answers": values.pop("respuestas", []),
        "client_key": values.pop("id_envio_cliente", None), "legacy_record_id": values.pop("id_registro_proceso", None),
        "response_id": values.pop("id_respuesta", None), "expected_version": values.pop("expected_version", None),
        "edit_registered": values.pop("editar_registrado", False),
        "attachments": values.pop("adjuntos", []),
    }
    return save_dynamic_response(session, user, form_id, correlation_id=correlation_id,
        context_type=context_type, context_id=record_id, response_destination_id=destination.id_destino,
        context_authorization_module=MODULE, required_destination_id=destination.id_destino, **mapped)


def _office_document_record(session: Session, user: AuthenticatedUser, *, kind: str, record_id: str, action: str):
    authorize(user, MODULE, action)
    _, _, _, document_type = _office_record(session, kind, record_id)
    return document_type


def office_documents(session: Session, user: AuthenticatedUser, *, kind: str, record_id: str):
    record_type = _office_document_record(session, user, kind=kind, record_id=record_id, action="read")
    return list_documentos(session, user, tipo_registro=record_type, id_registro=record_id, parent_module=MODULE)


def upload_office_document(session: Session, user: AuthenticatedUser, *, kind: str, record_id: str, correlation_id: str, **payload):
    record_type = _office_document_record(session, user, kind=kind, record_id=record_id, action="edit")
    return upload_documento(session, user, tipo_registro=record_type, id_registro=record_id,
                            correlation_id=correlation_id, parent_module=MODULE, **payload)


def _office_document(session: Session, user: AuthenticatedUser, *, kind: str, record_id: str, document_id: str, action: str) -> Documento:
    record_type = _office_document_record(session, user, kind=kind, record_id=record_id, action=action)
    document = get_active(session, Documento, document_id, Documento.id_archivo)
    if document.tipo_registro != record_type or document.id_registro != record_id:
        raise AppError("NOT_FOUND", "Documento de Oficina no encontrado.", 404)
    return document


def download_office_document(session: Session, user: AuthenticatedUser, *, kind: str, record_id: str, document_id: str, correlation_id: str = ""):
    _office_document(session, user, kind=kind, record_id=record_id, document_id=document_id, action="read")
    return download_documento(session, user, document_id, correlation_id=correlation_id, parent_module=MODULE)


def delete_office_document(session: Session, user: AuthenticatedUser, *, kind: str, record_id: str, document_id: str, expected_version: int | None, motivo: str, correlation_id: str = ""):
    _office_document(session, user, kind=kind, record_id=record_id, document_id=document_id, action="edit")
    return soft_delete_documento(session, user, document_id, expected_version=expected_version, motivo=motivo,
                                correlation_id=correlation_id, parent_module=MODULE)
