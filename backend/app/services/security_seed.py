"""Matriz inicial portada de Setup.gs; no sustituye los permisos de producción."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Permission, Role

MODULES = (
    "DASHBOARD", "ATENCIONES", "CASOS", "NOVEDADES", "RECORRIDOS", "SEGUIMIENTOS",
    "DERIVACIONES", "COMPROMISOS", "PERSONAS", "FORMULARIOS", "RESPUESTAS", "CATALOGOS",
    "DOCUMENTOS", "BUSQUEDA", "REPORTES", "IMPORTACION", "AUDITORIA", "ADMINISTRACION",
)
ROLES = {
    "ROLE_ADMIN": "Administrador",
    "ROLE_COORDINADOR": "Coordinador / Relaciones Laborales",
    "ROLE_TRABAJADOR_SOCIAL": "Trabajador Social",
    "ROLE_CONSULTA": "Consulta",
    "ROLE_GERENCIA": "Gerencia",
}
OPERATIONAL = {"ATENCIONES", "CASOS", "NOVEDADES", "RECORRIDOS", "SEGUIMIENTOS", "DERIVACIONES", "COMPROMISOS"}
BASE_READ = OPERATIONAL | {"DASHBOARD", "PERSONAS", "FORMULARIOS", "RESPUESTAS", "CATALOGOS", "DOCUMENTOS", "BUSQUEDA", "REPORTES"}


def initial_rights(role: str, module: str) -> dict[str, bool]:
    rights = dict.fromkeys(("create", "read", "edit", "delete", "sensitive", "export"), False)
    if role == "ROLE_ADMIN":
        return dict.fromkeys(rights, True)
    if role == "ROLE_COORDINADOR":
        rights.update(create=module in OPERATIONAL | {"RESPUESTAS", "DOCUMENTOS"},
                      read=module in BASE_READ | {"AUDITORIA"},
                      edit=module in OPERATIONAL | {"DOCUMENTOS"},
                      export=module in {"REPORTES", "BUSQUEDA"})
    elif role == "ROLE_TRABAJADOR_SOCIAL":
        rights.update(create=module in OPERATIONAL | {"PERSONAS", "RESPUESTAS", "DOCUMENTOS"},
                      read=module in BASE_READ,
                      edit=module in OPERATIONAL | {"PERSONAS", "RESPUESTAS", "DOCUMENTOS"},
                      export=module == "REPORTES")
    elif role == "ROLE_CONSULTA":
        rights["read"] = module in BASE_READ - {"RESPUESTAS", "REPORTES"}
    elif role == "ROLE_GERENCIA":
        rights.update(read=module in OPERATIONAL | {"DASHBOARD", "BUSQUEDA", "REPORTES", "CATALOGOS"},
                      export=module == "REPORTES")
    return rights


def seed_security(session: Session) -> None:
    # Solo inserta faltantes. Nunca crea usuarios ni eleva permisos existentes.
    for role_id, name in ROLES.items():
        if session.get(Role, role_id) is None:
            session.add(Role(id=role_id, name=name))
    session.flush()
    existing = set(session.execute(select(Permission.role_id, Permission.module)).all())
    for role_id in ROLES:
        for module in MODULES:
            if (role_id, module) not in existing:
                session.add(Permission(id=f"{role_id}:{module}", role_id=role_id, module=module,
                                       **{f"can_{action}": value for action, value in initial_rights(role_id, module).items()}))

