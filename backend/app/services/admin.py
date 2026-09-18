"""Servicio de administración: usuarios, roles y permisos.

Equivalente a Base Sistema/AuthService.gs (listAdministration, saveUserRole,
savePermissions). Conserva las dos protecciones verificadas en la auditoría: no se puede
cambiar de rol ni desactivar al último administrador (AuthService.gs:141-143), y el rol
Administrador no puede perder lectura/edición de ADMINISTRACION (AuthService.gs:166).
El alta de usuarios exige de forma independiente ADMINISTRACION:create.
"""

import re
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, authorize, can
from app.models import Permission, Role, User
from app.services.audit import log_change
from app.services.passwords import hash_password
from app.services.records import apply_restore, apply_soft_delete, check_expected_version, creation_metadata, mark_updated
from app.services.sessions import revoke_user_sessions

ADMIN_MODULE = "ADMINISTRACION"
ADMIN_ROLE_ID = "ROLE_ADMIN"

ACTION_TO_FIELD = {
    "create": "puede_crear", "read": "puede_leer", "edit": "puede_editar",
    "delete": "puede_eliminar", "sensitive": "puede_sensible", "export": "puede_exportar",
}

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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


def list_administration(session: Session, user: AuthenticatedUser, *, include_deleted: bool = False) -> dict:
    authorize(user, ADMIN_MODULE, "read")
    if include_deleted:
        authorize(user, ADMIN_MODULE, "delete")
    users_statement = select(User).order_by(User.nombre)
    if not include_deleted:
        users_statement = users_statement.where(User.eliminado.is_(False))
    usuarios = session.scalars(users_statement).all()
    roles = session.scalars(select(Role).order_by(Role.nombre)).all()
    permisos = session.scalars(select(Permission)).all()
    return {
        "usuarios": [serialize_user(u) for u in usuarios],
        "roles": [serialize_role(r) for r in roles],
        "permisos": [serialize_permission(p) for p in permisos],
        "puede_eliminar_usuarios": can(user, ADMIN_MODULE, "delete"),
    }


def create_user(
    session: Session, admin: AuthenticatedUser, *, correo: str, nombre: str,
    rol_id: str, password: str, correlation_id: str = "",
) -> dict:
    authorize(admin, ADMIN_MODULE, "create")
    correo_normalizado = correo.strip().lower()
    nombre_normalizado = nombre.strip()
    if not correo_normalizado or not nombre_normalizado:
        raise AppError("INVALID_INPUT", "El correo y el nombre son obligatorios.", 422)
    if EMAIL_PATTERN.fullmatch(correo_normalizado) is None:
        raise AppError("INVALID_EMAIL", "Ingrese un correo electrónico válido.", 422)
    if session.scalar(select(User).where(func.lower(User.correo) == correo_normalizado)) is not None:
        raise AppError("USER_ALREADY_EXISTS", "Ya existe un usuario registrado con ese correo.", 409)
    if session.get(Role, rol_id) is None:
        raise AppError("ROLE_NOT_FOUND", "El rol seleccionado no existe.", 422)
    try:
        password_hash = hash_password(password)
    except ValueError as error:
        raise AppError("WEAK_PASSWORD", str(error), 422) from None

    usuario = User(
        id_usuario=str(uuid4()), correo=correo_normalizado, nombre=nombre_normalizado,
        rol_id=rol_id, password_hash=password_hash, estado="ACTIVO", activo=True,
        eliminado=False, **creation_metadata(admin.correo),
    )
    session.add(usuario)
    session.flush()
    serialized = serialize_user(usuario)
    log_change(
        session, "usuarios", usuario.id_usuario, "CREATE", {}, serialized,
        admin.correo, "Alta de usuario", correlation_id,
    )
    return serialized


def save_user(
    session: Session, admin: AuthenticatedUser, id_usuario: str, *,
    nombre: str, correo: str, rol_id: str, estado: str, expected_version: int | None, correlation_id: str,
) -> dict:
    authorize(admin, ADMIN_MODULE, "edit")
    usuario = session.get(User, id_usuario)
    if usuario is None:
        raise AppError("NOT_FOUND", "Usuario no encontrado.", 404)
    nombre_normalizado = nombre.strip()
    correo_normalizado = correo.strip().lower()
    if not nombre_normalizado:
        raise AppError("INVALID_INPUT", "El nombre es obligatorio.", 422)
    if EMAIL_PATTERN.fullmatch(correo_normalizado) is None:
        raise AppError("INVALID_EMAIL", "Ingrese un correo electrónico válido.", 422)
    correo_existente = session.scalar(select(User).where(
        func.lower(User.correo) == correo_normalizado, User.id_usuario != id_usuario,
    ))
    if correo_existente is not None:
        raise AppError("USER_ALREADY_EXISTS", "Ya existe un usuario registrado con ese correo.", 409)
    if session.get(Role, rol_id) is None:
        raise AppError("ROLE_NOT_FOUND", "El rol seleccionado no existe.", 422)
    if estado not in {"ACTIVO", "INACTIVO"}:
        raise AppError("INVALID_INPUT", "El estado seleccionado no es válido.", 422)
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
    usuario.nombre = nombre_normalizado
    usuario.correo = correo_normalizado
    usuario.rol_id = rol_id
    usuario.estado = estado
    usuario.activo = estado == "ACTIVO"
    mark_updated(usuario, admin.correo)
    log_change(session, "usuarios", id_usuario, "UPDATE", before, serialize_user(usuario),
               admin.correo, "Actualización de usuario", correlation_id)
    return serialize_user(usuario)


