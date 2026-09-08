"""Validación, borradores y lectura contextual de respuestas dinámicas."""

import json
import re
from collections import defaultdict
from uuid import uuid4

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, authorize, can
from app.core.time import utc_now_iso
from app.models import EnvioFormulario, Formulario, FormularioDestino, FormularioVersion, Persona, RespuestaFormulario
from app.services.audit import log_change
from app.services.form_builder import ensure_published_version, get_definition
from app.services.records import apply_soft_delete, check_expected_version, creation_metadata, get_active, mark_updated
from app.services.response_codes import assign_response_code
from app.services.response_contexts import (
    CONTEXT_MODELS, authorize_response_action, create_dynamic_context,
    delete_generated_context_if_orphaned, resolve_person_id, response_actions,
)
from app.services.sensitivity import is_sensitive_record

VALUE_FIELDS = ("valor_texto", "valor_numero", "valor_fecha", "valor_booleano", "valor_opcion")
SELECTION_TYPES = {"SI_NO", "SELECCION_UNICA", "LISTA_DESPLEGABLE", "SELECCION_MULTIPLE", "CASILLAS"}
NUMBER_TYPES = {"NUMERO", "NUMERO_ENTERO", "NUMERO_DECIMAL", "MONEDA", "PORCENTAJE", "ESCALA", "CALIFICACION"}
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _answer_value(answer: dict):
    values = [answer[field] for field in VALUE_FIELDS if field in answer and answer[field] is not None]
    if len(values) != 1:
        raise AppError("INVALID_ANSWER", "Cada respuesta debe contener exactamente un valor.", 422)
    return values[0]


def _operator_matches(operator: str, current, expected: str | None) -> bool:
    values = current if isinstance(current, list) else [current]
    text_values = [str(value).strip().lower() for value in values if value is not None]
    expected_text = str(expected or "").strip().lower()
    if operator == "EMPTY": return not text_values or all(not value for value in text_values)
    if operator == "NOT_EMPTY": return bool(text_values and any(text_values))
    if operator == "INCLUDES": return expected_text in text_values
    if operator == "NOT_INCLUDES": return expected_text not in text_values
    current_text = text_values[0] if text_values else ""
    if operator == "EQ": return current_text == expected_text
    if operator == "NE": return current_text != expected_text
    if operator == "CONTAINS": return expected_text in current_text
    if operator == "NOT_CONTAINS": return expected_text not in current_text
    try:
        left, right = float(current_text), float(expected_text)
    except ValueError:
        return False
    return {"GT": left > right, "GTE": left >= right, "LT": left < right, "LTE": left <= right}.get(operator, False)


def dynamic_state(definition: dict, answer_values: dict[str, list]) -> tuple[dict[str, bool], dict[str, bool], dict[str, bool]]:
    visible_questions = {q["id_pregunta"]: bool(q.get("visible", True)) for q in definition["preguntas"]}
    required_questions = {q["id_pregunta"]: bool(q.get("obligatoria", False)) for q in definition["preguntas"]}
    visible_sections = {s["id_seccion"]: True for s in definition["secciones"]}
    grouped: dict[tuple, list[bool]] = defaultdict(list)
    for rule in definition["reglas"]:
        key = (rule.get("id_pregunta_destino"), rule.get("id_seccion_destino"), rule.get("accion"), rule.get("grupo") or "TODAS")
        grouped[key].append(_operator_matches(rule.get("operador") or "EQ", answer_values.get(rule["id_pregunta_origen"], []), rule.get("valor_comparacion")))
    for (question_id, section_id, action, group), matches in grouped.items():
        satisfied = all(matches) if group == "TODAS" else any(matches)
        if action == "MOSTRAR" and question_id: visible_questions[question_id] = satisfied
        elif action == "OCULTAR" and question_id and satisfied: visible_questions[question_id] = False
        elif action == "OBLIGATORIA" and question_id: required_questions[question_id] = satisfied
        elif action == "OPCIONAL" and question_id and satisfied: required_questions[question_id] = False
        elif action == "MOSTRAR_SECCION" and section_id: visible_sections[section_id] = satisfied
        elif action == "OCULTAR_SECCION" and section_id and satisfied: visible_sections[section_id] = False
    for question in definition["preguntas"]:
        if question.get("id_seccion") and not visible_sections.get(question["id_seccion"], True):
            visible_questions[question["id_pregunta"]] = False
    return visible_questions, required_questions, visible_sections


