from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.permissions import AuthenticatedUser
from app.api.formularios import ResponderFormularioRequest
from app.models import Documento
from app.schemas.riesgos_trabajo import RiesgoCierre, RiesgoCompromiso, RiesgoCreate, RiesgoSeguimiento, RiesgoUpdate
from app.services.documentos import MAX_FILE_BYTES, content_response_headers
from app.services.dynamic_responses import serialize_response
from app.services.riesgos_trabajo import add_riesgo_compromiso, add_riesgo_seguimiento, close_riesgo, create_riesgo, delete_riesgo_documento, download_riesgo_documento, get_riesgo, list_riesgos, riesgo_compromisos, riesgo_documentos, riesgo_forms, riesgo_history, riesgo_seguimientos, save_riesgo_form_response, update_riesgo, upload_riesgo_documento

router = APIRouter(prefix="/api/v1/riesgos-trabajo", tags=["Riesgos de trabajo"])


def _case(record, person=None) -> dict:
    return {"id_caso": record.id_caso, "codigo_caso": record.codigo_caso, "tipo_caso": record.tipo_caso,
            "persona_id": record.id_persona, "persona": person.nombre if person else record.colaborador,
            "cedula": person.cedula if person else None, "area": person.area if person else record.area,
            "fecha_apertura": record.fecha_apertura, "responsable": record.responsable,
            "estado_caso": record.estado_caso, "prioridad": record.prioridad, "resultado": record.resultado,
            "resumen": record.resultado, "ultimo_seguimiento": record.ultimo_seguimiento,
            "fecha_creacion": record.fecha_creacion, "fecha_actualizacion": record.fecha_actualizacion,
            "fecha_cierre": record.fecha_cierre, "motivo_cierre": record.motivo_cierre,
            "registrado_por": record.creado_por, "version": record.version,
            "activo": record.activo, "eliminado": record.eliminado}


def _child(record, fields: tuple[str, ...], identifier: str) -> dict:
    return {identifier: getattr(record, identifier), **{field: getattr(record, field) for field in fields},
            "fecha_creacion": record.fecha_creacion, "creado_por": record.creado_por, "version": record.version}


def _document(record: Documento) -> dict:
    return {"id_archivo": record.id_archivo, "tipo_registro": record.tipo_registro, "id_registro": record.id_registro,
            "nombre_archivo": record.nombre_archivo, "mime_type": record.mime_type, "extension": record.extension,
            "tamano_bytes": record.tamano_bytes, "tamano_comprimido_bytes": record.tamano_comprimido_bytes,
            "sha256": record.sha256, "categoria_documento": record.categoria_documento, "version": record.version,
            "activo": record.activo, "eliminado": record.eliminado, "fecha_creacion": record.fecha_creacion,
            "creado_por": record.creado_por}


