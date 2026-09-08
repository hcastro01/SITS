"""Selección de formularios y vistas consolidadas por módulo/Persona."""

from math import ceil

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, authorize, can
from app.models import (
    Atencion, Caso, Catalogo, EnvioFormulario, Formulario, FormularioDestino, Novedad,
    Persona, Pregunta, Recorrido,
)
from app.services.dynamic_responses import serialize_response
from app.services.records import get_active
from app.services.response_contexts import (
    CONTEXT_MODELS, get_context_record, resolve_person_id, response_action_allowed,
)
from app.services.sensitivity import is_sensitive_record

MODULES = ("CASOS", "ATENCIONES", "NOVEDADES", "RECORRIDOS", "PERSONAS")


def _module(value: str) -> str:
    normalized = value.strip().upper()
    if normalized not in MODULES:
        raise AppError("INVALID_MODULE", "El módulo indicado no admite formularios dinámicos.", 422)
    return normalized


def list_available_forms(session: Session, user: AuthenticatedUser, module: str) -> list[dict]:
    normalized = _module(module)
    authorize(user, normalized, "create")
    authorize(user, "RESPUESTAS", "create")
    question_counts = (
        select(Pregunta.id_formulario, func.count(Pregunta.id_pregunta).label("total"))
        .where(Pregunta.activo.is_(True), Pregunta.eliminado.is_(False))
        .group_by(Pregunta.id_formulario).subquery()
    )
    rows = session.execute(
        select(Formulario, func.coalesce(question_counts.c.total, 0))
        .join(FormularioDestino, FormularioDestino.id_formulario == Formulario.id_formulario)
        .outerjoin(question_counts, question_counts.c.id_formulario == Formulario.id_formulario)
        .where(
            FormularioDestino.modulo == normalized,
            FormularioDestino.activo.is_(True), FormularioDestino.eliminado.is_(False),
            Formulario.estado == "PUBLICADO", Formulario.activo.is_(True),
            Formulario.eliminado.is_(False),
        ).order_by(Formulario.nombre)
    ).all()
    return [{
        "id_formulario": form.id_formulario, "nombre": form.nombre,
        "descripcion": form.descripcion, "total_preguntas": int(total),
        "permite_multiples_respuestas": form.permite_multiples_respuestas,
    } for form, total in rows]


def _person_for_response(session: Session, response: EnvioFormulario) -> Persona | None:
    try:
        person_id = resolve_person_id(session, response.contexto_tipo, response.contexto_id)
    except AppError:
        return None
    return session.get(Persona, person_id) if person_id else None


def _response_item(session: Session, user: AuthenticatedUser, response: EnvioFormulario) -> dict:
    form = session.get(Formulario, response.id_formulario)
    person = _person_for_response(session, response)
    return {
        **serialize_response(session, response, user=user),
        "tipo_registro": "FORMULARIO",
        "formulario": form.nombre if form else "Formulario no disponible",
        "id_persona": person.id_persona if person else None,
        "persona": person.nombre if person else None,
        "responsable": response.usuario_respuesta,
    }


def list_module_responses(
    session: Session, user: AuthenticatedUser, module: str, *, state: str | None,
    page: int, page_size: int,
) -> dict:
    normalized = _module(module)
    authorize(user, normalized, "read")
    authorize(user, "RESPUESTAS", "read")
    conditions = [
        EnvioFormulario.contexto_tipo == normalized,
        EnvioFormulario.eliminado.is_(False),
    ]
    if state and state.strip():
        conditions.append(EnvioFormulario.estado == state.strip().upper())
    if normalized == "CASOS" and not can(user, "CASOS", "sensitive"):
        sensitive_values = {
            str(value).strip().upper() for row in session.scalars(select(Catalogo).where(
                Catalogo.tipo == "NIVEL_SENSIBILIDAD", Catalogo.es_sensible.is_(True),
                Catalogo.eliminado.is_(False),
            )) for value in (row.codigo, row.valor) if value
        }
        if sensitive_values:
            sensitive_contexts = select(Caso.id_caso).where(
                func.upper(Caso.nivel_sensibilidad).in_(sensitive_values),
            )
            conditions.append(EnvioFormulario.contexto_id.not_in(sensitive_contexts))
    total = int(session.scalar(select(func.count()).select_from(EnvioFormulario).where(*conditions)) or 0)
    rows = list(session.scalars(
        select(EnvioFormulario).where(*conditions)
        .order_by(EnvioFormulario.fecha_respuesta.desc(), EnvioFormulario.id_respuesta)
        .offset((page - 1) * page_size).limit(page_size)
    ))
    visible = [row for row in rows if response_action_allowed(session, user, row, "read")]
    return {
        "items": [_response_item(session, user, row) for row in visible],
        "pagina": page, "tamano_pagina": page_size, "total": total,
        "total_paginas": ceil(total / page_size) if total else 0,
    }


