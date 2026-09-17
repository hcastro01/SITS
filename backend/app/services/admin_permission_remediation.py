"""Remediación acotada de permisos faltantes de ROLE_ADMIN.

No reutiliza ``seed_security``: sólo conoce las filas autorizadas por el
incidente y nunca actualiza una fila existente.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Permission
from app.services.audit import log_change

ROLE_ADMIN = "ROLE_ADMIN"
TARGET_MODULES = (
    "RIESGOS_TRABAJO",
    "AUSENTISMO",
    "ACCIDENTES",
    "PRODUCCION",
    "OFICINA",
)
ALL_RIGHTS = {
    "puede_crear": True,
    "puede_leer": True,
    "puede_editar": True,
    "puede_eliminar": True,
    "puede_sensible": True,
    "puede_exportar": True,
}
AUDIT_USER = "SYSTEM_MAINTENANCE"
AUDIT_REASON = "Remediación controlada ROLE_ADMIN: permisos faltantes del hotfix Departamento Médico"


def missing_target_modules(session: Session) -> tuple[str, ...]:
    """Devuelve sólo objetivos sin fila; una fila con derechos falsos existe."""
    existing = set(session.scalars(select(Permission.modulo).where(
        Permission.rol_id == ROLE_ADMIN,
        Permission.modulo.in_(TARGET_MODULES),
    )))
    return tuple(module for module in TARGET_MODULES if module not in existing)


def insert_missing_role_admin_permissions(session: Session, *, correlation_id: str) -> tuple[str, ...]:
    """Inserta exclusivamente objetivos ausentes y deja auditoría en la misma transacción."""
    inserted: list[str] = []
    for module in missing_target_modules(session):
        permission = Permission(
            id_permiso=f"{ROLE_ADMIN}:{module}",
            rol_id=ROLE_ADMIN,
            modulo=module,
            **ALL_RIGHTS,
        )
        session.add(permission)
        session.flush()
        log_change(
            session,
            "permisos",
            permission.id_permiso,
            "CREATE",
            {},
            {"rol_id": ROLE_ADMIN, "modulo": module, **ALL_RIGHTS},
            AUDIT_USER,
            AUDIT_REASON,
            correlation_id,
        )
        inserted.append(module)
    return tuple(inserted)
