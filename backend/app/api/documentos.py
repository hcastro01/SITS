"""Router de Documentos: carga/descarga de adjuntos guardados como BLOB comprimido
en SQLite (decisión explícita del usuario, ver app/services/documentos.py)."""

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.permissions import AuthenticatedUser
from app.models import Documento
from app.services.documentos import download_documento, list_documentos, soft_delete_documento, upload_documento

router = APIRouter(prefix="/api/v1/documentos", tags=["Documentos"])


def _serialize(record: Documento) -> dict:
    return {
        "id_archivo": record.id_archivo, "tipo_registro": record.tipo_registro, "id_registro": record.id_registro,
        "nombre_archivo": record.nombre_archivo, "mime_type": record.mime_type, "extension": record.extension,
        "tamano_bytes": record.tamano_bytes, "tamano_comprimido_bytes": record.tamano_comprimido_bytes,
        "sha256": record.sha256, "categoria_documento": record.categoria_documento,
        "version": record.version, "activo": record.activo, "eliminado": record.eliminado,
        "fecha_creacion": record.fecha_creacion, "creado_por": record.creado_por,
    }


@router.get("")
def listar(
    tipo_registro: str = Query(...), id_registro: str = Query(...),
    db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user),
):
    registros = list_documentos(db, user, tipo_registro=tipo_registro, id_registro=id_registro)
    return [_serialize(r) for r in registros]


@router.post("", status_code=201)
async def cargar(
    tipo_registro: str = Form(...), id_registro: str = Form(...),
    categoria_documento: str | None = Form(None), correlation_id: str = Form(""),
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user),
):
    contenido = await archivo.read()
    registro = upload_documento(
        db, user, tipo_registro=tipo_registro, id_registro=id_registro,
        nombre_archivo=archivo.filename or "archivo", mime_type=archivo.content_type or "",
        contenido=contenido, categoria_documento=categoria_documento, correlation_id=correlation_id,
    )
    return _serialize(registro)


@router.get("/{id_archivo}/contenido")
def descargar(id_archivo: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    documento, contenido = download_documento(db, user, id_archivo)
    return Response(
        content=contenido, media_type=documento.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{documento.nombre_archivo}"'},
    )


@router.post("/{id_archivo}/eliminacion")
def eliminar(
    id_archivo: str, payload: dict, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    registro = soft_delete_documento(
        db, user, id_archivo, expected_version=payload.get("expected_version"),
        motivo=payload.get("motivo") or payload.get("reason") or "", correlation_id=payload.get("correlation_id", ""),
    )
    return _serialize(registro)