def _base_item(module: str, record, person: Persona, user: AuthenticatedUser) -> dict:
    id_field = CONTEXT_MODELS[module][1]
    state_field = "estado_caso" if module == "CASOS" else "estado"
    date_field = "fecha_apertura" if module == "CASOS" else "fecha"
    return {
        "tipo_registro": "REGISTRO_BASE", "contexto_tipo": module,
        "contexto_id": getattr(record, id_field),
        "codigo_respuesta": getattr(record, "codigo_caso", None),
        "formulario": None, "estado": getattr(record, state_field, None),
        "fecha_respuesta": getattr(record, date_field, None),
        "responsable": getattr(record, "responsable", None),
        "id_persona": person.id_persona, "persona": person.nombre,
        "version": record.version,
        "acciones": {
            "ver": can(user, module, "read"), "continuar": False,
            "editar": can(user, module, "edit"), "eliminar": can(user, module, "delete"),
        },
    }


def person_records(
    session: Session, user: AuthenticatedUser, person_id: str, *, module: str | None,
    state: str | None, page: int, page_size: int,
) -> dict:
    authorize(user, "PERSONAS", "read")
    person = get_active(session, Persona, person_id, Persona.id_persona)
    responses_only = (module or "").strip().upper() == "FORMULARIOS"
    selected_modules = list(MODULES) if responses_only or not module else [_module(module)]
    items: list[dict] = []

    if can(user, "RESPUESTAS", "read"):
        context_conditions = [
            (EnvioFormulario.contexto_tipo == "PERSONAS") & (EnvioFormulario.contexto_id == person_id)
        ]
        for name, (model, id_field) in CONTEXT_MODELS.items():
            if name == "PERSONAS" or name not in selected_modules or not can(user, name, "read"):
                continue
            linked_ids = select(getattr(model, id_field)).where(
                getattr(model, "id_persona") == person_id,
                model.eliminado.is_(False),
            )
            context_conditions.append(
                (EnvioFormulario.contexto_tipo == name) & (EnvioFormulario.contexto_id.in_(linked_ids))
            )
        response_stmt = select(EnvioFormulario).where(
            EnvioFormulario.eliminado.is_(False), or_(*context_conditions),
            EnvioFormulario.contexto_tipo.in_(selected_modules),
        )
        if state and state.strip():
            response_stmt = response_stmt.where(EnvioFormulario.estado == state.strip().upper())
        for response in session.scalars(response_stmt):
            if response_action_allowed(session, user, response, "read"):
                items.append(_response_item(session, user, response))

    if not state and not responses_only:
        for name in selected_modules:
            if name == "PERSONAS" or not can(user, name, "read"):
                continue
            model, id_field = CONTEXT_MODELS[name]
            generated_ids = select(EnvioFormulario.contexto_id).where(
                EnvioFormulario.contexto_tipo == name,
                EnvioFormulario.contexto_creado_dinamicamente.is_(True),
            )
            stmt = select(model).where(
                model.id_persona == person_id, model.eliminado.is_(False),
                getattr(model, id_field).not_in(generated_ids),
            )
            for record in session.scalars(stmt):
                if not is_sensitive_record(session, record) or can(user, name, "sensitive"):
                    items.append(_base_item(name, record, person, user))

    items.sort(key=lambda item: (item.get("fecha_respuesta") or "", item.get("contexto_id") or ""), reverse=True)
    total = len(items)
    start = (page - 1) * page_size
    return {
        "persona": {"id_persona": person.id_persona, "nombre": person.nombre,
                    "codigo_empleado": person.codigo_empleado, "cedula": person.cedula},
        "items": items[start:start + page_size], "pagina": page,
        "tamano_pagina": page_size, "total": total,
        "total_paginas": ceil(total / page_size) if total else 0,
    }


def response_by_code(session: Session, user: AuthenticatedUser, code: str) -> dict:
    normalized = code.strip().upper()
    response = session.scalar(select(EnvioFormulario).where(
        EnvioFormulario.codigo_respuesta == normalized,
        EnvioFormulario.eliminado.is_(False),
    ))
    if response is None:
        raise AppError("FORM_RESPONSE_NOT_FOUND", "No existe una respuesta con ese código.", 404)
    if not response_action_allowed(session, user, response, "read"):
        raise AppError("FORM_RESPONSE_NOT_FOUND", "No existe una respuesta con ese código.", 404)
    return _response_item(session, user, response)
