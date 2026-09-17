from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.permissions import AuthenticatedUser, authorize
from app.models import Actividad, Persona, User
from app.services.actividades import create_actividad, is_overdue, list_actividades, soft_delete_actividad, update_actividad
from app.services.records import get_active

router = APIRouter(prefix="/api/v1/actividades", tags=["Actividades"])


class ActivityPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str = Field(min_length=1)
    descripcion: str = Field(min_length=1)
    responsable_id: str
    tipo_fecha: Literal["PROGRAMADA", "LIMITE"]
    fecha_objetivo: str
    estado: Literal["PENDIENTE", "EN_PROCESO", "COMPLETADA"] = "PENDIENTE"
    persona_id: str | None = None


class ActivityUpdate(ActivityPayload):
    expected_version: int


class DeletePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int
    motivo: str = Field(min_length=1)


def serialize(record: Actividad, session: Session) -> dict:
    responsible = session.get(User, record.responsable_id)
    author = session.get(User, record.creado_por_id)
    person = session.get(Persona, record.persona_id) if record.persona_id else None
    return {
        "id_actividad": record.id_actividad, "nombre": record.nombre, "descripcion": record.descripcion,
        "responsable_id": record.responsable_id, "responsable": responsible.nombre if responsible else None,
        "tipo_fecha": record.tipo_fecha, "fecha_objetivo": record.fecha_objetivo, "estado": record.estado,
        "persona_id": record.persona_id, "persona": person.nombre if person else None,
        "cedula": person.cedula if person else None, "area": person.area if person else None,
        "creado_por_id": record.creado_por_id, "registrado_por": author.nombre if author else record.creado_por,
        "fecha_creacion": record.fecha_creacion, "fecha_modificacion": record.fecha_actualizacion,
        "fecha_finalizacion": record.fecha_finalizacion, "vencida": is_overdue(record),
        "version": record.version, "activo": record.activo, "eliminado": record.eliminado,
    }


@router.get("")
def listar(db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user), search: str | None = None,
           responsable_id: str | None = None, estado: str | None = None, tipo_fecha: str | None = None,
           desde: str | None = None, hasta: str | None = None, mis_actividades: bool = False,
           limite: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0)):
    rows, total = list_actividades(db, user, search=search, responsable_id=responsable_id, estado=estado,
                                   tipo_fecha=tipo_fecha, desde=desde, hasta=hasta, mis_actividades=mis_actividades,
                                   limit=limite, offset=offset)
    return {"items": [serialize(row, db) for row in rows], "total": total, "limite": limite, "offset": offset}


@router.get("/opciones")
def opciones(db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    authorize(user, "ACTIVIDADES", "read")
    users = db.scalars(select(User).where(User.eliminado.is_(False), User.activo.is_(True), User.estado == "ACTIVO").order_by(User.nombre)).all()
    people = db.scalars(select(Persona).where(Persona.eliminado.is_(False)).order_by(Persona.nombre).limit(100)).all()
    return {"usuarios": [{"id": u.id_usuario, "nombre": u.nombre} for u in users],
            "personas": [{"id": p.id_persona, "nombre": p.nombre, "cedula": p.cedula, "area": p.area} for p in people]}


@router.post("", status_code=status.HTTP_201_CREATED)
def crear(payload: ActivityPayload, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return serialize(create_actividad(db, user, motivo_auditoria="Creación de actividad", correlation_id=request.state.correlation_id, **payload.model_dump()), db)


@router.get("/{activity_id}")
def obtener(activity_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    authorize(user, "ACTIVIDADES", "read")
    return serialize(get_active(db, Actividad, activity_id, Actividad.id_actividad), db)


@router.patch("/{activity_id}")
def actualizar(activity_id: str, payload: ActivityUpdate, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    values = payload.model_dump(); expected_version = values.pop("expected_version")
    return serialize(update_actividad(db, user, activity_id, expected_version=expected_version, motivo_auditoria="Edición de actividad", correlation_id=request.state.correlation_id, **values), db)


@router.post("/{activity_id}/archivar")
def archivar(activity_id: str, payload: DeletePayload, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return serialize(soft_delete_actividad(db, user, activity_id, expected_version=payload.expected_version, motivo=payload.motivo, correlation_id=request.state.correlation_id), db)
