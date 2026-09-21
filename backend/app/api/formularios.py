"""Router de Formularios, Preguntas, Opciones, Reglas y Respuestas."""

import json
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, Field, StrictBool, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile

from app.api.deps import get_current_user, get_db
from app.core.permissions import AuthenticatedUser, authorize, can
from app.models import EnvioFormulario, Formulario, Pregunta, RespuestaDocumento, RespuestaFormulario
from app.services.dynamic_responses import (
    context_forms, get_user_response, serialize_response, soft_delete_dynamic_response,
)
from app.services.form_integrations import list_available_forms, list_module_responses
from app.services.form_destinations import (
    list_active_destinations, list_destination_responses, list_destination_tree,
    list_form_destinations, set_form_destinations,
)
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
from app.services.documentos import MAX_FILE_BYTES, content_response_headers, download_documento

router = APIRouter(prefix="/api/v1/formularios", tags=["Formularios"])


class CambiarEstadoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    estado: Literal["BORRADOR", "PUBLICADO", "INACTIVO", "ARCHIVADO"]
    expected_version: int


class ResponderFormularioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    borrador: StrictBool = False
    respuestas: list[dict] = Field(default_factory=list)
    id_envio_cliente: str | None = None
    id_registro_proceso: str | None = None
    contexto_tipo: str | None = None
    contexto_id: str | None = None
    id_respuesta: str | None = None
    expected_version: int | None = None
    crear_contexto: StrictBool = False
    id_persona: str | None = None
    editar_registrado: StrictBool = False
    id_destino_respuesta: str | None = None
    # Backward-compatible input: these server-owned values are accepted but
    # intentionally never forwarded to save_response.
    codigo_respuesta: str | None = None
    numero_secuencial: int | None = None


async def response_request_payload(request: Request) -> tuple[ResponderFormularioRequest, list[dict]]:
    """Lee JSON histórico o multipart con `payload` JSON y `archivo:<pregunta>` repetible."""
    try:
        if "multipart/form-data" not in (request.headers.get("content-type") or ""):
            return ResponderFormularioRequest.model_validate(await request.json()), []
        form = await request.form()
        raw_payload = form.get("payload")
        if not isinstance(raw_payload, str):
            raise ValueError("El envío multipart requiere el campo payload.")
        payload = ResponderFormularioRequest.model_validate_json(raw_payload)
    except ValidationError as error:
        raise RequestValidationError(error.errors()) from error
    attachments = []
    for name, value in form.multi_items():
        if not name.startswith("archivo:") or not isinstance(value, UploadFile):
            continue
        question_id = name.removeprefix("archivo:")
        if not question_id:
            raise ValueError("Cada adjunto requiere una pregunta.")
        try:
            contenido = await value.read(MAX_FILE_BYTES + 1)
        finally:
            await value.close()
        attachments.append({"id_pregunta": question_id, "nombre_archivo": value.filename or "archivo",
                            "mime_type": value.content_type or "", "contenido": contenido})
    return payload, attachments


class DestinosFormularioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destino_ids: list[str] = Field(default_factory=list)
    correlation_id: str = ""


def _with_actions(data: dict, user: AuthenticatedUser) -> dict:
    return {**data, "acciones": {"eliminar": can(user, FORMULARIOS_MODULE, "delete")}}


def _serialize_formulario(record: Formulario, user: AuthenticatedUser) -> dict:
    return _with_actions(serialize_form(record), user)


@router.get("/fuentes-busqueda")
def fuentes_busqueda(user: AuthenticatedUser = Depends(get_current_user)):
    return list_sources(user)