def _validate_context(session: Session, user: AuthenticatedUser, form_id: str,
                      context_type: str | None, context_id: str | None) -> tuple[str, str | None]:
    normalized = (context_type or "GENERAL").strip().upper()
    destination = session.scalar(select(FormularioDestino).where(
        FormularioDestino.id_formulario == form_id, FormularioDestino.modulo == normalized,
        FormularioDestino.activo.is_(True), FormularioDestino.eliminado.is_(False),
    ))
    if destination is None:
        raise AppError("FORM_CONTEXT_NOT_ALLOWED", "El formulario no está disponible en este módulo.", 403)
    if normalized == "GENERAL":
        if context_id:
            raise AppError("INVALID_FORM_CONTEXT", "Un formulario general no admite contexto.", 422)
        return normalized, None
    model_info = CONTEXT_MODELS.get(normalized)
    if model_info is None or not context_id:
        raise AppError("INVALID_FORM_CONTEXT", "El contexto del formulario no es válido.", 422)
    model, id_field = model_info
    record = get_active(session, model, context_id, getattr(model, id_field))
    authorize(user, normalized, "read", sensitive=is_sensitive_record(session, record))
    return normalized, context_id


def _validate_answers(definition: dict, answers: list[dict], *, draft: bool) -> dict[str, list]:
    questions = {q["id_pregunta"]: q for q in definition["preguntas"]}
    values: dict[str, list] = defaultdict(list)
    for answer in answers:
        unknown = set(answer) - {"id_pregunta", *VALUE_FIELDS}
        if unknown or answer.get("id_pregunta") not in questions:
            raise AppError("INVALID_ANSWER", "La respuesta contiene una pregunta o campo no permitido.", 422)
        values[answer["id_pregunta"]].append(_answer_value(answer))
    visible, required, _ = dynamic_state(definition, values)
    if draft:
        return values
    for question_id, question in questions.items():
        if not visible.get(question_id, True):
            continue
        question_values = [v for v in values.get(question_id, []) if v not in (None, "", [])]
        if required.get(question_id, False) and not question_values:
            raise AppError("REQUIRED_ANSWER", f"El campo «{question['etiqueta']}» es obligatorio.", 422)
        if not question_values:
            continue
        question_type = (question.get("tipo") or "TEXTO_CORTO").upper()
        validation = question.get("validacion") or {}
        config = question.get("configuracion") or {}
        if question_type in SELECTION_TYPES and question_type != "SI_NO":
            allowed = {str(o["valor"]) for o in question.get("opciones", [])}
            if any(str(value) not in allowed for value in question_values):
                raise AppError("INVALID_OPTION", f"Seleccione una opción válida para «{question['etiqueta']}».", 422)
        if question_type in NUMBER_TYPES:
            try:
                numeric_values = [float(v) for v in question_values]
            except (TypeError, ValueError):
                raise AppError("INVALID_NUMBER", f"Ingrese un número válido en «{question['etiqueta']}».", 422) from None
            minimum, maximum = validation.get("min"), validation.get("max")
            if minimum not in (None, "") and any(v < float(minimum) for v in numeric_values):
                raise AppError("NUMBER_TOO_SMALL", f"El valor de «{question['etiqueta']}» es menor al permitido.", 422)
            if maximum not in (None, "") and any(v > float(maximum) for v in numeric_values):
                raise AppError("NUMBER_TOO_LARGE", f"El valor de «{question['etiqueta']}» supera el máximo permitido.", 422)
        text = str(question_values[0])
        min_length = validation.get("min_length")
        max_length = validation.get("max_length") or question.get("longitud_maxima")
        if min_length and len(text) < int(min_length):
            raise AppError("TEXT_TOO_SHORT", f"«{question['etiqueta']}» no alcanza la longitud mínima.", 422)
        if max_length and len(text) > int(max_length):
            raise AppError("TEXT_TOO_LONG", f"«{question['etiqueta']}» supera la longitud máxima.", 422)
        if question_type == "EMAIL" and not EMAIL_RE.match(text):
            raise AppError("INVALID_EMAIL", f"Ingrese un correo válido en «{question['etiqueta']}».", 422)
        if question_type == "PORCENTAJE" and any(float(v) < 0 or float(v) > 100 for v in question_values):
            raise AppError("INVALID_PERCENTAGE", "El porcentaje debe estar entre 0 y 100.", 422)
        if question_type in {"ARCHIVO", "FOTOGRAFIA"} and config.get("max_files") and len(question_values) > int(config["max_files"]):
            raise AppError("TOO_MANY_FILES", f"«{question['etiqueta']}» supera la cantidad máxima de archivos.", 422)
    return values


