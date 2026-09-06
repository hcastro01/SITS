"""Núcleo de autorización. Equivalente a Base Sistema/AuthService.gs (TSAuth).

Política única: no existe más de un criterio de sensibilidad en el sistema. El OR entre
el permiso sensible del módulo y el de CASOS (Base Sistema/SearchService.gs:95,123 —
MIGRACION_FASE_1.md §6) no se reproduce aquí: para hijos de casos sensibles se exige
AND sobre ambos permisos, como ya hacía Base Sistema/DriveService.gs:46-47.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Permission, Role, User

ACTIONS = ("create", "read", "edit", "delete", "sensitive", "export")

# Mapea la acción RPC (Base Sistema/AuthService.gs:2, ACTION_COLUMNS) a la columna en español.
_ACTION_TO_FIELD = {
    "create": "puede_crear",
    "read": "puede_leer",
    "edit": "puede_editar",
    "delete": "puede_eliminar",
    "sensitive": "puede_sensible",
    "export": "puede_exportar",
}


@dataclass(frozen=True)
class AuthenticatedUser:
    """Usuario vigente con su matriz de permisos ya resuelta (AuthService.gs:12-24)."""

    id_usuario: str
    correo: str
    nombre: str
    rol_id: str
    rol_nombre: str
    permisos: dict[str, dict[str, bool]]  # modulo -> {create, read, edit, delete, sensitive, export}


def resolve_current_user(session: Session, correo: str) -> AuthenticatedUser:
    """Carga y valida el usuario vigente. Equivalente a TSAuth.current() (AuthService.gs:12-24).

    No resuelve identidad por sí mismo: recibe el correo ya extraído de la sesión/token
    verificado (pendiente de MIGRACION_FASE_1.md §10, bloqueo de identidad).
    """
    correo_normalizado = correo.strip().lower()
    user = session.scalar(select(User).where(User.correo == correo_normalizado))
    if user is None:
        raise AppError("USER_NOT_REGISTERED", "Su usuario no está registrado en la aplicación.", 403)
    if user.eliminado or not user.activo or user.estado != "ACTIVO":
        raise AppError("USER_DISABLED", "Su usuario se encuentra inactivo.", 403)
    role = session.get(Role, user.rol_id)
    if role is None or role.eliminado or not role.activo:
        raise AppError("ROLE_NOT_FOUND", "El rol asignado no se encuentra activo.", 403)
    permisos_rows = session.scalars(
        select(Permission).where(
            Permission.rol_id == user.rol_id,
            Permission.activo.is_(True),
            Permission.eliminado.is_(False),
        )
    ).all()
    permisos = {
        row.modulo: {action: getattr(row, field) for action, field in _ACTION_TO_FIELD.items()}
        for row in permisos_rows
    }
    return AuthenticatedUser(
        id_usuario=user.id_usuario, correo=user.correo, nombre=user.nombre,
        rol_id=user.rol_id, rol_nombre=role.nombre, permisos=permisos,
    )


def can(user: AuthenticatedUser, module: str, action: str) -> bool:
    """Equivalente a TSAuth.can (AuthService.gs:54-58)."""
    rights = user.permisos.get(module)
    return bool(rights and rights.get(action, False))


def authorize(user: AuthenticatedUser, module: str, action: str, *, sensitive: bool = False) -> AuthenticatedUser:
    """Equivalente a TSAuth.authorize (AuthService.gs:43-52).

    `sensitive` es una comprobación ADITIVA sobre la acción principal, nunca alternativa.
    """
    if action not in ACTIONS:
        raise AppError("INVALID_ACTION", "Acción de permiso inválida.", 400)
    if not can(user, module, action):
        raise AppError("FORBIDDEN", "No tiene permisos para realizar esta acción.", 403)
    if sensitive and not can(user, module, "sensitive"):
        raise AppError("SENSITIVE_FORBIDDEN", "No tiene permisos para consultar información sensible.", 403)
    return user


def authorize_sensitive_child(user: AuthenticatedUser, child_module: str, action: str) -> AuthenticatedUser:
    """Para hijos de casos sensibles (Seguimientos, Derivaciones, Compromisos, Cierres,
    Documentos): exige el permiso sobre el hijo Y sobre CASOS. AND, no OR."""
    authorize(user, child_module, action, sensitive=True)
    authorize(user, "CASOS", "read", sensitive=True)
    return user
