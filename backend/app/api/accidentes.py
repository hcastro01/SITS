from typing import Literal
from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.core.permissions import AuthenticatedUser
from app.models import Accidente
from app.services.accidentes import create, get_record, list_records, update

router = APIRouter(prefix="/api/v1/accidentes", tags=["Accidentes"])

class AccidentePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    persona_id: str
    fecha_accidente: str
    clasificacion: str = Field(min_length=1)
    descripcion: str = Field(min_length=1)
    estado: Literal["ABIERTO", "EN_SEGUIMIENTO", "CERRADO"] = "ABIERTO"
    observacion: str | None = None
class AccidenteUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int
    clasificacion: str | None = Field(default=None, min_length=1)
    descripcion: str | None = Field(default=None, min_length=1)
    estado: Literal["ABIERTO", "EN_SEGUIMIENTO", "CERRADO"] | None = None
    observacion: str | None = None

def serialize(row) -> dict:
    record, person, lot, author = row
    return {"id_accidente": record.id_accidente, "persona_id": record.persona_id, "persona": person.nombre, "cedula": person.cedula, "area": person.area, "fecha_accidente": record.fecha_accidente, "clasificacion": record.clasificacion, "estado": record.estado, "descripcion": record.descripcion, "observacion": record.observacion, "fecha_registro": record.fecha_creacion, "origen": "IMPORTACION_XLSX" if record.lote_id else "REGISTRO_MANUAL", "lote_id": record.lote_id, "lote_nombre_archivo": lot.nombre_archivo if lot else None, "registrado_por_id": author.id_usuario if author else None, "registrado_por": author.nombre if author else record.creado_por, "version": record.version}

@router.get("")
def listar(nombre: str | None = None, cedula: str | None = None, clasificacion: str | None = None, estado: str | None = None, desde: str | None = None, hasta: str | None = None, origen: str | None = None, lote_id: str | None = None, limite: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    rows, total = list_records(db, user, nombre=nombre, cedula=cedula, clasificacion=clasificacion, estado=estado, desde=desde, hasta=hasta, origen=origen, lote_id=lote_id, limit=limite, offset=offset)
    return {"items": [serialize(row) for row in rows], "total": total, "limite": limite, "offset": offset}

@router.post("", status_code=status.HTTP_201_CREATED)
def crear(payload: AccidentePayload, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    record = create(db, user, correlation_id=request.state.correlation_id, **payload.model_dump())
    return serialize(get_record(db, user, record.id_accidente))

@router.get("/{accidente_id}")
def detalle(accidente_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return serialize(get_record(db, user, accidente_id))

@router.patch("/{accidente_id}")
def actualizar(accidente_id: str, payload: AccidenteUpdate, request: Request, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    values = payload.model_dump(exclude_unset=True); expected_version = values.pop("expected_version")
    return serialize(get_record(db, user, update(db, user, accidente_id, expected_version=expected_version, correlation_id=request.state.correlation_id, **values).id_accidente))
