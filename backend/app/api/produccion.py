from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.permissions import AuthenticatedUser
from app.services import produccion

router = APIRouter(prefix="/api/v1/produccion", tags=["Producción"])


def _history(rows):
    return [{"campo": row.campo, "accion": row.accion, "valor_anterior": row.valor_anterior, "valor_nuevo": row.valor_nuevo, "usuario": row.usuario, "fecha_hora": row.fecha_hora, "motivo": row.motivo} for row in rows]


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
