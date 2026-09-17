from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.permissions import AuthenticatedUser
from app.models import Ausentismo, LoteImportacionAusentismo, Persona, User
from app.schemas.ausentismos import AusentismoOperativoPaginado, AusentismoOperativoRespuesta
from app.services.ausentismos import (
    ORIGEN_IMPORTACION_XLSX, listar_ausentismos_operativos, obtener_ausentismo_operativo,
)

router = APIRouter(prefix="/api/v1/ausentismos", tags=["Ausentismos"])


def serializar_operativo(row: tuple[Ausentismo, Persona, LoteImportacionAusentismo | None, User | None]) -> dict:
    ausentismo, persona, lote, autor = row
    return {
        "id_ausentismo": ausentismo.id_ausentismo,
        "persona_id": persona.id_persona,
        "persona": persona.nombre,
        "cedula": persona.cedula,
        "area": persona.area,
        "fecha_inicio": ausentismo.fecha_inicio,
        "fecha_fin": ausentismo.fecha_fin,
        "tipo_ausentismo": ausentismo.tipo_ausentismo,
        "motivo": ausentismo.motivo,
        "observacion": ausentismo.observacion,
        "fecha_registro": ausentismo.fecha_creacion,
        "registrado_por_id": autor.id_usuario if autor else None,
        "registrado_por": autor.nombre if autor else None,
        "origen": ORIGEN_IMPORTACION_XLSX if lote else None,
        "lote_id": lote.id_lote if lote else None,
        "lote_nombre_archivo": lote.nombre_archivo if lote else None,
    }


@router.get("", response_model=AusentismoOperativoPaginado)
def listar(
    db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user),
    nombre: str | None = None, cedula: str | None = None, area: str | None = None,
    tipo_ausentismo: str | None = None, desde: str | None = None, hasta: str | None = None,
    origen: str | None = None, lote_id: str | None = None,
    limite: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0),
):
    rows, total = listar_ausentismos_operativos(
        db, user, nombre=nombre, cedula=cedula, area=area, tipo_ausentismo=tipo_ausentismo,
        desde=desde, hasta=hasta, origen=origen, lote_id=lote_id, limit=limite, offset=offset,
    )
    return {"items": [serializar_operativo(row) for row in rows], "total": total, "limite": limite, "offset": offset}


@router.get("/{ausentismo_id}", response_model=AusentismoOperativoRespuesta)
def detalle(ausentismo_id: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return serializar_operativo(obtener_ausentismo_operativo(db, user, ausentismo_id))
