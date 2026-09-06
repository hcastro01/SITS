"""GET /bootstrap: perfil, permisos y módulos visibles para el usuario vigente.
Equivalente a Base Sistema/Code.gs:12-25 (getBootstrapData)."""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.permissions import AuthenticatedUser

router = APIRouter(prefix="/api/v1", tags=["Bootstrap"])


@router.get("/bootstrap")
def bootstrap(user: AuthenticatedUser = Depends(get_current_user)):
    modulos_visibles = sorted(
        modulo for modulo, acciones in user.permisos.items() if acciones.get("read") or acciones.get("create")
    )
    return {
        "usuario": {
            "id_usuario": user.id_usuario, "correo": user.correo, "nombre": user.nombre,
            "rol_id": user.rol_id, "rol_nombre": user.rol_nombre,
        },
        "permisos": user.permisos,
        "modulos": modulos_visibles,
    }
