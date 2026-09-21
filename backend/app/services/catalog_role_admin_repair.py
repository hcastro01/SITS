"""Reparación explícita y reversible de cinco nodos y cuatro permisos.

Este módulo no llama a los seeds.  Las definiciones son una copia trazable de
``security_seed.MODULOS_ARQUITECTURA`` a la fecha de la reparación, para que
una aplicación futura no dependa de un seed que pudiera cambiar.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Auditoria, ModuloSistema, Permission, Role
from app.services.audit import log_change


ROLE_ADMIN = "ROLE_ADMIN"
AUDIT_USER = "SYSTEM_MAINTENANCE"
CORRELATION_PREFIX = "catalog-role-admin-repair"
AUDIT_REASON = "Reparación controlada de catálogo y permisos ROLE_ADMIN"
REVERSAL_REASON = "Reversión controlada de reparación de catálogo y permisos ROLE_ADMIN"
RIGHT_FIELDS = (
    "puede_crear", "puede_leer", "puede_editar", "puede_eliminar",
    "puede_sensible", "puede_exportar",
)
ALL_RIGHTS = dict.fromkeys(RIGHT_FIELDS, True)

# Valores revisados directamente en security_seed.MODULOS_ARQUITECTURA.
CATALOG_TARGETS = (
    {"id_modulo": "sits-actividades-tabla", "nombre": "Tabla de actividades", "permiso": "ACTIVIDADES",
     "ruta": "/trabajo-social/actividades", "icono": "☷", "padre_id_modulo": "sits-actividades", "orden": 21},
    {"id_modulo": "sits-actividades-registrar", "nombre": "Registrar actividad", "permiso": "ACTIVIDADES",
     "ruta": "/trabajo-social/actividades/registrar", "icono": "+", "padre_id_modulo": "sits-actividades", "orden": 22},
    {"id_modulo": "sits-beneficios", "nombre": "Beneficios", "permiso": "BENEFICIOS",
     "ruta": "/trabajo-social/oficina/beneficios", "icono": "★", "padre_id_modulo": "sits-oficina", "orden": 51},
    {"id_modulo": "sits-prestamos", "nombre": "Préstamos", "permiso": "PRESTAMOS",
     "ruta": "/trabajo-social/oficina/prestamos", "icono": "$", "padre_id_modulo": "sits-oficina", "orden": 53},
    {"id_modulo": "sits-seguros", "nombre": "Seguro", "permiso": "SEGUROS",
     "ruta": "/trabajo-social/oficina/seguro", "icono": "◈", "padre_id_modulo": "sits-oficina", "orden": 54},
)
PERMISSION_TARGETS = ("ACTIVIDADES", "BENEFICIOS", "PRESTAMOS", "SEGUROS")

# ACTIVIDADES se comparte, deliberadamente, entre el padre y sus tres hijos.
KNOWN_PERMISSION_OWNERS = {
    "ACTIVIDADES": frozenset({
        "sits-actividades", "sits-actividades-tabla", "sits-actividades-registrar", "sits-actividades-formularios",
    }),
    "BENEFICIOS": frozenset({"sits-beneficios"}),
    "PRESTAMOS": frozenset({"sits-prestamos"}),
    "SEGUROS": frozenset({"sits-seguros"}),
}
REQUIRED_PARENTS = {
    "sits-trabajo-social": None,
    "sits-actividades": "sits-trabajo-social",
    "sits-oficina": "sits-trabajo-social",
}


class RepairAbort(RuntimeError):
    """Una incompatibilidad detectada antes de cualquier cambio."""


@dataclass(frozen=True)
class RepairPlan:
    missing_modules: tuple[dict[str, object], ...]
    missing_permissions: tuple[str, ...]

    @property
    def has_changes(self) -> bool:
        return bool(self.missing_modules or self.missing_permissions)


@dataclass(frozen=True)
class RepairResult:
    correlation_id: str | None
    created_modules: tuple[str, ...]
    created_permissions: tuple[str, ...]


def _active(row: object) -> bool:
    return bool(getattr(row, "activo", False)) and not bool(getattr(row, "eliminado", True))


def _module_values(definition: dict[str, object]) -> dict[str, object]:
    return {**definition, "activo": True, "eliminado": False, "version": 1}


def _permission_values(module: str) -> dict[str, object]:
    return {
        "id_permiso": f"{ROLE_ADMIN}:{module}", "rol_id": ROLE_ADMIN, "modulo": module,
        **ALL_RIGHTS, "activo": True, "eliminado": False, "version": 1,
    }


def _assert_values(row: object, expected: dict[str, object], label: str) -> None:
    mismatches = [field for field, value in expected.items() if getattr(row, field) != value]
    if mismatches:
        raise RepairAbort(f"{label} existente incompatible: {', '.join(mismatches)}.")


def _validate_prerequisites(session: Session) -> None:
    role = session.get(Role, ROLE_ADMIN)
    if role is None or not _active(role):
        raise RepairAbort("ROLE_ADMIN no existe o no está activo.")

    office_permission = session.get(Permission, f"{ROLE_ADMIN}:OFICINA")
    if office_permission is None:
        raise RepairAbort("Falta el prerrequisito ROLE_ADMIN:OFICINA.")
    _assert_values(office_permission, _permission_values("OFICINA"), "ROLE_ADMIN:OFICINA")

    for parent_id, expected_parent in REQUIRED_PARENTS.items():
        parent = session.get(ModuloSistema, parent_id)
        if parent is None or not _active(parent):
            raise RepairAbort(f"Falta el padre requerido activo {parent_id}.")
        if parent.padre_id_modulo != expected_parent:
            raise RepairAbort(f"Padre requerido incompatible {parent_id}: padre_id_modulo.")


def inspect_repair(session: Session) -> RepairPlan:
    """Valida todo el alcance sin añadir ni modificar filas."""
    _validate_prerequisites(session)

    target_by_id = {row["id_modulo"]: row for row in CATALOG_TARGETS}
    target_routes = {row["ruta"] for row in CATALOG_TARGETS}
    for module in session.scalars(select(ModuloSistema).where(
        ModuloSistema.permiso.in_(PERMISSION_TARGETS),
    )):
        if module.id_modulo not in KNOWN_PERMISSION_OWNERS[module.permiso]:
            raise RepairAbort(
                f"Conflicto de permiso {module.permiso}: módulo no autorizado {module.id_modulo}."
            )

    missing_modules: list[dict[str, object]] = []
    for definition in CATALOG_TARGETS:
        existing = session.get(ModuloSistema, definition["id_modulo"])
        if existing is None:
            route_owner = session.scalar(select(ModuloSistema).where(
                ModuloSistema.ruta == definition["ruta"],
            ))
            if route_owner is not None:
                raise RepairAbort(
                    f"Conflicto de ruta {definition['ruta']}: pertenece a {route_owner.id_modulo}."
                )
            missing_modules.append(definition)
        else:
            _assert_values(existing, _module_values(definition), f"Módulo {definition['id_modulo']}")

    # Una ruta objetivo en otro identificador se detecta incluso si no comparte permiso.
    for module in session.scalars(select(ModuloSistema).where(ModuloSistema.ruta.in_(target_routes))):
        expected = target_by_id.get(module.id_modulo)
        if expected is None or module.ruta != expected["ruta"]:
            raise RepairAbort(f"Conflicto de ruta {module.ruta}: módulo equivalente {module.id_modulo}.")

    rows_by_module: dict[str, Permission] = {}
    for permission in session.scalars(select(Permission).where(
        Permission.rol_id == ROLE_ADMIN,
        Permission.modulo.in_(PERMISSION_TARGETS),
    )):
        expected_id = f"{ROLE_ADMIN}:{permission.modulo}"
        if permission.id_permiso != expected_id:
            raise RepairAbort(f"Conflicto de permiso {permission.modulo}: id_permiso {permission.id_permiso}.")
        rows_by_module[permission.modulo] = permission

    missing_permissions: list[str] = []
    for module in PERMISSION_TARGETS:
        existing_by_id = session.get(Permission, f"{ROLE_ADMIN}:{module}")
        existing = rows_by_module.get(module)
        if existing is not None and existing_by_id is not existing:
            raise RepairAbort(f"Conflicto de id_permiso ROLE_ADMIN:{module}.")
        if existing is None and existing_by_id is not None:
            raise RepairAbort(f"Conflicto de id_permiso ROLE_ADMIN:{module}.")
        if existing is None:
            missing_permissions.append(module)
        else:
            _assert_values(existing, _permission_values(module), f"Permiso ROLE_ADMIN:{module}")

    return RepairPlan(tuple(missing_modules), tuple(missing_permissions))


def apply_repair(session: Session) -> RepairResult:
    """Revalida y aplica catálogo, permisos y auditoría en una sola transacción."""
    with session.begin():
        plan = inspect_repair(session)
        if not plan.has_changes:
            return RepairResult(None, (), ())
        correlation_id = f"{CORRELATION_PREFIX}:{uuid4()}"
        for definition in plan.missing_modules:
            values = _module_values(definition)
            row = ModuloSistema(**values)
            session.add(row)
            session.flush()
            log_change(session, "modulos", row.id_modulo, "CREATE", {}, values,
                       AUDIT_USER, AUDIT_REASON, correlation_id)
        for module in plan.missing_permissions:
            values = _permission_values(module)
            row = Permission(**values)
            session.add(row)
            session.flush()
            log_change(session, "permisos", row.id_permiso, "CREATE", {}, values,
                       AUDIT_USER, AUDIT_REASON, correlation_id)
    return RepairResult(
        correlation_id,
        tuple(row["id_modulo"] for row in plan.missing_modules),
        plan.missing_permissions,
    )


def _created_ids(session: Session, correlation_id: str, table: str) -> set[str]:
    return set(session.scalars(select(Auditoria.id_registro).where(
        Auditoria.correlation_id == correlation_id,
        Auditoria.tabla == table,
        Auditoria.accion == "CREATE",
    )))


def _assert_reversal_dependencies(
    session: Session, module_ids: set[str], permission_ids: set[str], permission_modules: set[str],
) -> None:
    for child in session.scalars(select(ModuloSistema).where(
        ModuloSistema.padre_id_modulo.in_(module_ids),
    )):
        if child.id_modulo not in module_ids:
            raise RepairAbort(f"Reversión bloqueada: módulo hijo posterior {child.id_modulo}.")
    for permission in session.scalars(select(Permission).where(Permission.modulo.in_(permission_modules))):
        if permission.id_permiso not in permission_ids:
            raise RepairAbort(f"Reversión bloqueada: permiso lógico dependiente {permission.id_permiso}.")


def revert_repair(session: Session, correlation_id: str) -> RepairResult:
    """Elimina exclusivamente filas demostrablemente creadas por una ejecución."""
    if not correlation_id.startswith(f"{CORRELATION_PREFIX}:"):
        raise RepairAbort("El identificador no corresponde a esta reparación.")
    with session.begin():
        module_ids = _created_ids(session, correlation_id, "modulos")
        permission_ids = _created_ids(session, correlation_id, "permisos")
        if not module_ids and not permission_ids:
            raise RepairAbort("No hay filas CREATE de esta reparación para revertir.")
        unknown_modules = module_ids - {row["id_modulo"] for row in CATALOG_TARGETS}
        unknown_permissions = permission_ids - {f"{ROLE_ADMIN}:{module}" for module in PERMISSION_TARGETS}
        if unknown_modules or unknown_permissions:
            raise RepairAbort("La auditoría de la ejecución contiene registros fuera del alcance autorizado.")

        modules = {row.id_modulo: row for row in session.scalars(select(ModuloSistema).where(
            ModuloSistema.id_modulo.in_(module_ids),
        ))}
        permissions = {row.id_permiso: row for row in session.scalars(select(Permission).where(
            Permission.id_permiso.in_(permission_ids),
        ))}
        if set(modules) != module_ids or set(permissions) != permission_ids:
            raise RepairAbort("Una fila creada ya no existe; no es segura la reversión.")
        for module_id, row in modules.items():
            definition = next(item for item in CATALOG_TARGETS if item["id_modulo"] == module_id)
            _assert_values(row, _module_values(definition), f"Módulo {module_id}")
        for permission_id, row in permissions.items():
            module = permission_id.removeprefix(f"{ROLE_ADMIN}:")
            _assert_values(row, _permission_values(module), f"Permiso {permission_id}")

        permission_modules = {row.modulo for row in permissions.values()}
        _assert_reversal_dependencies(session, module_ids, permission_ids, permission_modules)
        for row in permissions.values():
            values = _permission_values(row.modulo)
            log_change(session, "permisos", row.id_permiso, "DELETE", values, {},
                       AUDIT_USER, REVERSAL_REASON, correlation_id)
            session.delete(row)
        session.flush()
        for row in modules.values():
            definition = next(item for item in CATALOG_TARGETS if item["id_modulo"] == row.id_modulo)
            log_change(session, "modulos", row.id_modulo, "DELETE", _module_values(definition), {},
                       AUDIT_USER, REVERSAL_REASON, correlation_id)
            session.delete(row)
    return RepairResult(correlation_id, tuple(sorted(module_ids)), tuple(sorted(permission_modules)))
