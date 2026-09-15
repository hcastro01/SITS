from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.permissions import AuthenticatedUser
from app.schemas.riesgos_trabajo import RiesgoCierre, RiesgoCreate, RiesgoSeguimiento, RiesgoUpdate
from app.services.riesgos_trabajo import add_riesgo_seguimiento, close_riesgo, create_riesgo, get_riesgo, list_riesgos, riesgo_compromisos, riesgo_history, riesgo_seguimientos, update_riesgo

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


@router.post("/{riesgo_id}/cierres", status_code=status.HTTP_201_CREATED)
def cerrar(riesgo_id: str, payload: RiesgoCierre, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    record = close_riesgo(db, user, riesgo_id, correlation_id=request.state.correlation_id, **payload.model_dump())
    return {"id_cierre": record.id_cierre, "fecha_cierre_caso": record.fecha_cierre_caso, "motivo_cierre": record.motivo_cierre, "resultado_final": record.resultado_final, "version": record.version}


@router.get("/{riesgo_id}/historial")
def historial(riesgo_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return [{"campo": row.campo, "accion": row.accion, "valor_anterior": row.valor_anterior, "valor_nuevo": row.valor_nuevo, "usuario": row.usuario, "fecha_hora": row.fecha_hora, "motivo": row.motivo} for row in riesgo_history(db, user, riesgo_id)]
