"""Router de Formularios, Preguntas, Opciones, Reglas y Respuestas."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.permissions import AuthenticatedUser, authorize
from app.models import Formulario, Pregunta
from app.services.formularios import CAMPOS as CAMPOS_FORMULARIO
from app.services.formularios import MODULE as FORMULARIOS_MODULE
from app.services.formularios import change_status, create_formulario, update_formulario
from app.services.opciones_pregunta import opciones_pregunta
from app.services.preguntas import preguntas
from app.services.records import get_active
from app.services.reglas_formulario import reglas_formulario
from app.services.respuestas_formulario import save_response

router = APIRouter(prefix="/api/v1/formularios", tags=["Formularios"])


def _serialize_formulario(record: Formulario) -> dict:
    return {
        "id_formulario": record.id_formulario,
        **{c: getattr(record, c) for c in CAMPOS_FORMULARIO},
        "estado": record.estado, "fecha_publicacion": record.fecha_publicacion,
        "version": record.version, "activo": record.activo, "eliminado": record.eliminado,
    }


@router.get("")
def listar(
    db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user),
    incluir_eliminados: bool = False, limite: int = Query(50, le=200), offset: int = Query(0, ge=0),
):
    authorize(user, FORMULARIOS_MODULE, "read")
    stmt = select(Formulario)
    if not incluir_eliminados:
        stmt = stmt.where(Formulario.eliminado.is_(False))
    return [_serialize_formulario(r) for r in db.scalars(stmt.offset(offset).limit(limite)).all()]


@router.get("/{id_formulario}")
def obtener(id_formulario: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    authorize(user, FORMULARIOS_MODULE, "read")
    formulario = get_active(db, Formulario, id_formulario, Formulario.id_formulario)
    filas_preguntas = db.scalars(
        select(Pregunta)
        .where(Pregunta.id_formulario == id_formulario, Pregunta.eliminado.is_(False))
        .order_by(Pregunta.orden)
    ).all()
    return {**_serialize_formulario(formulario), "preguntas": [preguntas.serialize(p) for p in filas_preguntas]}


@router.post("", status_code=201)
def crear(payload: dict, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    payload = dict(payload)
    motivo = payload.pop("motivo_auditoria", None) or "Alta de formulario"
    correlation_id = payload.pop("correlation_id", "")
    registro = create_formulario(db, user, motivo_auditoria=motivo, correlation_id=correlation_id, **payload)
    return _serialize_formulario(registro)


@router.patch("/{id_formulario}")
def actualizar(
    id_formulario: str, payload: dict, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    payload = dict(payload)
    expected_version = payload.pop("expected_version", None)
    motivo = payload.pop("motivo_auditoria", None) or "Edición de formulario"
    correlation_id = payload.pop("correlation_id", "")
    registro = update_formulario(db, user, id_formulario, expected_version=expected_version,
                                  motivo_auditoria=motivo, correlation_id=correlation_id, **payload)
    return _serialize_formulario(registro)


@router.patch("/{id_formulario}/estado")
def cambiar_estado(
    id_formulario: str, payload: dict, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    registro = change_status(
        db, user, id_formulario, payload["estado"],
        expected_version=payload.get("expected_version"), correlation_id=payload.get("correlation_id", ""),
    )
    return _serialize_formulario(registro)


@router.post("/{id_formulario}/preguntas", status_code=201)
def crear_pregunta(
    id_formulario: str, payload: dict, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    payload = dict(payload)
    motivo = payload.pop("motivo_auditoria", None) or "Alta de pregunta"
    correlation_id = payload.pop("correlation_id", "")
    registro = preguntas.create(db, user, motivo_auditoria=motivo, correlation_id=correlation_id,
                                 id_formulario=id_formulario, **payload)
    return preguntas.serialize(registro)


@router.patch("/preguntas/{id_pregunta}")
def actualizar_pregunta(
    id_pregunta: str, payload: dict, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    payload = dict(payload)
    expected_version = payload.pop("expected_version", None)
    motivo = payload.pop("motivo_auditoria", None) or "Edición de pregunta"
    correlation_id = payload.pop("correlation_id", "")
    registro = preguntas.update(db, user, id_pregunta, expected_version=expected_version,
                                 motivo_auditoria=motivo, correlation_id=correlation_id, **payload)
    return preguntas.serialize(registro)


@router.post("/preguntas/{id_pregunta}/opciones", status_code=201)
def crear_opcion(
    id_pregunta: str, payload: dict, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    payload = dict(payload)
    motivo = payload.pop("motivo_auditoria", None) or "Alta de opción"
    correlation_id = payload.pop("correlation_id", "")
    registro = opciones_pregunta.create(db, user, motivo_auditoria=motivo, correlation_id=correlation_id,
                                         id_pregunta=id_pregunta, **payload)
    return opciones_pregunta.serialize(registro)


@router.post("/{id_formulario}/reglas", status_code=201)
def crear_regla(
    id_formulario: str, payload: dict, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    payload = dict(payload)
    motivo = payload.pop("motivo_auditoria", None) or "Alta de regla"
    correlation_id = payload.pop("correlation_id", "")
    registro = reglas_formulario.create(db, user, motivo_auditoria=motivo, correlation_id=correlation_id,
                                         id_formulario=id_formulario, **payload)
    return reglas_formulario.serialize(registro)


@router.post("/{id_formulario}/respuestas", status_code=201)
def responder(
    id_formulario: str, payload: dict, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    envio = save_response(
        db, user, id_formulario,
        draft=bool(payload.get("borrador", False)),
        respuestas=payload.get("respuestas", []),
        id_envio_cliente=payload.get("id_envio_cliente"),
        id_registro_proceso=payload.get("id_registro_proceso"),
        correlation_id=payload.get("correlation_id", ""),
    )
    return {"id_respuesta": envio.id_respuesta, "estado": envio.estado, "fecha_respuesta": envio.fecha_respuesta}
