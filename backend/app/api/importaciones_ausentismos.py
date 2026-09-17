from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.permissions import AuthenticatedUser
from app.models import ErrorImportacionAusentismo, LoteImportacionAusentismo
from app.schemas.ausentismos import ErrorImportacionAusentismoRespuesta, LoteImportacionAusentismoRespuesta
from app.services.importaciones_ausentismos import (
    MAX_XLSX_BYTES, analizar_archivo_ausentismos, confirmar_lote_ausentismos,
    listar_errores_lote_ausentismos, listar_lotes_ausentismos, obtener_lote_ausentismos,
)

router = APIRouter(prefix="/api/v1/importaciones/ausentismos", tags=["Importaciones Ausentismos"])


def serialize_lote(lote: LoteImportacionAusentismo) -> dict:
    return {
        "id_lote": lote.id_lote, "nombre_archivo": lote.nombre_archivo, "usuario_id": lote.usuario_id,
        "estado": lote.estado, "total_filas": lote.total_filas, "filas_validas": lote.filas_validas,
        "filas_con_error": lote.filas_con_error, "filas_duplicadas": lote.filas_duplicadas,
        "filas_importadas": lote.filas_importadas, "fecha_creacion": lote.fecha_creacion,
        "fecha_actualizacion": lote.fecha_actualizacion, "version": lote.version,
    }


def serialize_error(error: ErrorImportacionAusentismo) -> dict:
    return {"id_error": error.id_error, "numero_fila": error.numero_fila, "codigo": error.codigo,
            "mensaje": error.mensaje, "datos_fila": error.datos_fila}


@router.post("/analizar", status_code=201)
async def analizar(request: Request, archivo: UploadFile = File(...), db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    contenido = await archivo.read(MAX_XLSX_BYTES + 1)
    lote, analysis = analizar_archivo_ausentismos(
        db, user, nombre_archivo=archivo.filename or "archivo.xlsx", contenido=contenido,
        correlation_id=getattr(request.state, "correlation_id", ""),
    )
    return {"lote": serialize_lote(lote), "puede_confirmarse": analysis.puede_confirmarse,
            "previsualizacion": [row.model_dump() for row in analysis.filas]}


@router.post("/{lote_id}/confirmar")
def confirmar(lote_id: str, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return serialize_lote(confirmar_lote_ausentismos(db, user, lote_id, correlation_id=request.state.correlation_id))


@router.get("")
def listar(limite: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    lots, total = listar_lotes_ausentismos(db, user, limit=limite, offset=offset)
    return {"items": [serialize_lote(lote) for lote in lots], "total": total, "limite": limite, "offset": offset}


@router.get("/{lote_id}")
def detalle(lote_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return serialize_lote(obtener_lote_ausentismos(db, user, lote_id))


@router.get("/{lote_id}/errores")
def errores(lote_id: str, limite: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    rows, total = listar_errores_lote_ausentismos(db, user, lote_id, limit=limite, offset=offset)
    return {"items": [serialize_error(row) for row in rows], "total": total, "limite": limite, "offset": offset}
