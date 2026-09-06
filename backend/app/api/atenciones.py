"""Router de Atenciones. Espejo de app/services/atenciones.py — no usa la fábrica
EntityService (ver la nota en app/services/simple_entities.py)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.permissions import AuthenticatedUser, authorize
from app.models import Atencion
from app.services.atenciones import CAMPOS, create_atencion, restore_atencion, soft_delete_atencion, update_atencion
from app.services.records import get_active, get_history

router = APIRouter(prefix="/api/v1/atenciones", tags=["Atenciones"])


def _serialize(record: Atencion) -> dict:
    return {
        "id_atencion": record.id_atencion,
        **{campo: getattr(record, campo) for campo in CAMPOS},
        "version": record.version, "activo": record.activo, "eliminado": record.eliminado,
    }


@router.get("")
def listar(
    db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user),
    incluir_eliminados: bool = False, limite: int = Query(50, le=200), offset: int = Query(0, ge=0),
):
    authorize(user, "ATENCIONES", "read")
    stmt = select(Atencion)
    if not incluir_eliminados:
        stmt = stmt.where(Atencion.eliminado.is_(False))
    return [_serialize(r) for r in db.scalars(stmt.offset(offset).limit(limite)).all()]


@router.post("", status_code=201)
def crear(payload: dict, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    payload = dict(payload)
    motivo = payload.pop("motivo_auditoria", None) or "Creación de registro"
    correlation_id = payload.pop("correlation_id", "")
    registro = create_atencion(db, user, motivo_auditoria=motivo, correlation_id=correlation_id, **payload)
    return _serialize(registro)


@router.get("/{id_atencion}")
def obtener(id_atencion: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    authorize(user, "ATENCIONES", "read")
    return _serialize(get_active(db, Atencion, id_atencion, Atencion.id_atencion))


@router.patch("/{id_atencion}")
def actualizar(
    id_atencion: str, payload: dict, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    payload = dict(payload)
    expected_version = payload.pop("expected_version", None)
    motivo = payload.pop("motivo_auditoria", None) or "Edición de registro"
    correlation_id = payload.pop("correlation_id", "")
    registro = update_atencion(db, user, id_atencion, expected_version=expected_version,
                                motivo_auditoria=motivo, correlation_id=correlation_id, **payload)
    return _serialize(registro)


@router.post("/{id_atencion}/eliminacion")
def eliminar(
    id_atencion: str, payload: dict, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    registro = soft_delete_atencion(
        db, user, id_atencion, expected_version=payload.get("expected_version"),
        motivo=payload.get("motivo") or payload.get("reason") or "", correlation_id=payload.get("correlation_id", ""),
    )
    return _serialize(registro)


@router.post("/{id_atencion}/restauracion")
def restaurar(
    id_atencion: str, payload: dict | None = None, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    registro = restore_atencion(db, user, id_atencion, correlation_id=(payload or {}).get("correlation_id", ""))
    return _serialize(registro)


@router.get("/{id_atencion}/historial")
def historial(id_atencion: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    filas = get_history(db, user, "ATENCIONES", "atenciones", id_atencion)
    return [
        {"campo": f.campo, "accion": f.accion, "valor_anterior": f.valor_anterior,
         "valor_nuevo": f.valor_nuevo, "usuario": f.usuario, "fecha_hora": f.fecha_hora, "motivo": f.motivo}
        for f in filas
    ]
