"""Búsqueda multi-entidad con proyección por permisos. Equivalente a
Base Sistema/SearchService.gs, con dos correcciones deliberadas frente al legacy
(MIGRACION_FASE_1.md §6):

1. Sensibilidad por AND, no por OR: SearchService.gs:95,123 concedía visibilidad si el
   usuario tenía `sensitive` en el módulo de la fila O en CASOS. Aquí, para cualquier
   módulo que no sea CASOS, se exigen ambos.
2. Esquemas de salida explícitos en vez de una lista fija de campos a enmascarar
   (Base Sistema/AuthService.gs:75, que se demostró incompleta contra los esquemas reales
   en la auditoría): cada tabla declara qué campos son públicos; todo lo demás se omite
   por completo cuando el registro es sensible y no autorizado, en vez de sustituirse.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, authorize, can
from app.models import (
    Atencion, Caso, Cierre, Compromiso, Derivacion, HallazgoRecorrido, Novedad, Persona,
    Recorrido, Seguimiento,
)
from app.services.sensitivity import is_sensitive_record

PROVENANCE_FIELDS = frozenset(
    {"archivo_fuente", "hoja_fuente", "registro_fuente", "fecha_importacion", "usuario_importacion"}
)
MAX_EXPORT_ROWS = 5000


@dataclass(frozen=True)
class SearchableTable:
    model: type
    tabla: str
    modulo: str
    id_field: str
    campos_texto: tuple[str, ...]
    campo_fecha: str | None
    campos_publicos: tuple[str, ...]


REGISTRY: dict[str, SearchableTable] = {
    "personas": SearchableTable(
        Persona, "personas", "PERSONAS", "id_persona",
        ("codigo_empleado", "cedula", "nombre", "cargo", "area", "departamento", "centro",
         "sub_centro", "turno", "estado_laboral"),
        "fecha_creacion", ("id_persona", "nombre", "area"),
    ),
    "atenciones": SearchableTable(
        Atencion, "atenciones", "ATENCIONES", "id_atencion",
        ("colaborador", "responsable", "tipo_atencion", "motivo", "canal", "gestion",
         "resultado", "observaciones", "estado"),
        "fecha", ("id_atencion", "estado", "fecha"),
    ),
    "casos": SearchableTable(
        Caso, "casos", "CASOS", "id_caso",
        ("codigo_caso", "colaborador", "responsable", "tipo_caso", "subtipo_caso", "prioridad",
         "estado_caso", "tipo_gestion", "tipo_evento", "area", "turno", "resultado"),
        "fecha_apertura", ("id_caso", "codigo_caso", "estado_caso", "prioridad", "fecha_apertura"),
    ),
    "novedades": SearchableTable(
        Novedad, "novedades", "NOVEDADES", "id_novedad",
        ("responsable", "fuente", "tipo", "subtipo", "area", "turno", "lugar", "descripcion",
         "impacto", "prioridad", "accion_inmediata", "estado"),
        "fecha", ("id_novedad", "estado", "fecha"),
    ),
    "recorridos": SearchableTable(
        Recorrido, "recorridos", "RECORRIDOS", "id_recorrido",
        ("responsable", "planta", "area", "turno", "objetivo", "observaciones", "acciones"),
        "fecha", ("id_recorrido", "fecha"),
    ),
    "hallazgos_recorrido": SearchableTable(
        HallazgoRecorrido, "hallazgos_recorrido", "RECORRIDOS", "id_hallazgo",
        ("tipo_hallazgo", "categoria", "subcategoria", "area", "descripcion", "prioridad",
         "accion", "estado"),
        None, ("id_hallazgo", "estado"),
    ),
    "seguimientos": SearchableTable(
        Seguimiento, "seguimientos", "SEGUIMIENTOS", "id_seguimiento",
        ("responsable", "tipo_seguimiento", "canal", "tecnica", "descripcion", "resultado",
         "proxima_accion", "estado"),
        "fecha", ("id_seguimiento", "estado", "fecha"),
    ),
    "derivaciones": SearchableTable(
        Derivacion, "derivaciones", "DERIVACIONES", "id_derivacion",
        ("area_destino", "responsable_destino", "motivo", "estado", "resultado", "observaciones"),
        "fecha", ("id_derivacion", "estado", "fecha"),
    ),
    "compromisos": SearchableTable(
        Compromiso, "compromisos", "COMPROMISOS", "id_compromiso",
        ("responsable", "descripcion", "estado", "evidencia", "observacion"),
        "fecha_limite", ("id_compromiso", "estado", "fecha_limite"),
    ),
    "cierres": SearchableTable(
        Cierre, "cierres", "CASOS", "id_cierre",
        ("responsable", "motivo_cierre", "resultado_final", "evidencia", "observacion"),
        "fecha_cierre_caso", ("id_cierre", "fecha_cierre_caso"),
    ),
}

DEFAULT_TABLES = (
    "casos", "atenciones", "novedades", "recorridos", "seguimientos", "derivaciones", "compromisos",
)


def _puede_ver_sensible(user: AuthenticatedUser, modulo: str, sensible: bool) -> bool:
    if not sensible:
        return True
    if modulo == "CASOS":
        return can(user, "CASOS", "sensitive")
    return can(user, modulo, "sensitive") and can(user, "CASOS", "sensitive")


def _project(registro, model: type, campos_publicos: tuple[str, ...], *, full: bool) -> dict:
    if full:
        return {c.name: getattr(registro, c.name) for c in model.__table__.columns if c.name not in PROVENANCE_FIELDS}
    return {campo: getattr(registro, campo) for campo in campos_publicos}


def search(
    session: Session, user: AuthenticatedUser, *,
    tablas: list[str] | None = None, q: str = "", filtros: dict | None = None,
    incluir_eliminados: bool = False, pagina: int = 1, tamano_pagina: int = 20,
    modo_exportacion: bool = False,
) -> dict:
    authorize(user, "BUSQUEDA", "read")
    filtros = filtros or {}
    tablas = tablas or list(DEFAULT_TABLES)
    desconocidas = set(tablas) - set(REGISTRY)
    if desconocidas:
        raise AppError("INVALID_ENTITY", f"Tablas no reconocidas: {', '.join(sorted(desconocidas))}.", 400)

    q_normalizado = q.strip().lower()
    items = []
    for tabla in tablas:
        config = REGISTRY[tabla]
        if not can(user, config.modulo, "read"):
            continue
        puede_ver_eliminados = incluir_eliminados and (
            can(user, "ADMINISTRACION", "read") or can(user, config.modulo, "delete")
        )
        stmt = select(config.model)
        if not puede_ver_eliminados:
            stmt = stmt.where(config.model.eliminado.is_(False))
        for registro in session.scalars(stmt).all():
            if q_normalizado:
                valores = " ".join(str(getattr(registro, campo) or "") for campo in config.campos_texto).lower()
                if q_normalizado not in valores:
                    continue
            if filtros.get("responsable") and getattr(registro, "responsable", None) != filtros["responsable"]:
                continue
            if filtros.get("area") and getattr(registro, "area", None) != filtros["area"]:
                continue
            sensible = is_sensitive_record(session, registro)
            puede_ver = _puede_ver_sensible(user, config.modulo, sensible)
            items.append({
                "tabla": tabla,
                "id": getattr(registro, config.id_field),
                "fecha": getattr(registro, config.campo_fecha) if config.campo_fecha else None,
                "sensible": sensible,
                "restringido": sensible and not puede_ver,
                "registro": _project(registro, config.model, config.campos_publicos, full=puede_ver),
                "acciones": {
                    "ver": can(user, config.modulo, "read") and puede_ver,
                    "editar": can(user, config.modulo, "edit") and puede_ver,
                    "eliminar": can(user, config.modulo, "delete") and puede_ver,
                    "historial": can(user, config.modulo, "read") and puede_ver,
                },
            })

    items.sort(key=lambda item: item["fecha"] or "", reverse=True)
    total = len(items)

    if modo_exportacion:
        exportados = items[:MAX_EXPORT_ROWS]
        return {"items": exportados, "total": total, "truncado": total > MAX_EXPORT_ROWS}

    inicio = max(0, (pagina - 1) * tamano_pagina)
    pagina_items = items[inicio:inicio + tamano_pagina]
    total_paginas = (total + tamano_pagina - 1) // tamano_pagina if tamano_pagina else 1
    return {"items": pagina_items, "total": total, "pagina": pagina, "tamano_pagina": tamano_pagina,
            "total_paginas": total_paginas}
