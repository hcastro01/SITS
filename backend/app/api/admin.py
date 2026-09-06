"""Router de Administración: usuarios, roles y permisos."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.permissions import AuthenticatedUser
from app.services.admin import list_administration, save_permission, save_user_role

router = APIRouter(prefix="/api/v1/admin", tags=["Administración"])


@router.get("/usuarios")
def listar(db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return list_administration(db, user)


@router.patch("/usuarios/{id_usuario}")
def actualizar_usuario(
    id_usuario: str, payload: dict, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    return save_user_role(
        db, user, id_usuario, rol_id=payload["rol_id"], estado=payload.get("estado", "ACTIVO"),
        expected_version=payload.get("expected_version"), correlation_id=payload.get("correlation_id", ""),
    )


@router.put("/roles/{rol_id}/permisos/{modulo}")
def actualizar_permiso(
    rol_id: str, modulo: str, payload: dict, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    return save_permission(
        db, user, rol_id, modulo, derechos=payload.get("derechos", {}),
        expected_version=payload.get("expected_version"), correlation_id=payload.get("correlation_id", ""),
    )