def _find_response(session: Session, user: AuthenticatedUser, form: Formulario, *,
                   response_id: str | None, client_key: str | None,
                   context_type: str, context_id: str | None) -> EnvioFormulario | None:
    if response_id:
        response = session.get(EnvioFormulario, response_id)
        if response is None or response.usuario_respuesta != user.correo or response.id_formulario != form.id_formulario:
            raise AppError("FORM_RESPONSE_NOT_FOUND", "Borrador no encontrado.", 404)
        return response
    if client_key:
        response = session.scalar(select(EnvioFormulario).where(
            EnvioFormulario.id_formulario == form.id_formulario,
            EnvioFormulario.usuario_respuesta == user.correo,
            EnvioFormulario.id_envio_cliente == client_key,
            EnvioFormulario.contexto_tipo == context_type,
            EnvioFormulario.contexto_id.is_(None) if context_id is None else EnvioFormulario.contexto_id == context_id,
            EnvioFormulario.eliminado.is_(False),
        ))
        if response:
            return response
    if not form.permite_multiples_respuestas:
        return session.scalar(select(EnvioFormulario).where(
            EnvioFormulario.id_formulario == form.id_formulario,
            EnvioFormulario.usuario_respuesta == user.correo,
            EnvioFormulario.contexto_tipo == context_type,
            EnvioFormulario.contexto_id.is_(None) if context_id is None else EnvioFormulario.contexto_id == context_id,
            EnvioFormulario.eliminado.is_(False),
        ).order_by(EnvioFormulario.fecha_respuesta.desc()))
    return None


def _find_response_by_identity(
    session: Session, user: AuthenticatedUser, form: Formulario, *,
    response_id: str | None, client_key: str | None,
) -> EnvioFormulario | None:
    """Resuelve primero la identidad del envío, antes de crear un contexto nuevo.

    La clave de cliente es única por usuario. Consultarla sin contexto mantiene la
    idempotencia aun cuando el primer intento haya creado transaccionalmente el contexto.
    """
    response = session.get(EnvioFormulario, response_id) if response_id else None
    if response_id and (response is None or response.eliminado or response.id_formulario != form.id_formulario):
        raise AppError("FORM_RESPONSE_NOT_FOUND", "Respuesta no encontrada.", 404)
    if response is None and client_key:
        response = session.scalar(select(EnvioFormulario).where(
            EnvioFormulario.usuario_respuesta == user.correo,
            EnvioFormulario.id_envio_cliente == client_key,
            EnvioFormulario.eliminado.is_(False),
        ))
        if response is not None and response.id_formulario != form.id_formulario:
            raise AppError("IDEMPOTENCY_KEY_CONFLICT", "La clave de envío ya fue utilizada en otro formulario.", 409)
    return response


def _version_definition(session: Session, response: EnvioFormulario) -> dict | None:
    if not response.id_version_formulario:
        return None
    version = session.get(FormularioVersion, response.id_version_formulario)
    if version is None or version.eliminado:
        return None
    try:
        return json.loads(version.definicion_json)
    except (TypeError, ValueError):
        return None


