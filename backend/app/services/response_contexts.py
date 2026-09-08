"""Contextos reales y autorización compartida para respuestas dinámicas."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, authorize, can
from app.core.time import ecuador_now
from app.models import Atencion, Caso, EnvioFormulario, Novedad, Persona, Recorrido
from app.services.atenciones import create_atencion, soft_delete_atencion
from app.services.casos import create_caso, soft_delete_caso
from app.services.novedades import novedades
from app.services.records import get_active
from app.services.recorridos import recorridos
from app.services.sensitivity import is_sensitive_record

CONTEXT_MODELS = {
    "CASOS": (Caso, "id_caso"),
    "ATENCIONES": (Atencion, "id_atencion"),
    "NOVEDADES": (Novedad, "id_novedad"),
    "RECORRIDOS": (Recorrido, "id_recorrido"),
    "PERSONAS": (Persona, "id_persona"),
}


def get_context_record(session: Session, context_type: str, context_id: str, *, include_deleted: bool = False):
    info = CONTEXT_MODELS.get(context_type)
    if info is None:
        raise AppError("INVALID_FORM_CONTEXT", "El contexto del formulario no es válido.", 422)
    model, id_field = info
    return get_active(session, model, context_id, getattr(model, id_field), include_deleted=include_deleted)


def resolve_person_id(session: Session, context_type: str | None, context_id: str | None) -> str | None:
    normalized = (context_type or "GENERAL").strip().upper()
    if normalized == "PERSONAS":
        return context_id
    if normalized == "GENERAL" or not context_id:
        return None
    record = get_context_record(session, normalized, context_id, include_deleted=True)
    return getattr(record, "id_persona", None)


def create_dynamic_context(
    session: Session, user: AuthenticatedUser, context_type: str, person_id: str | None, correlation_id: str,
) -> tuple[str, bool]:
    normalized = context_type.strip().upper()
    person = None
    if person_id:
        authorize(user, "PERSONAS", "read")
        person = get_active(session, Persona, person_id, Persona.id_persona)
    if normalized == "PERSONAS":
        if person is None:
            raise AppError("PERSON_REQUIRED", "Seleccione la Persona para registrar el formulario.", 422)
        return person.id_persona, False

    today = ecuador_now().date().isoformat()
    common = {"id_persona": person.id_persona if person else None, "responsable": user.nombre}
    if normalized == "CASOS":
        record = create_caso(
            session, user, motivo_auditoria="Contexto creado desde formulario dinámico",
            correlation_id=correlation_id, fecha_apertura=today, colaborador=person.nombre if person else None,
            estado_caso="ABIERTO", **common,
        )
        return record.id_caso, True
    if normalized == "ATENCIONES":
        record = create_atencion(
            session, user, motivo_auditoria="Contexto creado desde formulario dinámico",
            correlation_id=correlation_id, fecha=today, colaborador=person.nombre if person else None,
            estado="ABIERTO", **common,
        )
        return record.id_atencion, True
    if normalized == "NOVEDADES":
        record = novedades.create(
            session, user, motivo_auditoria="Contexto creado desde formulario dinámico",
            correlation_id=correlation_id, fecha=today, estado="ABIERTO", **common,
        )
        return record.id_novedad, True
    if normalized == "RECORRIDOS":
        record = recorridos.create(
            session, user, motivo_auditoria="Contexto creado desde formulario dinámico",
            correlation_id=correlation_id, fecha=today, **common,
        )
        return record.id_recorrido, True
    raise AppError("INVALID_FORM_CONTEXT", "El módulo no admite nuevos registros dinámicos.", 422)


def response_action_allowed(session: Session, user: AuthenticatedUser, response: EnvioFormulario, action: str) -> bool:
    if not can(user, "RESPUESTAS", action):
        return False
    normalized = (response.contexto_tipo or "GENERAL").strip().upper()
    if normalized == "GENERAL":
        return True
    if not can(user, normalized, action):
        return False
    try:
        record = get_context_record(session, normalized, response.contexto_id or "", include_deleted=True)
    except AppError:
        return False
    if is_sensitive_record(session, record):
        return can(user, normalized, "sensitive")
    return True


def authorize_response_action(
    session: Session, user: AuthenticatedUser, response: EnvioFormulario, action: str,
) -> None:
    if not response_action_allowed(session, user, response, action):
        raise AppError("FORBIDDEN", "No tiene permisos para realizar esta acción sobre la respuesta.", 403)


def response_actions(session: Session, user: AuthenticatedUser, response: EnvioFormulario) -> dict[str, bool]:
    draft = response.estado == "BORRADOR"
    return {
        "ver": not draft and response_action_allowed(session, user, response, "read"),
        "continuar": draft and response.usuario_respuesta == user.correo
                      and response_action_allowed(session, user, response, "create"),
        "editar": not draft and response_action_allowed(session, user, response, "edit"),
        "eliminar": response_action_allowed(session, user, response, "delete"),
    }


def delete_generated_context_if_orphaned(
    session: Session, user: AuthenticatedUser, response: EnvioFormulario, reason: str, correlation_id: str,
) -> None:
    if not response.contexto_creado_dinamicamente or not response.contexto_id:
        return
    remaining = session.scalar(select(func.count()).select_from(EnvioFormulario).where(
        EnvioFormulario.id_respuesta != response.id_respuesta,
        EnvioFormulario.contexto_tipo == response.contexto_tipo,
        EnvioFormulario.contexto_id == response.contexto_id,
        EnvioFormulario.eliminado.is_(False),
    ))
    if remaining:
        return
    normalized = (response.contexto_tipo or "").upper()
    record = get_context_record(session, normalized, response.contexto_id)
    if normalized == "CASOS":
        soft_delete_caso(session, user, response.contexto_id, expected_version=record.version,
                         motivo=reason, correlation_id=correlation_id)
    elif normalized == "ATENCIONES":
        soft_delete_atencion(session, user, response.contexto_id, expected_version=record.version,
                             motivo=reason, correlation_id=correlation_id)
    elif normalized == "NOVEDADES":
        novedades.soft_delete(session, user, response.contexto_id, expected_version=record.version,
                              motivo=reason, correlation_id=correlation_id)
    elif normalized == "RECORRIDOS":
        recorridos.soft_delete(session, user, response.contexto_id, expected_version=record.version,
                               motivo=reason, correlation_id=correlation_id)


def dynamic_context_ids(module: str):
    return select(EnvioFormulario.contexto_id).where(
        EnvioFormulario.contexto_tipo == module,
        EnvioFormulario.contexto_creado_dinamicamente.is_(True),
        EnvioFormulario.eliminado.is_(False),
    )
