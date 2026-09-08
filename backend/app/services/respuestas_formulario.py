"""Fachada compatible para el guardado validado de respuestas dinámicas."""

from sqlalchemy.orm import Session

from app.core.permissions import AuthenticatedUser
from app.models import EnvioFormulario


def save_response(
    session: Session, user: AuthenticatedUser, id_formulario: str, *,
    draft: bool, respuestas: list[dict], id_envio_cliente: str | None = None,
    id_registro_proceso: str | None = None, contexto_tipo: str | None = None,
    contexto_id: str | None = None, id_respuesta: str | None = None,
    expected_version: int | None = None, correlation_id: str,
    crear_contexto: bool = False, id_persona: str | None = None,
    editar_registrado: bool = False,
) -> EnvioFormulario:
    from app.services.dynamic_responses import save_dynamic_response
    return save_dynamic_response(
        session, user, id_formulario, draft=draft, answers=respuestas,
        client_key=id_envio_cliente, legacy_record_id=id_registro_proceso,
        context_type=contexto_tipo, context_id=contexto_id, response_id=id_respuesta,
        expected_version=expected_version, correlation_id=correlation_id,
        create_context=crear_contexto, person_id=id_persona,
        edit_registered=editar_registrado,
    )
