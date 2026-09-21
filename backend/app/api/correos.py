"""API de Correos: sesión SITS para personas y credencial exclusiva para n8n."""
import secrets
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Header, Query, Request, Response, UploadFile, status
from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser
from app.models import Correo, ErrorImportacionCorreo, LoteImportacionCorreo, SeguimientoCorreo
from app.services.correos import CATEGORIAS_VALIDAS, ESTADOS_REQUERIMIENTO, add_follow_up, analyze_import, confirm_import, create_from_post, create_integration_email, get_detail, list_emails, list_lot_errors, list_lots, max_xlsx_bytes, normalize_received, summary

router = APIRouter(prefix="/api/v1/correos", tags=["Correos"])


class CorreoPostPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id_externo_correo: str = Field(min_length=1, max_length=512)
    idempotency_key: str = Field(min_length=1, max_length=600)
    asunto: str = Field(default="", max_length=2000)
    remitente: str | None = Field(default=None, max_length=1000)
    destinatarios: str | None = Field(default=None, max_length=8000)
    cc: str | None = Field(default=None, max_length=8000)
    recibido_en: str | None = Field(default=None, max_length=100)
    prioridad: str | None = Field(default=None, max_length=100)
    cuerpo: str | None = Field(default=None, max_length=2_000_000)
    tiene_adjuntos: bool = False
    leido: bool = False
    categoria_macro: str | None = Field(default=None, max_length=160)
    categoria_nombre: str | None = Field(default=None, max_length=300)
    regla_disparadora: str | None = Field(default=None, max_length=500)
    estado_clasificacion: Literal["CLASIFICADO", "REVISION"] = "REVISION"


class N8nCorreoPayload(BaseModel):
    """Contrato de n8n. Admite nombres Outlook y el contrato interno sin exponer una sesión."""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    message_id: Annotated[str, Field(validation_alias=AliasChoices("MessageId", "messageId", "message_id", "id_externo_correo"), min_length=1, max_length=512)]
    subject: Annotated[str, Field(default="", validation_alias=AliasChoices("Subject", "subject", "asunto"), max_length=2000)]
    sender: Annotated[str | None, Field(default=None, validation_alias=AliasChoices("From", "from", "remitente"), max_length=1000)]
    recipients: Annotated[str | None, Field(default=None, validation_alias=AliasChoices("To", "to", "destinatarios"), max_length=8000)]
    cc: Annotated[str | None, Field(default=None, validation_alias=AliasChoices("CC", "cc"), max_length=8000)]
    received_time: Annotated[str | None, Field(default=None, validation_alias=AliasChoices("ReceivedTime", "receivedTime", "recibido_en"), max_length=100)]
    importance: Annotated[str | None, Field(default=None, validation_alias=AliasChoices("Importance", "importance", "prioridad"), max_length=100)]
    body: Annotated[str | None, Field(default=None, validation_alias=AliasChoices("Body", "body", "cuerpo"), max_length=2_000_000)]
    has_attachments: Annotated[bool, Field(default=False, validation_alias=AliasChoices("HasAttachments", "hasAttachments", "tiene_adjuntos"))]
    is_read: Annotated[bool, Field(default=False, validation_alias=AliasChoices("IsRead", "isRead", "leido"))]
    category: Annotated[str | None, Field(default=None, validation_alias=AliasChoices("Category", "Categoría", "categoria_macro"), max_length=160)]
    category_name: Annotated[str | None, Field(default=None, validation_alias=AliasChoices("CategoryName", "categoria_nombre"), max_length=300)]


class ConfirmImportPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    incluir_sin_clasificar: bool = False


class SeguimientoPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    detalle_seguimiento: str = Field(min_length=1, max_length=20_000)
    seguimiento_por: str | None = Field(default=None, max_length=500)
    estado_requerimiento: Literal["PENDIENTE", "EN_PROCESO", "EN_ESPERA", "RESUELTO", "CERRADO"]


