"""Rutas contextuales de Oficina disponibles en el Bloque 2 de Fase 8."""

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.permissions import AuthenticatedUser
from app.services import oficina
from app.services import oficina_entidades
from app.api.formularios import ResponderFormularioRequest
from app.services.documentos import MAX_FILE_BYTES, content_response_headers
from app.services.dynamic_responses import serialize_response

router = APIRouter(prefix="/api/v1/oficina", tags=["Oficina"])


@router.get("/atenciones")
def list_atenciones(nombre: str | None = None, cedula: str | None = None, area: str | None = None,
                    responsable: str | None = None, estado: str | None = None, desde: str | None = None,
                    hasta: str | None = None, limite: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0),
                    db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return oficina.list_atenciones(db, user, nombre=nombre, cedula=cedula, area=area, responsable=responsable,
                                   estado=estado, desde=desde, hasta=hasta, limit=limite, offset=offset)


@router.post("/atenciones", status_code=status.HTTP_201_CREATED)
def create_atencion(payload: dict, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return oficina.create_atencion_oficina(db, user, correlation_id=request.state.correlation_id, fields=payload)


@router.get("/atenciones/{record_id}")
def get_atencion(record_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return oficina.get_atencion_oficina(db, user, record_id)


@router.patch("/atenciones/{record_id}")
def update_atencion(record_id: str, payload: dict, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    values = dict(payload); expected_version = values.pop("expected_version", None)
    return oficina.update_atencion_oficina(db, user, record_id, expected_version=expected_version,
                                            correlation_id=request.state.correlation_id, fields=values)


@router.post("/atenciones/{record_id}/eliminacion")
def delete_atencion(record_id: str, payload: dict, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return oficina.delete_atencion_oficina(db, user, record_id, expected_version=payload.get("expected_version"),
                                            motivo=payload.get("motivo") or payload.get("reason") or "",
                                            correlation_id=request.state.correlation_id)


@router.get("/atenciones/{record_id}/historial")
def history_atencion(record_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return [{"campo": row.campo, "accion": row.accion, "valor_anterior": row.valor_anterior,
             "valor_nuevo": row.valor_nuevo, "usuario": row.usuario, "fecha_hora": row.fecha_hora,
             "motivo": row.motivo} for row in oficina.atencion_history(db, user, record_id)]


def _history(rows):
    return [{"campo": row.campo, "accion": row.accion, "valor_anterior": row.valor_anterior,
             "valor_nuevo": row.valor_nuevo, "usuario": row.usuario, "fecha_hora": row.fecha_hora,
             "motivo": row.motivo} for row in rows]


def _document(record):
    return {"id_archivo": record.id_archivo, "tipo_registro": record.tipo_registro, "id_registro": record.id_registro,
            "nombre_archivo": record.nombre_archivo, "mime_type": record.mime_type, "extension": record.extension,
            "tamano_bytes": record.tamano_bytes, "tamano_comprimido_bytes": record.tamano_comprimido_bytes,
            "sha256": record.sha256, "categoria_documento": record.categoria_documento, "version": record.version,
            "activo": record.activo, "eliminado": record.eliminado, "fecha_creacion": record.fecha_creacion,
            "creado_por": record.creado_por}


def _office_entity_routes(entity, path: str):
    @router.get(path)
    def list_records(nombre: str | None = None, cedula: str | None = None, area: str | None = None,
                     responsable: str | None = None, fecha: str | None = None, tipo: str | None = None,
                     tipo_gestion: str | None = None, limite: int = Query(25, ge=1, le=100),
                     offset: int = Query(0, ge=0), db: Session = Depends(get_db),
                     user: AuthenticatedUser = Depends(get_current_user)):
        return oficina_entidades.list_records(db, user, entity, nombre=nombre, cedula=cedula, area=area,
            responsable=responsable, fecha=fecha, tipo=tipo, tipo_gestion=tipo_gestion, limit=limite, offset=offset)

    @router.post(path, status_code=status.HTTP_201_CREATED)
    def create_record(payload: dict, request: Request, db: Session = Depends(get_db),
                      user: AuthenticatedUser = Depends(get_current_user)):
        return oficina_entidades.create(db, user, entity, correlation_id=request.state.correlation_id, fields=payload)

    @router.get(f"{path}/{{record_id}}")
    def get_record(record_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
        return oficina_entidades.get(db, user, entity, record_id)

    @router.patch(f"{path}/{{record_id}}")
    def update_record(record_id: str, payload: dict, request: Request, db: Session = Depends(get_db),
                      user: AuthenticatedUser = Depends(get_current_user)):
        values = dict(payload); expected_version = values.pop("expected_version", None)
        return oficina_entidades.update(db, user, entity, record_id, expected_version=expected_version,
            correlation_id=request.state.correlation_id, fields=values)

    @router.post(f"{path}/{{record_id}}/eliminacion")
    def delete_record(record_id: str, payload: dict, request: Request, db: Session = Depends(get_db),
                      user: AuthenticatedUser = Depends(get_current_user)):
        return oficina_entidades.delete(db, user, entity, record_id, expected_version=payload.get("expected_version"),
            motivo=payload.get("motivo") or payload.get("reason") or "", correlation_id=request.state.correlation_id)

    @router.get(f"{path}/{{record_id}}/historial")
    def history_record(record_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
        return _history(oficina_entidades.history(db, user, entity, record_id))


_office_entity_routes(oficina_entidades.beneficios, "/beneficios")
_office_entity_routes(oficina_entidades.prestamos, "/prestamos")
_office_entity_routes(oficina_entidades.seguros, "/seguro")


def _integration_routes(kind: str):
    @router.get(f"/{kind}/{{record_id}}/formularios")
    def forms(record_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
        return oficina.office_forms(db, user, kind=kind, record_id=record_id)

    @router.post(f"/{kind}/{{record_id}}/formularios/{{form_id}}/respuestas", status_code=status.HTTP_201_CREATED)
    async def answer(form_id: str, record_id: str, request: Request,
               db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
        from app.api.formularios import response_request_payload
        payload, attachments = await response_request_payload(request)
        values = payload.model_dump(); values["adjuntos"] = attachments
        return serialize_response(db, oficina.save_office_form_response(
            db, user, kind=kind, record_id=record_id, form_id=form_id,
            correlation_id=request.state.correlation_id, payload=values), user=user)

    @router.get(f"/{kind}/{{record_id}}/documentos")
    def documents(record_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
        return [_document(record) for record in oficina.office_documents(db, user, kind=kind, record_id=record_id)]

    @router.post(f"/{kind}/{{record_id}}/documentos", status_code=status.HTTP_201_CREATED)
    async def upload_document(record_id: str, request: Request, categoria_documento: str | None = Form(None),
                              archivo: UploadFile = File(...), db: Session = Depends(get_db),
                              user: AuthenticatedUser = Depends(get_current_user)):
        record = oficina.upload_office_document(db, user, kind=kind, record_id=record_id,
            nombre_archivo=archivo.filename or "archivo", mime_type=archivo.content_type or "",
            contenido=await archivo.read(MAX_FILE_BYTES + 1), categoria_documento=categoria_documento,
            correlation_id=request.state.correlation_id)
        return _document(record)

    @router.get(f"/{kind}/{{record_id}}/documentos/{{document_id}}/contenido")
    def download_document(record_id: str, document_id: str, request: Request, db: Session = Depends(get_db),
                          user: AuthenticatedUser = Depends(get_current_user)):
        document, content = oficina.download_office_document(db, user, kind=kind, record_id=record_id,
            document_id=document_id, correlation_id=request.state.correlation_id)
        return Response(content=content, media_type=document.mime_type,
            headers=content_response_headers(document.nombre_archivo))

    @router.post(f"/{kind}/{{record_id}}/documentos/{{document_id}}/eliminacion")
    def delete_document(record_id: str, document_id: str, payload: dict, request: Request,
                        db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
        record = oficina.delete_office_document(db, user, kind=kind, record_id=record_id,
            document_id=document_id, expected_version=payload.get("expected_version"),
            motivo=payload.get("motivo") or payload.get("reason") or "", correlation_id=request.state.correlation_id)
        return _document(record)


for _kind in ("atenciones", "beneficios", "prestamos", "seguro"):
    _integration_routes(_kind)