def save_dynamic_response(session: Session, user: AuthenticatedUser, form_id: str, *,
                          draft: bool, answers: list[dict], client_key: str | None = None,
                          legacy_record_id: str | None = None, context_type: str | None = None,
                          context_id: str | None = None, response_id: str | None = None,
                          expected_version: int | None = None, correlation_id: str = "",
                          create_context: bool = False, person_id: str | None = None,
                          edit_registered: bool = False) -> EnvioFormulario:
    authorize(user, "RESPUESTAS", "edit" if edit_registered else "create")
    form = session.get(Formulario, form_id)
    if form is None or form.eliminado or not form.activo:
        raise AppError("FORM_NOT_FOUND", "Formulario no encontrado.", 404)
    if not answers and not draft:
        raise AppError("EMPTY_RESPONSE", "El formulario no contiene respuestas para guardar.", 422)
    response = _find_response_by_identity(
        session, user, form, response_id=response_id, client_key=client_key,
    )
    if response is None and (form.estado or "").strip().upper() != "PUBLICADO":
        raise AppError("FORM_NOT_PUBLISHED", "El formulario no está publicado.", 422)
    inferred_type = response.contexto_tipo if response is not None else context_type
    inferred_id = response.contexto_id if response is not None else (context_id or legacy_record_id)
    context_created = bool(response and response.contexto_creado_dinamicamente)
    if legacy_record_id and not context_type:
        inferred_type = next((d.modulo for d in session.scalars(select(FormularioDestino).where(
            FormularioDestino.id_formulario == form_id, FormularioDestino.modulo != "GENERAL",
            FormularioDestino.eliminado.is_(False),
        ))), "GENERAL")
    if response is None and create_context:
        normalized_requested = (inferred_type or "GENERAL").strip().upper()
        inferred_id, context_created = create_dynamic_context(
            session, user, normalized_requested, person_id, correlation_id,
        )
        inferred_type = normalized_requested
    normalized_type, normalized_id = _validate_context(session, user, form_id, inferred_type, inferred_id)
    if response is None:
        response = _find_response(session, user, form, response_id=None, client_key=None,
                                  context_type=normalized_type, context_id=normalized_id)
    if response is not None and response.estado == "REGISTRADO":
        if edit_registered:
            if draft:
                raise AppError("INVALID_RESPONSE_STATE", "Una respuesta registrada no puede volver a borrador.", 422)
            authorize_response_action(session, user, response, "edit")
        elif not draft and client_key and response.id_envio_cliente == client_key:
            return response
        else:
            raise AppError("FORM_ALREADY_ANSWERED", "Este formulario ya fue respondido en el contexto actual.", 409)
    elif edit_registered:
        raise AppError("INVALID_RESPONSE_STATE", "Solo se pueden editar respuestas ya registradas.", 422)
    elif response is not None and response.usuario_respuesta != user.correo:
        raise AppError("FORBIDDEN", "No puede continuar el borrador de otro usuario.", 403)
    definition = _version_definition(session, response) if response is not None else None
    definition = definition or get_definition(session, form_id)
    _validate_answers(definition, answers, draft=draft)
    version = (session.get(FormularioVersion, response.id_version_formulario)
               if response is not None and response.id_version_formulario else None)
    version = version or ensure_published_version(session, form, user)
    new_state = "BORRADOR" if draft else "REGISTRADO"
    if response is None:
        response = EnvioFormulario(
            id_respuesta=str(uuid4()), id_formulario=form_id,
            id_version_formulario=version.id_version_formulario,
            usuario_respuesta=user.correo, id_envio_cliente=client_key,
            estado=new_state, fecha_respuesta=utc_now_iso(),
            id_registro_proceso=normalized_id, contexto_tipo=normalized_type,
            contexto_id=normalized_id, contexto_creado_dinamicamente=context_created,
            **creation_metadata(user.correo),
        )
        session.add(response)
        session.flush()
        audit_action = "CREATE"
    else:
        if expected_version is not None:
            check_expected_version(response, expected_version)
        for detail in session.scalars(select(RespuestaFormulario).where(
            RespuestaFormulario.id_respuesta == response.id_respuesta,
            RespuestaFormulario.eliminado.is_(False),
        )):
            detail.activo = False
            detail.eliminado = True
            detail.fecha_eliminacion = utc_now_iso()
            detail.usuario_eliminacion = user.correo
            detail.motivo_eliminacion = "Nueva versión de respuesta"
        response.estado = new_state
        response.fecha_respuesta = utc_now_iso()
        if not response.id_version_formulario:
            response.id_version_formulario = version.id_version_formulario
        mark_updated(response, user.correo)
        audit_action = "UPDATE"
    if new_state == "REGISTRADO":
        assign_response_code(session, response)
    for answer in answers:
        values = {field: answer[field] for field in VALUE_FIELDS if field in answer}
        session.add(RespuestaFormulario(id_detalle_respuesta=str(uuid4()),
                    id_respuesta=response.id_respuesta, id_pregunta=answer["id_pregunta"],
                    **creation_metadata(user.correo), **values))
    log_change(session, "envios_formulario", response.id_respuesta, audit_action, {},
               {"id_formulario": form_id, "estado": new_state, "contexto_tipo": normalized_type,
                "contexto_id": normalized_id, "cantidad_respuestas": len(answers),
                "codigo_respuesta": response.codigo_respuesta},
               user.correo, ("Edición de respuesta definitiva" if edit_registered else
                              "Guardado de borrador" if draft else "Envío final de formulario"),
               correlation_id, sensitive_record=True)
    return response