def serialize_email(value: Correo, *, include_body: bool = False) -> dict:
    result = {"id_correo": value.id_correo, "id_externo_correo": value.id_externo_correo, "asunto": value.asunto, "remitente": value.remitente, "destinatarios": value.destinatarios, "cc": value.cc, "fecha_recibido": value.fecha_recibido, "importancia": value.importancia, "tiene_adjuntos": value.tiene_adjuntos, "leido": value.leido, "categoria_macro": value.categoria_macro, "categoria_nombre": value.categoria_nombre, "estado_categoria": value.estado_categoria, "regla_disparadora": value.regla_disparadora, "estado_clasificacion": value.estado_clasificacion, "estado_requerimiento": value.estado_requerimiento, "responsable_seguimiento": value.responsable_seguimiento, "origen": value.archivo_fuente, "fecha_creacion": value.fecha_creacion, "fecha_actualizacion": value.fecha_actualizacion, "version": value.version}
    if include_body: result["cuerpo"] = value.cuerpo
    return result


def serialize_follow(value: SeguimientoCorreo) -> dict:
    return {"id_seguimiento": value.id_seguimiento, "fecha_seguimiento": value.fecha_seguimiento, "detalle_seguimiento": value.detalle_seguimiento, "seguimiento_por": value.seguimiento_por, "estado_requerimiento": value.estado_requerimiento}


def serialize_lot(value: LoteImportacionCorreo) -> dict:
    return {"id_lote": value.id_lote, "nombre_archivo": value.nombre_archivo, "estado": value.estado, "origen": value.origen, "total_filas": value.total_filas, "filas_procesadas": value.filas_procesadas, "filas_clasificadas": value.filas_clasificadas, "filas_revision": value.filas_revision, "filas_importadas": value.filas_importadas, "filas_duplicadas": value.filas_duplicadas, "filas_omitidas": value.filas_omitidas, "filas_error": value.filas_error, "duracion_ms": value.duracion_ms, "fecha_creacion": value.fecha_creacion, "version": value.version}


def serialize_error(value: ErrorImportacionCorreo) -> dict:
    return {"fila": value.fila, "message_id": value.id_externo_correo, "codigo": value.codigo, "detalle": value.detalle}


def _api_data(payload: CorreoPostPayload) -> dict:
    data = payload.model_dump(); data["fecha_recibido"] = normalize_received(data.pop("recibido_en")); data["importancia"] = data.pop("prioridad")
    category = data["categoria_macro"]
    data["estado_categoria"] = "VALIDA" if category in CATEGORIAS_VALIDAS else ("SIN_CATEGORIA" if not category else "DESCONOCIDA")
    if data["estado_categoria"] != "VALIDA": data["estado_clasificacion"] = "REVISION"
    return data


def _n8n_data(payload: N8nCorreoPayload) -> dict:
    category = payload.category
    return {"id_externo_correo": payload.message_id.strip(), "idempotency_key": f"correo:{payload.message_id.strip()}", "asunto": payload.subject, "remitente": payload.sender, "destinatarios": payload.recipients, "cc": payload.cc, "fecha_recibido": normalize_received(payload.received_time), "importancia": payload.importance, "cuerpo": payload.body, "tiene_adjuntos": payload.has_attachments, "leido": payload.is_read, "categoria_macro": category, "categoria_nombre": payload.category_name, "regla_disparadora": None, "estado_categoria": "VALIDA" if category in CATEGORIAS_VALIDAS else ("SIN_CATEGORIA" if not category else "DESCONOCIDA"), "estado_clasificacion": "CLASIFICADO" if category in CATEGORIAS_VALIDAS else "REVISION"}


def _require_n8n_token(authorization: str | None) -> None:
    configured = get_settings().n8n_sits_api_key
    supplied = authorization.removeprefix("Bearer ").strip() if authorization and authorization.startswith("Bearer ") else ""
    if not configured or not supplied or not secrets.compare_digest(configured, supplied):
        raise AppError("INTEGRATION_AUTH_REQUIRED", "La credencial de integración no es válida.", 401)


