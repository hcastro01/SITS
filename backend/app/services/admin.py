"""Servicio de administración: usuarios, roles y permisos.

Equivalente a Base Sistema/AuthService.gs (listAdministration, saveUserRole,
savePermissions). Conserva las dos protecciones verificadas en la auditoría: no se puede
cambiar de rol ni desactivar al último administrador (AuthService.gs:141-143), y el rol
Administrador no puede perder lectura/edición de ADMINISTRACION (AuthService.gs:166). El
alta de usuarios nuevos no ocurre aquí: solo por app/cli/bootstrap_admin.py o, en el
futuro, por la importación histórica — nunca por esta API.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, authorize
from app.models import Permission, Role, User
from app.services.audit import log_change
from app.services.records import check_expected_version, mark_updated

ADMIN_MODULE = "ADMINISTRACION"
ADMIN_ROLE_ID = "ROLE_ADMIN"

ACTION_TO_FIELD = {
    "create": "puede_crear", "read": "puede_leer", "edit": "puede_editar",
    "delete": "puede_eliminar", "sensitive": "puede_sensible", "export": "puede_exportar",
}


def serialize_user(user: User) -> dict:
    return {"id_usuario": user.id_usuario, "correo": user.correo, "nombre": user.nombre,
            "rol_id": user.rol_id, "estado": user.estado, "activo": user.activo,
            "eliminado": user.eliminado, "version": user.version}


def serialize_role(role: Role) -> dict:
    return {"id_rol": role.id_rol, "nombre": role.nombre, "descripcion": role.descripcion}


def serialize_permission(permiso: Permission) -> dict:
    return {
        "id_permiso": permiso.id_permiso, "rol_id": permiso.rol_id, "modulo": permiso.modulo,
        **{accion: getattr(permiso, campo) for accion, campo in ACTION_TO_FIELD.items()},
        "version": permiso.version,
    }


def list_administration(session: Session, user: AuthenticatedUser) -> dict:
    authorize(user, ADMIN_MODULE, "read")
    usuarios = session.scalars(select(User).order_by(User.nombre)).all()
    roles = session.scalars(select(Role).order_by(Role.nombre)).all()
    permisos = session.scalars(select(Permission)).all()
    return {
        "usuarios": [serialize_user(u) for u in usuarios],
        "roles": [serialize_role(r) for r in roles],
        "permisos": [serialize_permission(p) for p in permisos],
    }


def save_user_role(
    session: Session, admin: AuthenticatedUser, id_usuario: str, *,
    rol_id: str, estado: str, expected_version: int | None, correlation_id: str,
) -> dict:
    authorize(admin, ADMIN_MODULE, "edit")
    usuario = session.get(User, id_usuario)
    if usuario is None:
        raise AppError("NOT_FOUND", "Usuario no encontrado.", 404)
    if session.get(Role, rol_id) is None:
        raise AppError("ROLE_NOT_FOUND", "El rol seleccionado no existe.", 422)
    if usuario.rol_id == ADMIN_ROLE_ID and (rol_id != ADMIN_ROLE_ID or estado != "ACTIVO"):
        otros_admins = session.scalar(
            select(func.count()).select_from(User).where(
                User.rol_id == ADMIN_ROLE_ID, User.id_usuario != id_usuario,
                User.estado == "ACTIVO", User.eliminado.is_(False),
            )
        )
        if not otros_admins:
            raise AppError("LAST_ADMIN", "No se puede cambiar el rol o desactivar al último administrador.", 409)
    check_expected_version(usuario, expected_version)
    before = serialize_user(usuario)
    usuario.rol_id = rol_id
    usuario.estado = estado
    mark_updated(usuario, admin.correo)
    log_change(session, "usuarios", id_usuario, "UPDATE", before, serialize_user(usuario),
               admin.correo, "Asignación de rol", correlation_id)
    return serialize_user(usuario)


def save_permission(
    session: Session, admin: AuthenticatedUser, rol_id: str, modulo: str, *,
    derechos: dict[str, bool], expected_version: int | None, correlation_id: str,
) -> dict:
    authorize(admin, ADMIN_MODULE, "edit")
    if session.get(Role, rol_id) is None:
        raise AppError("ROLE_NOT_FOUND", "El rol seleccionado no existe.", 422)
    permiso = session.scalar(select(Permission).where(Permission.rol_id == rol_id, Permission.modulo == modulo))
    if permiso is None:
        raise AppError("NOT_FOUND", "Permiso no encontrado.", 404)
    if rol_id == ADMIN_ROLE_ID and modulo == ADMIN_MODULE:
        lectura_final = derechos.get("read", permiso.puede_leer)
        edicion_final = derechos.get("edit", permiso.puede_editar)
        if not lectura_final or not edicion_final:
            raise AppError(
                "CORE_ADMIN_PERMISSION",
                "El rol Administrador debe conservar lectura y edición de Administración.", 409,
            )
    check_expected_version(permiso, expected_version)
    before = serialize_permission(permiso)
    for accion, campo in ACTION_TO_FIELD.items():
        if accion in derechos:
            setattr(permiso, campo, bool(derechos[accion]))
    mark_updated(permiso, admin.correo)
    log_change(session, "permisos", permiso.id_permiso, "UPDATE", before, serialize_permission(permiso),
               admin.correo, "Cambio de permisos", correlation_id)
    return serialize_permission(permiso)