def serialize_response(
    session: Session, response: EnvioFormulario, *, include_answers: bool = False,
    user: AuthenticatedUser | None = None,
) -> dict:
    data = {"id_respuesta": response.id_respuesta, "id_formulario": response.id_formulario,
            "numero_secuencial": response.numero_secuencial, "codigo_respuesta": response.codigo_respuesta,
            "estado": response.estado, "fecha_respuesta": response.fecha_respuesta,
            "usuario_respuesta": response.usuario_respuesta, "contexto_tipo": response.contexto_tipo,
            "contexto_id": response.contexto_id, "version": response.version,
            "id_version_formulario": response.id_version_formulario,
            "contexto_creado_dinamicamente": response.contexto_creado_dinamicamente}
    if user is not None:
        data["acciones"] = response_actions(session, user, response)
    if include_answers:
        details = list(session.scalars(select(RespuestaFormulario).where(
            RespuestaFormulario.id_respuesta == response.id_respuesta,
            RespuestaFormulario.eliminado.is_(False),
        )))
        data["respuestas"] = [{"id_pregunta": d.id_pregunta,
            **{field: getattr(d, field) for field in VALUE_FIELDS if getattr(d, field) is not None}}
            for d in details]
    return data


def context_forms(session: Session, user: AuthenticatedUser, context_type: str,
                  context_id: str) -> list[dict]:
    normalized = context_type.strip().upper()
    model_info = CONTEXT_MODELS.get(normalized)
    if model_info is None:
        raise AppError("INVALID_FORM_CONTEXT", "El contexto solicitado no existe.", 422)
    model, id_field = model_info
    record = get_active(session, model, context_id, getattr(model, id_field))
    authorize(user, normalized, "read", sensitive=is_sensitive_record(session, record))
    forms = list(session.scalars(select(Formulario).join(
        FormularioDestino, FormularioDestino.id_formulario == Formulario.id_formulario,
    ).where(FormularioDestino.modulo == normalized, FormularioDestino.activo.is_(True),
            FormularioDestino.eliminado.is_(False), Formulario.estado == "PUBLICADO",
            Formulario.activo.is_(True), Formulario.eliminado.is_(False)).order_by(Formulario.nombre)))
    result = []
    for form in forms:
        response = session.scalar(select(EnvioFormulario).where(
            EnvioFormulario.id_formulario == form.id_formulario,
            EnvioFormulario.usuario_respuesta == user.correo,
            EnvioFormulario.contexto_tipo == normalized,
            EnvioFormulario.contexto_id == context_id,
            EnvioFormulario.eliminado.is_(False),
        ).order_by(EnvioFormulario.fecha_respuesta.desc()))
        definition = get_definition(session, form.id_formulario)
        item = {**(serialize_response(session, response, user=user) if response else {}),
                "id_formulario": form.id_formulario, "nombre": form.nombre,
                "descripcion": form.descripcion, "estado_respuesta": response.estado if response else "PENDIENTE",
                "total_preguntas": definition["total_preguntas"],
                "permite_multiples_respuestas": form.permite_multiples_respuestas,
                "puede_crear": can(user, "RESPUESTAS", "create") and can(user, normalized, "create")}
        result.append(item)
    return result


def get_user_response(session: Session, user: AuthenticatedUser, response_id: str) -> dict:
    response = get_active(session, EnvioFormulario, response_id, EnvioFormulario.id_respuesta)
    authorize_response_action(session, user, response, "read")
    data = serialize_response(session, response, include_answers=True, user=user)
    person_id = resolve_person_id(session, response.contexto_tipo, response.contexto_id)
    person = session.get(Persona, person_id) if person_id else None
    data["id_persona"] = person.id_persona if person else None
    data["persona"] = person.nombre if person else None
    data["definicion"] = _version_definition(session, response) or get_definition(session, response.id_formulario)
    return data


def soft_delete_dynamic_response(
    session: Session, user: AuthenticatedUser, response_id: str, *,
    expected_version: int | None, reason: str, correlation_id: str = "",
) -> EnvioFormulario:
    response = get_active(session, EnvioFormulario, response_id, EnvioFormulario.id_respuesta)
    authorize_response_action(session, user, response, "delete")
    check_expected_version(response, expected_version)
    previous = serialize_response(session, response)
    apply_soft_delete(response, user.correo, reason)
    mark_updated(response, user.correo)
    log_change(
        session, "envios_formulario", response.id_respuesta, "DELETE", previous,
        {"codigo_respuesta": response.codigo_respuesta, "estado": response.estado},
        user.correo, reason, correlation_id, sensitive_record=True,
    )
    delete_generated_context_if_orphaned(session, user, response, reason, correlation_id)
    return response
