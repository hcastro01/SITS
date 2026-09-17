from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.core.permissions import AuthenticatedUser
from app.services.accidentes import analyze_file, confirm_lot, issues, lot, lots
from app.services.importaciones_ausentismos import MAX_XLSX_BYTES

router = APIRouter(prefix="/api/v1/importaciones/accidentes", tags=["Importaciones Accidentes"])
def serialize_lot(value): return {key: getattr(value, key) for key in ("id_lote", "nombre_archivo", "usuario_id", "estado", "total_filas", "filas_validas", "filas_con_error", "filas_duplicadas", "filas_importadas", "fecha_creacion", "fecha_actualizacion", "version")}
def serialize_issue(value): return {key: getattr(value, key) for key in ("id_error", "numero_fila", "codigo", "mensaje", "datos_fila")}

@router.post("/analizar", status_code=201)
async def analizar(request: Request, archivo: UploadFile = File(...), db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    lote, analysis = analyze_file(db, user, name=archivo.filename or "accidentes.xlsx", content=await archivo.read(MAX_XLSX_BYTES + 1), correlation_id=request.state.correlation_id)
    return {"lote": serialize_lot(lote), "puede_confirmarse": analysis["puede_confirmarse"], "previsualizacion": analysis["filas"]}
@router.post("/{lote_id}/confirmar")
def confirmar(lote_id: str, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)): return serialize_lot(confirm_lot(db, user, lote_id, correlation_id=request.state.correlation_id))
@router.get("")
def listar(limite: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    values, total = lots(db, user, limit=limite, offset=offset); return {"items": [serialize_lot(value) for value in values], "total": total, "limite": limite, "offset": offset}
@router.get("/{lote_id}")
def detalle(lote_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)): return serialize_lot(lot(db, user, lote_id))
@router.get("/{lote_id}/errores")
def errores(lote_id: str, limite: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    values, total = issues(db, user, lote_id, limit=limite, offset=offset); return {"items": [serialize_issue(value) for value in values], "total": total, "limite": limite, "offset": offset}
