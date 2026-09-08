"""Router de Casos y sus hijos. Espejo de app/services/casos.py."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.permissions import AuthenticatedUser, authorize
from app.models import Caso
from app.services.casos import (
    CAMPOS_CASO, CAMPOS_CIERRE, CAMPOS_COMPROMISO, CAMPOS_DERIVACION, CAMPOS_SEGUIMIENTO,
    add_compromiso, add_derivacion, add_seguimiento, close_caso, create_caso, is_sensitive_caso,
    list_compromisos as get_compromisos, list_seguimientos as get_seguimientos,
    soft_delete_caso, update_caso,
)
from app.services.records import get_active, get_history
from app.services.response_contexts import dynamic_context_ids

router = APIRouter(prefix="/api/v1/casos", tags=["Casos"])


def _serialize_caso(session: Session, record: Caso) -> dict:
    return {
        "id_caso": record.id_caso,
        "codigo_caso": record.codigo_caso,
        **{campo: getattr(record, campo) for campo in CAMPOS_CASO},
        "version": record.version, "activo": record.activo, "eliminado": record.eliminado,
        "sensible": is_sensitive_caso(session, record.nivel_sensibilidad),
    }


def _serialize_hijo(record, campos: tuple[str, ...], id_field: str) -> dict:
    return {id_field: getattr(record, id_field), **{c: getattr(record, c) for c in campos},
            "version": record.version}


@router.get("")
def listar(
    db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user),
    incluir_eliminados: bool = False, limite: int = Query(50, le=200), offset: int = Query(0, ge=0),
):
    authorize(user, "CASOS", "read")
    stmt = select(Caso)
    if not incluir_eliminados:
        stmt = stmt.where(
            Caso.eliminado.is_(False), Caso.id_caso.not_in(dynamic_context_ids("CASOS")),
        )
    return [_serialize_caso(db, r) for r in db.scalars(stmt.offset(offset).limit(limite)).all()]


@router.post("", status_code=201)
def crear(payload: dict, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    payload = dict(payload)
    motivo = payload.pop("motivo_auditoria", None) or "Apertura de caso"
    correlation_id = payload.pop("correlation_id", "")
    registro = create_caso(db, user, motivo_auditoria=motivo, correlation_id=correlation_id, **payload)
    return _serialize_caso(db, registro)


@router.get("/{id_caso}")
def obtener(id_caso: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    authorize(user, "CASOS", "read")
    registro = get_active(db, Caso, id_caso, Caso.id_caso)
    if is_sensitive_caso(db, registro.nivel_sensibilidad):
        authorize(user, "CASOS", "read", sensitive=True)
    return _serialize_caso(db, registro)


@router.patch("/{id_caso}")
def actualizar(
    id_caso: str, payload: dict, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    payload = dict(payload)
    expected_version = payload.pop("expected_version", None)
    motivo = payload.pop("motivo_auditoria", None) or "Edición de caso"
    correlation_id = payload.pop("correlation_id", "")
    registro = update_caso(db, user, id_caso, expected_version=expected_version,
                            motivo_auditoria=motivo, correlation_id=correlation_id, **payload)
    return _serialize_caso(db, registro)


@router.post("/{id_caso}/eliminacion")
def eliminar(
    id_caso: str, payload: dict, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    registro = soft_delete_caso(
        db, user, id_caso, expected_version=payload.get("expected_version"),
        motivo=payload.get("motivo") or payload.get("reason") or "", correlation_id=payload.get("correlation_id", ""),
    )
    return _serialize_caso(db, registro)


@router.get("/{id_caso}/historial")
def historial(id_caso: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    filas = get_history(db, user, "CASOS", "casos", id_caso)
    return [
        {"campo": f.campo, "accion": f.accion, "valor_anterior": f.valor_anterior,
         "valor_nuevo": f.valor_nuevo, "usuario": f.usuario, "fecha_hora": f.fecha_hora, "motivo": f.motivo}
        for f in filas
    ]


@router.post("/{id_caso}/seguimientos", status_code=201)
def crear_seguimiento(
    id_caso: str, payload: dict, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    payload = dict(payload)
    correlation_id = payload.pop("correlation_id", "")
    motivo = payload.pop("motivo_auditoria", None) or "Seguimiento"
    registro = add_seguimiento(db, user, id_caso, correlation_id=correlation_id, motivo_auditoria=motivo, **payload)
    return _serialize_hijo(registro, CAMPOS_SEGUIMIENTO, "id_seguimiento")


@router.get("/{id_caso}/seguimientos")
def listar_seguimientos(
    id_caso: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user),
):
    return [_serialize_hijo(row, CAMPOS_SEGUIMIENTO, "id_seguimiento") for row in get_seguimientos(db, user, id_caso)]


@router.post("/{id_caso}/derivaciones", status_code=201)
def crear_derivacion(
    id_caso: str, payload: dict, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    payload = dict(payload)
    correlation_id = payload.pop("correlation_id", "")
    motivo = payload.pop("motivo_auditoria", None) or "Derivación"
    registro = add_derivacion(db, user, id_caso, correlation_id=correlation_id, motivo_auditoria=motivo, **payload)
    return _serialize_hijo(registro, CAMPOS_DERIVACION, "id_derivacion")


@router.post("/{id_caso}/compromisos", status_code=201)
def crear_compromiso(
    id_caso: str, payload: dict, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    payload = dict(payload)
    correlation_id = payload.pop("correlation_id", "")
    motivo = payload.pop("motivo_auditoria", None) or "Compromiso"
    registro = add_compromiso(db, user, id_caso, correlation_id=correlation_id, motivo_auditoria=motivo, **payload)
    return _serialize_hijo(registro, CAMPOS_COMPROMISO, "id_compromiso")


@router.get("/{id_caso}/compromisos")
def listar_compromisos(
    id_caso: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user),
):
    return [_serialize_hijo(row, CAMPOS_COMPROMISO, "id_compromiso") for row in get_compromisos(db, user, id_caso)]


@router.post("/{id_caso}/cierres", status_code=201)
def crear_cierre(
    id_caso: str, payload: dict, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    payload = dict(payload)
    expected_version = payload.pop("expected_version", None)
    correlation_id = payload.pop("correlation_id", "")
    motivo = payload.pop("motivo_auditoria", None) or "Cierre de caso"
    registro = close_caso(db, user, id_caso, expected_version=expected_version,
                           correlation_id=correlation_id, motivo_auditoria=motivo, **payload)
    return _serialize_hijo(registro, CAMPOS_CIERRE, "id_cierre")
