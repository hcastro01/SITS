"""Matriz inicial portada de Setup.gs; no sustituye los permisos de producción."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ModuloSistema, Permission, Role

MODULES = (
    "DASHBOARD", "ATENCIONES", "CASOS", "NOVEDADES", "RECORRIDOS", "SEGUIMIENTOS",
    "DERIVACIONES", "COMPROMISOS", "PERSONAS", "FORMULARIOS", "RESPUESTAS", "CATALOGOS",
    "DOCUMENTOS", "BUSQUEDA", "REPORTES", "IMPORTACION", "AUDITORIA", "ADMINISTRACION",
    "ACTIVIDADES", "RIESGOS_TRABAJO", "PRODUCCION", "OFICINA", "AUSENTISMO", "ACCIDENTES", "BENEFICIOS", "PRESTAMOS", "SEGUROS", "CORREOS",
)

MODULOS_ARQUITECTURA = (
    {"id_modulo": "sits-trabajo-social", "nombre": "Trabajo Social", "permiso": None, "ruta": None,
     "icono": "⌂", "padre_id_modulo": None, "orden": 10},
    {"id_modulo": "sits-inicio", "nombre": "Inicio", "permiso": "DASHBOARD", "ruta": "/trabajo-social/inicio",
     "icono": "⌂", "padre_id_modulo": "sits-trabajo-social", "orden": 11},
    {"id_modulo": "sits-actividades", "nombre": "Actividades", "permiso": "ACTIVIDADES", "ruta": None,
     "icono": "✓", "padre_id_modulo": "sits-trabajo-social", "orden": 20},
    {"id_modulo": "sits-actividades-tabla", "nombre": "Tabla de actividades", "permiso": "ACTIVIDADES", "ruta": "/trabajo-social/actividades",
     "icono": "☷", "padre_id_modulo": "sits-actividades", "orden": 21},
    {"id_modulo": "sits-actividades-registrar", "nombre": "Registrar actividad", "permiso": "ACTIVIDADES", "ruta": "/trabajo-social/actividades/registrar",
     "icono": "+", "padre_id_modulo": "sits-actividades", "orden": 22},
    {"id_modulo": "sits-actividades-formularios", "nombre": "Formularios", "permiso": "FORMULARIOS", "ruta": "/trabajo-social/actividades/formularios",
     "icono": "▤", "padre_id_modulo": "sits-actividades", "orden": 23},
    {"id_modulo": "sits-correos", "nombre": "Correos y seguimiento", "permiso": "CORREOS", "ruta": "/trabajo-social/correos",
     "icono": "✉", "padre_id_modulo": "sits-trabajo-social", "orden": 25},
    {"id_modulo": "sits-medico", "nombre": "Departamento Médico", "permiso": None, "ruta": None,
     "icono": "✚", "padre_id_modulo": "sits-trabajo-social", "orden": 30},
    {"id_modulo": "sits-riesgos", "nombre": "Riesgos de trabajo", "permiso": "RIESGOS_TRABAJO", "ruta": "/trabajo-social/departamento-medico/riesgos",
     "icono": "!", "padre_id_modulo": "sits-medico", "orden": 31},
    {"id_modulo": "sits-ausentismos", "nombre": "Ausentismos", "permiso": "AUSENTISMO", "ruta": "/trabajo-social/departamento-medico/ausentismos",
     "icono": "◷", "padre_id_modulo": "sits-medico", "orden": 32},
    {"id_modulo": "sits-accidentes", "nombre": "Accidentes", "permiso": "ACCIDENTES", "ruta": "/trabajo-social/departamento-medico/accidentes",
     "icono": "⚠", "padre_id_modulo": "sits-medico", "orden": 33},
    {"id_modulo": "sits-medico-formularios", "nombre": "Formularios", "permiso": "FORMULARIOS", "ruta": "/trabajo-social/departamento-medico/formularios",
     "icono": "▤", "padre_id_modulo": "sits-medico", "orden": 34},
    {"id_modulo": "sits-produccion", "nombre": "Producción", "permiso": None, "ruta": None,
     "icono": "◫", "padre_id_modulo": "sits-trabajo-social", "orden": 40},
    {"id_modulo": "sits-produccion-atenciones", "nombre": "Atenciones", "permiso": "ATENCIONES", "ruta": "/trabajo-social/produccion/atenciones",
     "icono": "+", "padre_id_modulo": "sits-produccion", "orden": 41},
    {"id_modulo": "sits-produccion-recorridos", "nombre": "Recorridos", "permiso": "RECORRIDOS", "ruta": "/trabajo-social/produccion/recorridos",
     "icono": "↗", "padre_id_modulo": "sits-produccion", "orden": 42},
    {"id_modulo": "sits-produccion-novedades", "nombre": "Novedades de planta", "permiso": "NOVEDADES", "ruta": "/trabajo-social/produccion/novedades",
     "icono": "!", "padre_id_modulo": "sits-produccion", "orden": 43},
    {"id_modulo": "sits-produccion-formularios", "nombre": "Formularios", "permiso": "FORMULARIOS", "ruta": "/trabajo-social/produccion/formularios",
     "icono": "▤", "padre_id_modulo": "sits-produccion", "orden": 44},
    {"id_modulo": "sits-oficina", "nombre": "Oficina", "permiso": None, "ruta": None,
     "icono": "▣", "padre_id_modulo": "sits-trabajo-social", "orden": 50},
    {"id_modulo": "sits-beneficios", "nombre": "Beneficios", "permiso": "BENEFICIOS", "ruta": "/trabajo-social/oficina/beneficios",
     "icono": "★", "padre_id_modulo": "sits-oficina", "orden": 51},
    {"id_modulo": "sits-oficina-atenciones", "nombre": "Atenciones", "permiso": "ATENCIONES", "ruta": "/trabajo-social/oficina/atenciones",
     "icono": "+", "padre_id_modulo": "sits-oficina", "orden": 52},
    {"id_modulo": "sits-prestamos", "nombre": "Préstamos", "permiso": "PRESTAMOS", "ruta": "/trabajo-social/oficina/prestamos",
     "icono": "$", "padre_id_modulo": "sits-oficina", "orden": 53},
    {"id_modulo": "sits-seguros", "nombre": "Seguro", "permiso": "SEGUROS", "ruta": "/trabajo-social/oficina/seguro",
     "icono": "◈", "padre_id_modulo": "sits-oficina", "orden": 54},
    {"id_modulo": "sits-oficina-formularios", "nombre": "Formularios", "permiso": "FORMULARIOS", "ruta": "/trabajo-social/oficina/formularios",
     "icono": "▤", "padre_id_modulo": "sits-oficina", "orden": 55},
    {"id_modulo": "sits-repositorio-formularios", "nombre": "Repositorio de formularios", "permiso": "FORMULARIOS", "ruta": "/formularios",
     "icono": "▤", "padre_id_modulo": None, "orden": 60},
    {"id_modulo": "sits-administracion", "nombre": "Administración", "permiso": "ADMINISTRACION", "ruta": None,
     "icono": "⚙", "padre_id_modulo": None, "orden": 70},
    {"id_modulo": "sits-admin-usuarios", "nombre": "Usuarios", "permiso": "ADMINISTRACION", "ruta": "/admin/usuarios",
     "icono": "♙", "padre_id_modulo": "sits-administracion", "orden": 71},
    {"id_modulo": "sits-admin-permisos", "nombre": "Roles y permisos", "permiso": "ADMINISTRACION", "ruta": "/admin/permisos",
     "icono": "⚙", "padre_id_modulo": "sits-administracion", "orden": 72},
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
OPERATIONAL = {"ATENCIONES", "CASOS", "NOVEDADES", "RECORRIDOS", "SEGUIMIENTOS", "DERIVACIONES", "COMPROMISOS", "RIESGOS_TRABAJO", "PRODUCCION", "CORREOS"}
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


def seed_module_catalog(session: Session) -> None:
    existing = set(session.scalars(select(ModuloSistema.id_modulo)))
    for row in MODULOS_ARQUITECTURA:
        if row["id_modulo"] in existing:
            continue
        session.add(ModuloSistema(
            id_modulo=row["id_modulo"], nombre=row["nombre"], permiso=row["permiso"],
            ruta=row["ruta"], icono=row["icono"], padre_id_modulo=row["padre_id_modulo"],
            orden=row["orden"], activo=True, eliminado=False, version=1,
        ))
