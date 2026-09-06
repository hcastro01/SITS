"""Fábrica de routers CRUD para las entidades declaradas con EntityService (Novedades,
Recorridos, HallazgosRecorrido, Personas). El payload se acepta como `dict` libre: la
allowlist real de campos vive en el servicio (EntityService._rechazar_desconocidos), no
aquí — esta capa solo traduce HTTP a llamadas de servicio.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.permissions import AuthenticatedUser, authorize
from app.services.records import get_active, get_history
from app.services.simple_entities import EntityService


def build_router(entidad: EntityService, prefix: str, tag: str) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=[tag])
    id_column = getattr(entidad.model, entidad.id_field)

    @router.get("")
    def listar(
        db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user),
        incluir_eliminados: bool = False, limite: int = Query(50, le=200), offset: int = Query(0, ge=0),
    ):
        authorize(user, entidad.modulo, "read")
        stmt = select(entidad.model)
        if not incluir_eliminados:
            stmt = stmt.where(entidad.model.eliminado.is_(False))
        registros = db.scalars(stmt.offset(offset).limit(limite)).all()
        return [entidad.serialize(r) for r in registros]

    @router.post("", status_code=201)
    def crear(payload: dict, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
        payload = dict(payload)
        motivo = payload.pop("motivo", None) or payload.pop("reason", None) or "Creación de registro"
        correlation_id = payload.pop("correlation_id", "")
        registro = entidad.create(db, user, motivo_auditoria=motivo, correlation_id=correlation_id, **payload)
        return entidad.serialize(registro)

    @router.get("/{id_valor}")
    def obtener(id_valor: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
        authorize(user, entidad.modulo, "read")
        registro = get_active(db, entidad.model, id_valor, id_column)
        return entidad.serialize(registro)

    @router.patch("/{id_valor}")
    def actualizar(
        id_valor: str, payload: dict, db: Session = Depends(get_db),
        user: AuthenticatedUser = Depends(get_current_user),
    ):
        payload = dict(payload)
        expected_version = payload.pop("expected_version", None)
        motivo = payload.pop("motivo", None) or payload.pop("reason", None) or "Edición de registro"
        correlation_id = payload.pop("correlation_id", "")
        registro = entidad.update(db, user, id_valor, expected_version=expected_version,
                                   motivo_auditoria=motivo, correlation_id=correlation_id, **payload)
        return entidad.serialize(registro)

    @router.post("/{id_valor}/eliminacion")
    def eliminar(
        id_valor: str, payload: dict, db: Session = Depends(get_db),
        user: AuthenticatedUser = Depends(get_current_user),
    ):
        registro = entidad.soft_delete(
            db, user, id_valor, expected_version=payload.get("expected_version"),
            motivo=payload.get("motivo") or payload.get("reason") or "", correlation_id=payload.get("correlation_id", ""),
        )
        return entidad.serialize(registro)

    @router.post("/{id_valor}/restauracion")
    def restaurar(
        id_valor: str, payload: dict | None = None, db: Session = Depends(get_db),
        user: AuthenticatedUser = Depends(get_current_user),
    ):
        registro = entidad.restore(db, user, id_valor, correlation_id=(payload or {}).get("correlation_id", ""))
        return entidad.serialize(registro)

    @router.get("/{id_valor}/historial")
    def historial(
        id_valor: str, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user),
    ):
        filas = get_history(db, user, entidad.modulo, entidad.tabla, id_valor)
        return [
            {"campo": f.campo, "accion": f.accion, "valor_anterior": f.valor_anterior,
             "valor_nuevo": f.valor_nuevo, "usuario": f.usuario, "fecha_hora": f.fecha_hora, "motivo": f.motivo}
            for f in filas
        ]

    return router
