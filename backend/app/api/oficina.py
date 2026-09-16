"""Rutas contextuales de Oficina disponibles en el Bloque 2 de Fase 8."""

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.permissions import AuthenticatedUser
from app.services import oficina

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