def save_user_role(
    session: Session, admin: AuthenticatedUser, id_usuario: str, *,
    rol_id: str, estado: str, expected_version: int | None, correlation_id: str,
) -> dict:
    """Compatibilidad para consumidores internos del contrato anterior."""
    usuario = session.get(User, id_usuario)
    if usuario is None:
        raise AppError("NOT_FOUND", "Usuario no encontrado.", 404)
    return save_user(
        session, admin, id_usuario, nombre=usuario.nombre, correo=usuario.correo,
        rol_id=rol_id, estado=estado, expected_version=expected_version, correlation_id=correlation_id,
    )


def reset_user_password(
    session: Session, admin: AuthenticatedUser, id_usuario: str, *,
    password: str, expected_version: int | None, correlation_id: str,
) -> dict:
    """Restablece una contraseña sin serializar ni auditar secretos o hashes."""
    authorize(admin, ADMIN_MODULE, "edit")
    usuario = session.get(User, id_usuario)
    if usuario is None:
        raise AppError("NOT_FOUND", "Usuario no encontrado.", 404)
    check_expected_version(usuario, expected_version)
    try:
        nuevo_hash = hash_password(password)
    except ValueError as error:
        raise AppError("WEAK_PASSWORD", str(error), 422) from None
    usuario.password_hash = nuevo_hash
    revoke_user_sessions(session, usuario.id_usuario)
    mark_updated(usuario, admin.correo)
    log_change(
        session, "usuarios", id_usuario, "UPDATE", {},
        {"evento_seguridad": "Restablecimiento de contraseña por administrador"},
        admin.correo, "Restablecimiento de contraseña por administrador", correlation_id,
    )
    return serialize_user(usuario)


def soft_delete_user(
    session: Session, admin: AuthenticatedUser, id_usuario: str, *,
    expected_version: int | None, motivo: str, correlation_id: str,
) -> dict:
    """Desactiva un usuario sin borrar su historial y revoca sus sesiones vigentes."""
    authorize(admin, ADMIN_MODULE, "delete")
    usuario = session.get(User, id_usuario)
    if usuario is None:
        raise AppError("NOT_FOUND", "Usuario no encontrado.", 404)
    if usuario.eliminado:
        raise AppError("USER_ALREADY_DELETED", "El usuario ya se encuentra eliminado.", 409)
    if usuario.id_usuario == admin.id_usuario:
        raise AppError("SELF_DELETE_FORBIDDEN", "No puede eliminar su propia cuenta.", 409)
    if usuario.rol_id == ADMIN_ROLE_ID and usuario.activo and usuario.estado == "ACTIVO":
        otros_admins = session.scalar(
            select(func.count()).select_from(User).where(
                User.rol_id == ADMIN_ROLE_ID,
                User.id_usuario != id_usuario,
                User.activo.is_(True),
                User.estado == "ACTIVO",
                User.eliminado.is_(False),
            )
        )
        if not otros_admins:
            raise AppError("LAST_ADMIN", "No se puede eliminar al último administrador activo.", 409)
    check_expected_version(usuario, expected_version)
    before = serialize_user(usuario)
    apply_soft_delete(usuario, admin.correo, motivo)
    mark_updated(usuario, admin.correo)
    revoke_user_sessions(session, usuario.id_usuario)
    log_change(session, "usuarios", id_usuario, "DELETE", before, serialize_user(usuario),
               admin.correo, motivo.strip(), correlation_id)
    return serialize_user(usuario)


def restore_user(
    session: Session, admin: AuthenticatedUser, id_usuario: str, *,
    expected_version: int | None, correlation_id: str,
) -> dict:
    """Restaura un usuario eliminado sin reactivar sus sesiones ni tocar su contraseña."""
    authorize(admin, ADMIN_MODULE, "delete")
    usuario = session.get(User, id_usuario)
    if usuario is None:
        raise AppError("NOT_FOUND", "Usuario no encontrado.", 404)
    if not usuario.eliminado:
        raise AppError("USER_NOT_DELETED", "El usuario no se encuentra eliminado.", 409)
    check_expected_version(usuario, expected_version)
    before = serialize_user(usuario)
    apply_restore(usuario)
    mark_updated(usuario, admin.correo)
    log_change(session, "usuarios", id_usuario, "RESTORE", before, serialize_user(usuario),
               admin.correo, "Restauración de usuario", correlation_id)
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
