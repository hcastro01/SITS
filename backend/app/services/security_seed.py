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
# Descripciones verbatim de Base Sistema/Setup.gs:101-105.
ROLE_DESCRIPTIONS = {
    "ROLE_ADMIN": "Acceso integral y administracion de seguridad.",
    "ROLE_COORDINADOR": "Supervision consolidada de procesos.",
    "ROLE_TRABAJADOR_SOCIAL": "Captura y gestion operativa autorizada.",
    "ROLE_CONSULTA": "Consulta sin modificacion segun permisos.",
    "ROLE_GERENCIA": "Indicadores y consulta agregada sin detalle sensible.",
}
OPERATIONAL = {"ATENCIONES", "CASOS", "NOVEDADES", "RECORRIDOS", "SEGUIMIENTOS", "DERIVACIONES", "COMPROMISOS"}
BASE_READ = OPERATIONAL | {"DASHBOARD", "PERSONAS", "FORMULARIOS", "RESPUESTAS", "CATALOGOS", "DOCUMENTOS", "BUSQUEDA", "REPORTES"}

# Mapea la acción RPC (AuthService.gs:2, ACTION_COLUMNS) a la columna en español.
ACTION_TO_FIELD = {
    "create": "puede_crear",
    "read": "puede_leer",
    "edit": "puede_editar",
    "delete": "puede_eliminar",
    "sensitive": "puede_sensible",
    "export": "puede_exportar",
}


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
    for id_rol, nombre in ROLES.items():
        if session.get(Role, id_rol) is None:
            session.add(Role(id_rol=id_rol, nombre=nombre, descripcion=ROLE_DESCRIPTIONS[id_rol]))
    session.flush()
    existing = set(session.execute(select(Permission.rol_id, Permission.modulo)).all())
    for id_rol in ROLES:
        for modulo in MODULES:
            if (id_rol, modulo) not in existing:
                session.add(Permission(
                    id_permiso=f"{id_rol}:{modulo}", rol_id=id_rol, modulo=modulo,
                    **{ACTION_TO_FIELD[action]: value for action, value in initial_rights(id_rol, modulo).items()},
                ))
