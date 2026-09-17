from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.permissions import AuthenticatedUser
from app.services import medico
from app.services.documentos import MAX_FILE_BYTES, content_response_headers

router = APIRouter(prefix="/api/v1/medico", tags=["Departamento Médico"])


def _document(record):
    return {name: getattr(record, name) for name in ("id_archivo", "tipo_registro", "id_registro", "nombre_archivo", "mime_type", "extension", "tamano_bytes", "tamano_comprimido_bytes", "sha256", "categoria_documento", "version", "activo", "eliminado", "fecha_creacion", "creado_por")}


@router.get("/atenciones")
def listar(limite: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return medico.list_atenciones(db, user, limit=limite, offset=offset)

@router.post("/atenciones", status_code=status.HTTP_201_CREATED)
def crear(payload: dict, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return medico.create(db, user, correlation_id=request.state.correlation_id, fields=payload)

@router.get("/atenciones/{record_id}")
def obtener(record_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)): return medico.get(db, user, record_id)

@router.patch("/atenciones/{record_id}")
def actualizar(record_id: str, payload: dict, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    values = dict(payload); return medico.update(db, user, record_id, expected_version=values.pop("expected_version", None), correlation_id=request.state.correlation_id, fields=values)

@router.post("/atenciones/{record_id}/eliminacion")
def eliminar(record_id: str, payload: dict, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return medico.delete(db, user, record_id, expected_version=payload.get("expected_version"), motivo=payload.get("motivo") or payload.get("reason") or "", correlation_id=request.state.correlation_id)

@router.post("/atenciones/{record_id}/restauracion")
def restaurar(record_id: str, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return medico.restore(db, user, record_id, correlation_id=request.state.correlation_id)

@router.get("/atenciones/{record_id}/historial")
def historial(record_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return [{"campo": row.campo, "accion": row.accion, "valor_anterior": row.valor_anterior, "valor_nuevo": row.valor_nuevo, "usuario": row.usuario, "fecha_hora": row.fecha_hora, "motivo": row.motivo} for row in medico.history(db, user, record_id)]

@router.get("/atenciones/{record_id}/documentos")
def documentos(record_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)): return [_document(row) for row in medico.documents(db, user, record_id)]

@router.post("/atenciones/{record_id}/documentos", status_code=status.HTTP_201_CREATED)
async def subir(record_id: str, request: Request, categoria_documento: str | None = Form(None), archivo: UploadFile = File(...), db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return _document(medico.upload_document(db, user, record_id, nombre_archivo=archivo.filename or "archivo", mime_type=archivo.content_type or "", contenido=await archivo.read(MAX_FILE_BYTES + 1), categoria_documento=categoria_documento, correlation_id=request.state.correlation_id))

@router.get("/atenciones/{record_id}/documentos/{document_id}/contenido")
def descargar(record_id: str, document_id: str, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    document, content = medico.download_document(db, user, record_id, document_id, correlation_id=request.state.correlation_id); return Response(content=content, media_type=document.mime_type, headers=content_response_headers(document.nombre_archivo))

@router.post("/atenciones/{record_id}/documentos/{document_id}/eliminacion")
def borrar_documento(record_id: str, document_id: str, payload: dict, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return _document(medico.delete_document(db, user, record_id, document_id, expected_version=payload.get("expected_version"), motivo=payload.get("motivo") or payload.get("reason") or "", correlation_id=request.state.correlation_id))