@router.get("")
def listar(nombre: str | None = None, cedula: str | None = None, area: str | None = None, estado: str | None = None, responsable: str | None = None, desde: str | None = None, hasta: str | None = None, limite: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    rows, total = list_riesgos(db, user, nombre=nombre, cedula=cedula, area=area, estado=estado, responsable=responsable, desde=desde, hasta=hasta, limit=limite, offset=offset)
    return {"items": [_case(record, person) for record, person in rows], "total": total, "limite": limite, "offset": offset}


@router.post("", status_code=status.HTTP_201_CREATED)
def crear(payload: RiesgoCreate, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    record = create_riesgo(db, user, correlation_id=request.state.correlation_id, **payload.model_dump())
    return _case(get_riesgo(db, user, record.id_caso))


@router.get("/{riesgo_id}")
def detalle(riesgo_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return _case(get_riesgo(db, user, riesgo_id))


@router.patch("/{riesgo_id}")
def actualizar(riesgo_id: str, payload: RiesgoUpdate, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    values = payload.model_dump(exclude_unset=True)
    expected_version = values.pop("expected_version")
    return _case(update_riesgo(db, user, riesgo_id, expected_version=expected_version, correlation_id=request.state.correlation_id, **values))


@router.get("/{riesgo_id}/seguimientos")
def seguimientos(riesgo_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    fields = ("fecha", "hora", "responsable", "tipo_seguimiento", "canal", "tecnica", "descripcion", "resultado", "proxima_accion", "fecha_proxima_accion", "estado", "evidencias")
    return [_child(row, fields, "id_seguimiento") for row in riesgo_seguimientos(db, user, riesgo_id)]


@router.post("/{riesgo_id}/seguimientos", status_code=status.HTTP_201_CREATED)
def crear_seguimiento(riesgo_id: str, payload: RiesgoSeguimiento, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    fields = ("fecha", "hora", "responsable", "tipo_seguimiento", "canal", "tecnica", "descripcion", "resultado", "proxima_accion", "fecha_proxima_accion", "estado", "evidencias")
    record = add_riesgo_seguimiento(db, user, riesgo_id, correlation_id=request.state.correlation_id, **payload.model_dump(exclude_none=True))
    return _child(record, fields, "id_seguimiento")


@router.get("/{riesgo_id}/compromisos")
def compromisos(riesgo_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    fields = ("id_seguimiento", "fecha_creacion_compromiso", "responsable", "descripcion", "fecha_limite", "estado", "fecha_cumplimiento", "evidencia", "observacion")
    return [_child(row, fields, "id_compromiso") for row in riesgo_compromisos(db, user, riesgo_id)]


@router.post("/{riesgo_id}/compromisos", status_code=status.HTTP_201_CREATED)
def crear_compromiso(riesgo_id: str, payload: RiesgoCompromiso, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    fields = ("id_seguimiento", "fecha_creacion_compromiso", "responsable", "descripcion", "fecha_limite", "estado", "fecha_cumplimiento", "evidencia", "observacion")
    record = add_riesgo_compromiso(db, user, riesgo_id, correlation_id=request.state.correlation_id, **payload.model_dump(exclude_none=True))
    return _child(record, fields, "id_compromiso")


@router.post("/{riesgo_id}/cierres", status_code=status.HTTP_201_CREATED)
def cerrar(riesgo_id: str, payload: RiesgoCierre, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    record = close_riesgo(db, user, riesgo_id, correlation_id=request.state.correlation_id, **payload.model_dump())
    return {"id_cierre": record.id_cierre, "fecha_cierre_caso": record.fecha_cierre_caso, "motivo_cierre": record.motivo_cierre, "resultado_final": record.resultado_final, "version": record.version}


@router.get("/{riesgo_id}/historial")
def historial(riesgo_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return [{"campo": row.campo, "accion": row.accion, "valor_anterior": row.valor_anterior, "valor_nuevo": row.valor_nuevo, "usuario": row.usuario, "fecha_hora": row.fecha_hora, "motivo": row.motivo} for row in riesgo_history(db, user, riesgo_id)]


@router.get("/{riesgo_id}/formularios")
def formularios(riesgo_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return riesgo_forms(db, user, riesgo_id)


@router.post("/{riesgo_id}/formularios/{id_formulario}/respuestas", status_code=status.HTTP_201_CREATED)
async def responder_formulario(riesgo_id: str, id_formulario: str, request: Request,
                         db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    from app.api.formularios import response_request_payload
    payload, attachments = await response_request_payload(request)
    envio = save_riesgo_form_response(db, user, riesgo_id, id_formulario,
        correlation_id=request.state.correlation_id, draft=payload.borrador, answers=payload.respuestas,
        client_key=payload.id_envio_cliente, legacy_record_id=payload.id_registro_proceso,
        response_id=payload.id_respuesta, expected_version=payload.expected_version,
        create_context=False, person_id=payload.id_persona, edit_registered=payload.editar_registrado,
        id_destino_respuesta=payload.id_destino_respuesta, attachments=attachments)
    return serialize_response(db, envio, user=user)


@router.get("/{riesgo_id}/documentos")
def documentos(riesgo_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return [_document(record) for record in riesgo_documentos(db, user, riesgo_id)]


@router.post("/{riesgo_id}/documentos", status_code=status.HTTP_201_CREATED)
async def cargar_documento(riesgo_id: str, request: Request, categoria_documento: str | None = Form(None),
                           archivo: UploadFile = File(...), db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    record = upload_riesgo_documento(db, user, riesgo_id, nombre_archivo=archivo.filename or "archivo",
        mime_type=archivo.content_type or "", contenido=await archivo.read(MAX_FILE_BYTES + 1),
        categoria_documento=categoria_documento, correlation_id=request.state.correlation_id)
    return _document(record)


@router.get("/{riesgo_id}/documentos/{id_archivo}/contenido")
def descargar_documento(riesgo_id: str, id_archivo: str, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    document, content = download_riesgo_documento(db, user, riesgo_id, id_archivo, correlation_id=request.state.correlation_id)
    return Response(content=content, media_type=document.mime_type,
        headers=content_response_headers(document.nombre_archivo))


@router.post("/{riesgo_id}/documentos/{id_archivo}/eliminacion")
def eliminar_documento(riesgo_id: str, id_archivo: str, payload: dict, request: Request,
                       db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    record = delete_riesgo_documento(db, user, riesgo_id, id_archivo, expected_version=payload.get("expected_version"),
        motivo=payload.get("motivo") or payload.get("reason") or "", correlation_id=request.state.correlation_id)
    return _document(record)