@router.get("/destinos")
def destinos_arbol(
    solo_activos: bool = True, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    return list_destination_tree(db, user, active_only=solo_activos)


@router.get("/destinos/activos")
def destinos_activos(db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return list_active_destinations(db, user)


@router.get("/destinos/{id_destino}/respuestas")
def respuestas_destino(
    id_destino: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user),
):
    return [serialize_response(db, response, user=user) for response in list_destination_responses(db, user, id_destino)]


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


@router.get("/respuestas/{id_respuesta}/adjuntos/{id_archivo}/contenido")
def descargar_adjunto_respuesta(id_respuesta: str, id_archivo: str, request: Request,
                                db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    response = get_active(db, EnvioFormulario, id_respuesta, EnvioFormulario.id_respuesta)
    from app.services.response_contexts import authorize_response_action
    authorize_response_action(db, user, response, "read")
    linked = db.scalar(select(RespuestaDocumento.id_respuesta_documento).join(
        RespuestaFormulario, RespuestaFormulario.id_detalle_respuesta == RespuestaDocumento.id_detalle_respuesta,
    ).where(RespuestaFormulario.id_respuesta == id_respuesta, RespuestaFormulario.eliminado.is_(False),
            RespuestaDocumento.id_archivo == id_archivo))
    if linked is None:
        from app.core.errors import AppError
        raise AppError("FORM_ATTACHMENT_NOT_FOUND", "El adjunto no pertenece a esta respuesta.", 404)
    document, content = download_documento(db, user, id_archivo, correlation_id=request.state.correlation_id)
    return Response(content=content, media_type=document.mime_type, headers=content_response_headers(document.nombre_archivo))


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
    incluir_eliminados: bool = False, limite: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
):
    authorize(user, FORMULARIOS_MODULE, "read")
    if incluir_eliminados:
        authorize(user, FORMULARIOS_MODULE, "delete")
        stmt = select(Formulario).offset(offset).limit(limite)
        return [_serialize_formulario(r, user) for r in db.scalars(stmt)]
    return [_with_actions(item, user) for item in list_forms(db)[offset:offset + limite]]


@router.get("/{id_formulario}")
def obtener(id_formulario: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    authorize(user, FORMULARIOS_MODULE, "read")
    return _with_actions(get_definition(db, id_formulario), user)


@router.get("/{id_formulario}/destinos")
def destinos_formulario(
    id_formulario: str, incluir_inactivos: bool = False, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    return list_form_destinations(db, user, id_formulario, include_inactive=incluir_inactivos)


@router.put("/{id_formulario}/destinos")
def guardar_destinos_formulario(
    id_formulario: str, payload: DestinosFormularioRequest, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    return set_form_destinations(
        db, user, id_formulario, payload.destino_ids, correlation_id=payload.correlation_id,
    )


@router.post("", status_code=201)
def crear(payload: dict, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    payload = dict(payload)
    destinos = payload.pop("destinos", None)
    destino_ids = payload.pop("destino_ids", [])
    if not isinstance(destino_ids, list) or not all(isinstance(item, str) for item in destino_ids):
        from app.core.errors import AppError
        raise AppError("INVALID_FORM_DESTINATIONS", "Los destinos jerárquicos deben ser una lista de identificadores.", 422)
    motivo = payload.pop("motivo_auditoria", None) or "Alta de formulario"
    correlation_id = payload.pop("correlation_id", "")
    registro = create_formulario(db, user, motivo_auditoria=motivo, correlation_id=correlation_id,
                                 destinos=destinos, **payload)
    if destino_ids:
        set_form_destinations(db, user, registro.id_formulario, destino_ids, correlation_id=correlation_id)
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
    id_formulario: str, payload: CambiarEstadoRequest, request: Request, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    registro = change_status(
        db, user, id_formulario, payload.estado,
        expected_version=payload.expected_version,
        correlation_id=getattr(request.state, "correlation_id", ""),
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
async def responder(
    id_formulario: str, request: Request,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    payload, attachments = await response_request_payload(request)
    envio = save_response(
        db, user, id_formulario,
        draft=payload.borrador,
        respuestas=payload.respuestas,
        id_envio_cliente=payload.id_envio_cliente,
        id_registro_proceso=payload.id_registro_proceso,
        contexto_tipo=payload.contexto_tipo, contexto_id=payload.contexto_id,
        id_respuesta=payload.id_respuesta, expected_version=payload.expected_version,
        crear_contexto=payload.crear_contexto, id_persona=payload.id_persona,
        editar_registrado=payload.editar_registrado,
        id_destino_respuesta=payload.id_destino_respuesta,
        adjuntos=attachments, correlation_id=getattr(request.state, "correlation_id", ""),
    )
    return serialize_response(db, envio, user=user)