@router.get("/resumen")
def obtener_resumen(db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)): return summary(db, user)


@router.get("")
def listar(estado: str | None = None, categoria: str | None = None, texto: str | None = None, asunto: str | None = None, remitente: str | None = None, destinatario: str | None = None, message_id: str | None = None, fecha_desde: str | None = None, fecha_hasta: str | None = None, origen: str | None = None, importancia: str | None = None, tiene_adjuntos: bool | None = None, orden: Literal["recibido_desc", "asunto_asc"] = "recibido_desc", limite: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    if estado and estado not in ESTADOS_REQUERIMIENTO: raise AppError("INVALID_STATE", "El estado solicitado no es válido.", 422)
    rows, total = list_emails(db, user, limit=limite, offset=offset, filters=locals())
    return {"items": [serialize_email(row) for row in rows], "total": total, "limite": limite, "offset": offset}


@router.get("/importar/lotes")
def historial_importaciones(db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)): return {"items": [serialize_lot(row) for row in list_lots(db, user)]}


@router.get("/importar/{lote_id}/errores")
def errores_importacion(lote_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)): return {"items": [serialize_error(row) for row in list_lot_errors(db, user, lote_id)]}


@router.post("", status_code=status.HTTP_201_CREATED)
def post_correo(payload: CorreoPostPayload, request: Request, idempotency_header: str | None = Header(default=None, alias="Idempotency-Key"), db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    if idempotency_header and idempotency_header != payload.idempotency_key: raise AppError("IDEMPOTENCY_MISMATCH", "La clave del encabezado no coincide con el cuerpo.", 422)
    record, created = create_from_post(db, user, _api_data(payload), correlation_id=request.state.correlation_id)
    return {"created": created, "correo": serialize_email(record)}


@router.post("/integraciones/n8n")
def recibir_n8n(payload: N8nCorreoPayload, request: Request, response: Response, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    _require_n8n_token(authorization)
    record, created = create_integration_email(db, _n8n_data(payload), correlation_id=request.state.correlation_id)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return {"created": created, "duplicate": not created, "correo": serialize_email(record)}


@router.post("/importar/analizar", status_code=status.HTTP_201_CREATED)
async def analizar(request: Request, archivo: UploadFile = File(...), db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    content = await archivo.read(max_xlsx_bytes() + 1)
    lot, preview = analyze_import(db, user, filename=archivo.filename or "correos.xlsx", content=content, correlation_id=request.state.correlation_id)
    return {"lote": serialize_lot(lot), "ultimos_100": [serialize_email_data(value) for value in preview]}


def serialize_email_data(value: dict) -> dict: return {key: value.get(key) for key in ("id_externo_correo", "asunto", "remitente", "fecha_recibido", "categoria_macro", "categoria_nombre", "estado_categoria", "estado_clasificacion")}


@router.post("/importar/{lote_id}/confirmar")
def confirmar(lote_id: str, payload: ConfirmImportPayload, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    lot, selected, inserted, duplicates = confirm_import(db, user, lote_id, include_revision=payload.incluir_sin_clasificar, correlation_id=request.state.correlation_id)
    return {"lote": serialize_lot(lot), "filas_seleccionadas": selected, "filas_importadas": inserted, "filas_duplicadas": duplicates}


@router.get("/{correo_id}")
def detalle(correo_id: str, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    record, follows = get_detail(db, user, correo_id, correlation_id=request.state.correlation_id)
    return {"correo": serialize_email(record, include_body=True), "seguimientos": [serialize_follow(item) for item in follows]}


@router.post("/{correo_id}/seguimientos", status_code=status.HTTP_201_CREATED)
def crear_seguimiento(correo_id: str, payload: SeguimientoPayload, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    record, follow = add_follow_up(db, user, correo_id, expected_version=payload.expected_version, detail=payload.detalle_seguimiento, responsible=payload.seguimiento_por, state=payload.estado_requerimiento, correlation_id=request.state.correlation_id)
    return {"correo": serialize_email(record), "seguimiento": serialize_follow(follow)}
