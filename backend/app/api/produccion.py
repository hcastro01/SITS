from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.permissions import AuthenticatedUser
from app.services import produccion
from app.services.dynamic_responses import serialize_response
from app.api.formularios import ResponderFormularioRequest
from app.services.documentos import MAX_FILE_BYTES, content_response_headers

router = APIRouter(prefix="/api/v1/produccion", tags=["Producción"])


def _history(rows):
    return [{"campo": row.campo, "accion": row.accion, "valor_anterior": row.valor_anterior, "valor_nuevo": row.valor_nuevo, "usuario": row.usuario, "fecha_hora": row.fecha_hora, "motivo": row.motivo} for row in rows]


def _document(record):
    return {"id_archivo": record.id_archivo, "tipo_registro": record.tipo_registro, "id_registro": record.id_registro,
            "nombre_archivo": record.nombre_archivo, "mime_type": record.mime_type, "extension": record.extension,
            "tamano_bytes": record.tamano_bytes, "tamano_comprimido_bytes": record.tamano_comprimido_bytes,
            "sha256": record.sha256, "categoria_documento": record.categoria_documento, "version": record.version,
            "activo": record.activo, "eliminado": record.eliminado, "fecha_creacion": record.fecha_creacion,
            "creado_por": record.creado_por}


def _filters(nombre=None, cedula=None, area=None, responsable=None, estado=None, desde=None, hasta=None, limite=25, offset=0):
    return {"nombre": nombre, "cedula": cedula, "area": area, "responsable": responsable, "estado": estado, "desde": desde, "hasta": hasta, "limit": limite, "offset": offset}


@router.get("/atenciones")
def list_atenciones(nombre: str | None = None, cedula: str | None = None, area: str | None = None, responsable: str | None = None, estado: str | None = None, desde: str | None = None, hasta: str | None = None, limite: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return produccion.list_atenciones(db, user, **_filters(nombre, cedula, area, responsable, estado, desde, hasta, limite, offset))


@router.post("/atenciones", status_code=status.HTTP_201_CREATED)
def create_atenciones(payload: dict, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return produccion.create_atencion_produccion(db, user, correlation_id=request.state.correlation_id, fields=payload)


@router.get("/atenciones/{record_id}")
def get_atenciones(record_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return produccion.get_atencion_produccion(db, user, record_id)


@router.patch("/atenciones/{record_id}")
def update_atenciones(record_id: str, payload: dict, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    values = dict(payload); expected_version = values.pop("expected_version", None)
    return produccion.update_atencion_produccion(db, user, record_id, expected_version=expected_version, correlation_id=request.state.correlation_id, fields=values)


@router.post("/atenciones/{record_id}/eliminacion")
def delete_atenciones(record_id: str, payload: dict, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return produccion.delete_atencion_produccion(db, user, record_id, expected_version=payload.get("expected_version"), motivo=payload.get("motivo") or "", correlation_id=request.state.correlation_id)


@router.get("/atenciones/{record_id}/historial")
def history_atenciones(record_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return _history(produccion.production_history(db, user, kind="atenciones", record_id=record_id))


def _form_routes(kind: str):
    @router.get(f"/{kind}/{{record_id}}/formularios")
    def forms(record_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
        return produccion.production_forms(db, user, kind=kind, record_id=record_id)

    @router.post(f"/{kind}/{{record_id}}/formularios/{{form_id}}/respuestas", status_code=status.HTTP_201_CREATED)
    def answer(form_id: str, record_id: str, payload: ResponderFormularioRequest, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
        return serialize_response(db, produccion.save_production_form_response(db, user, kind=kind, record_id=record_id, form_id=form_id, correlation_id=request.state.correlation_id, payload=payload.model_dump()), user=user)

    @router.get(f"/{kind}/{{record_id}}/documentos")
    def documents(record_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
        return [_document(record) for record in produccion.production_documents(db, user, kind=kind, record_id=record_id)]

    @router.post(f"/{kind}/{{record_id}}/documentos", status_code=status.HTTP_201_CREATED)
    async def upload_document(record_id: str, request: Request, categoria_documento: str | None = Form(None), archivo: UploadFile = File(...), db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
        record = produccion.upload_production_document(db, user, kind=kind, record_id=record_id, nombre_archivo=archivo.filename or "archivo", mime_type=archivo.content_type or "", contenido=await archivo.read(MAX_FILE_BYTES + 1), categoria_documento=categoria_documento, correlation_id=request.state.correlation_id)
        return _document(record)

    @router.get(f"/{kind}/{{record_id}}/documentos/{{document_id}}/contenido")
    def download_document(record_id: str, document_id: str, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
        document, content = produccion.download_production_document(db, user, kind=kind, record_id=record_id, document_id=document_id, correlation_id=request.state.correlation_id)
        return Response(content=content, media_type=document.mime_type, headers=content_response_headers(document.nombre_archivo))

    @router.post(f"/{kind}/{{record_id}}/documentos/{{document_id}}/eliminacion")
    def delete_document(record_id: str, document_id: str, payload: dict, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
        record = produccion.delete_production_document(db, user, kind=kind, record_id=record_id, document_id=document_id, expected_version=payload.get("expected_version"), motivo=payload.get("motivo") or payload.get("reason") or "", correlation_id=request.state.correlation_id)
        return _document(record)


def _register_entity(name, listing, create, get, update, delete):
    @router.get(f"/{name}")
    def list_records(nombre: str | None = None, cedula: str | None = None, area: str | None = None, responsable: str | None = None, estado: str | None = None, desde: str | None = None, hasta: str | None = None, limite: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
        return listing(db, user, **_filters(nombre, cedula, area, responsable, estado, desde, hasta, limite, offset))
    @router.post(f"/{name}", status_code=status.HTTP_201_CREATED)
    def create_record(payload: dict, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
        return create(db, user, correlation_id=request.state.correlation_id, fields=payload)
    @router.get(f"/{name}/{{record_id}}")
    def get_record(record_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
        return get(db, user, record_id)
    @router.patch(f"/{name}/{{record_id}}")
    def update_record(record_id: str, payload: dict, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
        values = dict(payload); expected_version = values.pop("expected_version", None)
        return update(db, user, record_id, expected_version=expected_version, correlation_id=request.state.correlation_id, fields=values)
    @router.post(f"/{name}/{{record_id}}/eliminacion")
    def delete_record(record_id: str, payload: dict, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
        return delete(db, user, record_id, expected_version=payload.get("expected_version"), motivo=payload.get("motivo") or "", correlation_id=request.state.correlation_id)
    @router.get(f"/{name}/{{record_id}}/historial")
    def history_record(record_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
        return _history(produccion.production_history(db, user, kind=name, record_id=record_id))


_register_entity("recorridos", produccion.list_recorridos, produccion.create_recorrido, produccion.get_recorrido, produccion.update_recorrido, produccion.delete_recorrido)
_register_entity("novedades", produccion.list_novedades, produccion.create_novedad, produccion.get_novedad, produccion.update_novedad, produccion.delete_novedad)
_form_routes("atenciones")
_form_routes("recorridos")
_form_routes("novedades")
