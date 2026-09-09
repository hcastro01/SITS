"""Router de Formularios, Preguntas, Opciones, Reglas y Respuestas."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.permissions import AuthenticatedUser, authorize, can
from app.models import EnvioFormulario, Formulario, Pregunta
from app.services.dynamic_responses import (
    context_forms, get_user_response, serialize_response, soft_delete_dynamic_response,
)
from app.services.form_integrations import list_available_forms, list_module_responses
from app.services.form_builder import duplicate_form, get_definition, list_forms, save_definition, serialize_form
from app.services.form_search import list_sources, search_options
from app.services.formularios import CAMPOS as CAMPOS_FORMULARIO
from app.services.formularios import MODULE as FORMULARIOS_MODULE
from app.services.formularios import change_status, create_formulario, soft_delete_formulario, update_formulario
from app.services.opciones_pregunta import opciones_pregunta
from app.services.preguntas import preguntas
from app.services.records import get_active
from app.services.reglas_formulario import reglas_formulario
from app.services.respuestas_formulario import save_response
from app.services.response_contexts import response_action_allowed

router = APIRouter(prefix="/api/v1/formularios", tags=["Formularios"])


def _with_actions(data: dict, user: AuthenticatedUser) -> dict:
    return {**data, "acciones": {"eliminar": can(user, FORMULARIOS_MODULE, "delete")}}


def _serialize_formulario(record: Formulario, user: AuthenticatedUser) -> dict:
    return _with_actions(serialize_form(record), user)


@router.get("/fuentes-busqueda")
def fuentes_busqueda(user: AuthenticatedUser = Depends(get_current_user)):
    return list_sources(user)


@router.get("/search-options")
def buscar_opciones(
    source: str, q: str = Query("", max_length=100), limit: int = Query(15, ge=1, le=20),
    tipo_catalogo: str | None = None, browse: bool = False,
    selected_id: str | None = Query(None, max_length=100),
    db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user),
):
    return search_options(
        db, user, source, q, limit=limit, catalog_type=tipo_catalogo,
        browse=browse, selected_id=selected_id,
    )


@router.get("/contexto/{contexto_tipo}/{contexto_id}")
def formularios_contexto(
    contexto_tipo: str, contexto_id: str, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    return context_forms(db, user, contexto_tipo, contexto_id)


@router.get("/disponibles/{modulo}")
def formularios_disponibles(
    modulo: str, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    return list_available_forms(db, user, modulo)


@router.get("/modulo/{modulo}/respuestas")
def respuestas_modulo(
    modulo: str, estado: str | None = None,
    pagina: int = Query(1, ge=1), tamano_pagina: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user),
):
    return list_module_responses(
        db, user, modulo, state=estado, page=pagina, page_size=tamano_pagina,
    )


@router.get("/respuestas/{id_respuesta}")
def obtener_respuesta(
    id_respuesta: str, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    return get_user_response(db, user, id_respuesta)


@router.post("/respuestas/{id_respuesta}/eliminacion")
def eliminar_respuesta(
    id_respuesta: str, payload: dict, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    response = soft_delete_dynamic_response(
        db, user, id_respuesta, expected_version=payload.get("expected_version"),
        reason=payload.get("motivo") or payload.get("reason") or "",
        correlation_id=payload.get("correlation_id", ""),
    )
    return serialize_response(db, response, user=user)


@router.get("/{id_formulario}/respuestas")
def listar_respuestas(
    id_formulario: str, estado: str | None = None,
    q: str | None = Query(None, max_length=40),
    db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user),
):
    authorize(user, "RESPUESTAS", "read")
    stmt = select(EnvioFormulario).where(
        EnvioFormulario.id_formulario == id_formulario, EnvioFormulario.eliminado.is_(False),
    ).order_by(EnvioFormulario.fecha_respuesta.desc())
    if estado:
        stmt = stmt.where(EnvioFormulario.estado == estado.strip().upper())
    if q and q.strip():
        stmt = stmt.where(EnvioFormulario.codigo_respuesta.contains(q.strip().upper()))
    return [serialize_response(db, row, user=user) for row in db.scalars(stmt.limit(200))
            if not row.eliminado and response_action_allowed(db, user, row, "read")]


@router.get("")
def listar(
    db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user),
    incluir_eliminados: bool = False, limite: int = Query(50, le=200), offset: int = Query(0, ge=0),
):
    authorize(user, FORMULARIOS_MODULE, "read")
    if incluir_eliminados:
        stmt = select(Formulario).offset(offset).limit(limite)
        return [_serialize_formulario(r, user) for r in db.scalars(stmt)]
    return [_with_actions(item, user) for item in list_forms(db)[offset:offset + limite]]


@router.get("/{id_formulario}")
def obtener(id_formulario: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    authorize(user, FORMULARIOS_MODULE, "read")
    return _with_actions(get_definition(db, id_formulario), user)


@router.post("", status_code=201)
def crear(payload: dict, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    payload = dict(payload)
    destinos = payload.pop("destinos", None)
    motivo = payload.pop("motivo_auditoria", None) or "Alta de formulario"
    correlation_id = payload.pop("correlation_id", "")
    registro = create_formulario(db, user, motivo_auditoria=motivo, correlation_id=correlation_id,
                                 destinos=destinos, **payload)
    return _with_actions(get_definition(db, registro.id_formulario), user)


@router.put("/{id_formulario}/definicion")
def guardar_definicion(
    id_formulario: str, payload: dict, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    return _with_actions(
        save_definition(db, user, id_formulario, dict(payload),
                        correlation_id=payload.get("correlation_id", "")),
        user,
    )


@router.post("/{id_formulario}/duplicar", status_code=201)
def duplicar(
    id_formulario: str, payload: dict | None = None, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    record = duplicate_form(db, user, id_formulario,
                            correlation_id=(payload or {}).get("correlation_id", ""))
    return _with_actions(get_definition(db, record.id_formulario), user)


@router.patch("/{id_formulario}")
def actualizar(
    id_formulario: str, payload: dict, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    payload = dict(payload)
    expected_version = payload.pop("expected_version", None)
    motivo = payload.pop("motivo_auditoria", None) or "Edición de formulario"
    correlation_id = payload.pop("correlation_id", "")
    registro = update_formulario(db, user, id_formulario, expected_version=expected_version,
                                  motivo_auditoria=motivo, correlation_id=correlation_id, **payload)
    return _serialize_formulario(registro, user)


@router.patch("/{id_formulario}/estado")
def cambiar_estado(
    id_formulario: str, payload: dict, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    registro = change_status(
        db, user, id_formulario, payload["estado"],
        expected_version=payload.get("expected_version"), correlation_id=payload.get("correlation_id", ""),
    )
    return _serialize_formulario(registro, user)


@router.post("/{id_formulario}/eliminacion")
def eliminar_formulario(
    id_formulario: str, payload: dict, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    registro = soft_delete_formulario(
        db, user, id_formulario, expected_version=payload.get("expected_version"),
        motivo=payload.get("motivo") or payload.get("reason") or "",
        correlation_id=payload.get("correlation_id", ""),
    )
    return _serialize_formulario(registro, user)


@router.post("/{id_formulario}/preguntas", status_code=201)
def crear_pregunta(
    id_formulario: str, payload: dict, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    payload = dict(payload)
    motivo = payload.pop("motivo_auditoria", None) or "Alta de pregunta"
    correlation_id = payload.pop("correlation_id", "")
    registro = preguntas.create(db, user, motivo_auditoria=motivo, correlation_id=correlation_id,
                                 id_formulario=id_formulario, **payload)
    return preguntas.serialize(registro)


@router.patch("/preguntas/{id_pregunta}")
def actualizar_pregunta(
    id_pregunta: str, payload: dict, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    payload = dict(payload)
    expected_version = payload.pop("expected_version", None)
    motivo = payload.pop("motivo_auditoria", None) or "Edición de pregunta"
    correlation_id = payload.pop("correlation_id", "")
    registro = preguntas.update(db, user, id_pregunta, expected_version=expected_version,
                                 motivo_auditoria=motivo, correlation_id=correlation_id, **payload)
    return preguntas.serialize(registro)


@router.post("/preguntas/{id_pregunta}/opciones", status_code=201)
def crear_opcion(
    id_pregunta: str, payload: dict, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    payload = dict(payload)
    motivo = payload.pop("motivo_auditoria", None) or "Alta de opción"
    correlation_id = payload.pop("correlation_id", "")
    registro = opciones_pregunta.create(db, user, motivo_auditoria=motivo, correlation_id=correlation_id,
                                         id_pregunta=id_pregunta, **payload)
    return opciones_pregunta.serialize(registro)


@router.post("/{id_formulario}/reglas", status_code=201)
def crear_regla(
    id_formulario: str, payload: dict, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    payload = dict(payload)
    motivo = payload.pop("motivo_auditoria", None) or "Alta de regla"
    correlation_id = payload.pop("correlation_id", "")
    registro = reglas_formulario.create(db, user, motivo_auditoria=motivo, correlation_id=correlation_id,
                                         id_formulario=id_formulario, **payload)
    return reglas_formulario.serialize(registro)


@router.post("/{id_formulario}/respuestas", status_code=201)
def responder(
    id_formulario: str, payload: dict, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    envio = save_response(
        db, user, id_formulario,
        draft=bool(payload.get("borrador", False)),
        respuestas=payload.get("respuestas", []),
        id_envio_cliente=payload.get("id_envio_cliente"),
        id_registro_proceso=payload.get("id_registro_proceso"),
        contexto_tipo=payload.get("contexto_tipo"), contexto_id=payload.get("contexto_id"),
        id_respuesta=payload.get("id_respuesta"), expected_version=payload.get("expected_version"),
        crear_contexto=bool(payload.get("crear_contexto", False)), id_persona=payload.get("id_persona"),
        editar_registrado=bool(payload.get("editar_registrado", False)),
        correlation_id=payload.get("correlation_id", ""),
    )
    return serialize_response(db, envio, user=user)
