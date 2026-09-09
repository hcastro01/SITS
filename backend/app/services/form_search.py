"""Fuentes allowlist para preguntas de búsqueda/autocompletado."""

import unicodedata

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, authorize
from app.models import Atencion, Caso, Catalogo, Persona

SOURCES = {
    "PERSONAS": {"label": "Personas", "module": "PERSONAS", "search_fields": ["Código", "Cédula", "Nombre"],
                 "mapping_fields": ["codigo_empleado", "cedula", "nombre", "cargo", "area", "departamento", "centro", "sub_centro"]},
    "RESPONSABLES": {"label": "Responsables", "module": "PERSONAS", "search_fields": ["Código", "Cédula", "Nombre"],
                       "mapping_fields": ["codigo_empleado", "cedula", "nombre", "cargo", "area", "departamento", "centro", "sub_centro"]},
    "AREAS": {"label": "Áreas", "module": "PERSONAS", "search_fields": ["Área"],
              "mapping_fields": ["area"]},
    "CENTROS_COSTO": {"label": "Centros de costo", "module": "PERSONAS", "search_fields": ["Centro"],
                       "mapping_fields": ["centro"]},
    "CASOS": {"label": "Casos", "module": "CASOS", "search_fields": ["Código", "Colaborador"],
              "mapping_fields": ["codigo_caso", "colaborador", "responsable", "tipo_caso", "prioridad"]},
    "ATENCIONES": {"label": "Atenciones", "module": "ATENCIONES", "search_fields": ["Colaborador", "Motivo"],
                    "mapping_fields": ["colaborador", "responsable", "tipo_atencion", "motivo", "fecha"]},
    "CATALOGOS": {"label": "Catálogos", "module": "CATALOGOS", "search_fields": ["Código", "Valor"],
                   "mapping_fields": ["codigo", "valor", "descripcion"]},
}

_ACCENT_REPLACEMENTS = (
    ("Á", "A"), ("À", "A"), ("Ä", "A"), ("Â", "A"), ("á", "a"), ("à", "a"), ("ä", "a"), ("â", "a"),
    ("É", "E"), ("È", "E"), ("Ë", "E"), ("Ê", "E"), ("é", "e"), ("è", "e"), ("ë", "e"), ("ê", "e"),
    ("Í", "I"), ("Ì", "I"), ("Ï", "I"), ("Î", "I"), ("í", "i"), ("ì", "i"), ("ï", "i"), ("î", "i"),
    ("Ó", "O"), ("Ò", "O"), ("Ö", "O"), ("Ô", "O"), ("ó", "o"), ("ò", "o"), ("ö", "o"), ("ô", "o"),
    ("Ú", "U"), ("Ù", "U"), ("Ü", "U"), ("Û", "U"), ("ú", "u"), ("ù", "u"), ("ü", "u"), ("û", "u"),
    ("Ñ", "N"), ("ñ", "n"),
)


def _normalize_term(value: str) -> str:
    return "".join(
        character for character in unicodedata.normalize("NFKD", value.strip().casefold())
        if not unicodedata.combining(character)
    )


def _normalized_column(column):
    expression = func.coalesce(column, "")
    for source, replacement in _ACCENT_REPLACEMENTS:
        expression = func.replace(expression, source, replacement)
    return func.lower(expression)


def _matches(term: str, *columns):
    pattern = f"%{_normalize_term(term)}%"
    return or_(*(_normalized_column(column).like(pattern) for column in columns))


def list_sources(user: AuthenticatedUser) -> list[dict]:
    result = []
    for code, config in SOURCES.items():
        try:
            authorize(user, config["module"], "read")
        except AppError:
            continue
        result.append({"codigo": code, **config})
    return result


def search_options(session: Session, user: AuthenticatedUser, source: str, query: str,
                   *, limit: int = 15, catalog_type: str | None = None,
                   browse: bool = False) -> list[dict]:
    code = (source or "").strip().upper()
    config = SOURCES.get(code)
    if config is None:
        raise AppError("INVALID_SEARCH_SOURCE", "Fuente de búsqueda no permitida.", 422)
    authorize(user, config["module"], "read")
    term = (query or "").strip()
    if len(term) < 2 and not browse:
        return []
    capped = max(1, min(limit, 20))
    if code in {"PERSONAS", "RESPONSABLES"}:
        conditions = [Persona.eliminado.is_(False), Persona.activo.is_(True)]
        if term:
            conditions.append(_matches(term, Persona.codigo_empleado, Persona.cedula, Persona.nombre))
        rows = session.scalars(select(Persona).where(*conditions).order_by(Persona.nombre).limit(capped)).all()
        return [{"id": r.id_persona,
                 "label": r.nombre if code == "RESPONSABLES" else " — ".join(v for v in (r.cedula, r.nombre) if v),
                 "data": {field: getattr(r, field) for field in config["mapping_fields"]}} for r in rows]
    if code in {"AREAS", "CENTROS_COSTO"}:
        field_name = "area" if code == "AREAS" else "centro"
        field = getattr(Persona, field_name)
        conditions = [
            Persona.eliminado.is_(False), Persona.activo.is_(True),
            field.is_not(None), func.trim(field) != "",
        ]
        if term:
            conditions.append(_matches(term, field))
        values = session.scalars(
            select(field).where(*conditions).distinct().order_by(field).limit(capped)
        ).all()
        return [{"id": value, "label": value, "data": {field_name: value}} for value in values]
    if code == "CASOS":
        conditions = [Caso.eliminado.is_(False), Caso.activo.is_(True)]
        if term:
            conditions.append(_matches(term, Caso.codigo_caso, Caso.colaborador))
        rows = session.scalars(select(Caso).where(
            *conditions,
        ).order_by(Caso.codigo_caso.desc()).limit(capped)).all()
        return [{"id": r.id_caso, "label": " — ".join(v for v in (r.codigo_caso, r.colaborador) if v),
                 "data": {field: getattr(r, field) for field in config["mapping_fields"]}} for r in rows]
    if code == "ATENCIONES":
        conditions = [Atencion.eliminado.is_(False), Atencion.activo.is_(True)]
        if term:
            conditions.append(_matches(term, Atencion.colaborador, Atencion.motivo))
        rows = session.scalars(select(Atencion).where(
            *conditions,
        ).order_by(Atencion.fecha.desc()).limit(capped)).all()
        return [{"id": r.id_atencion, "label": " — ".join(v for v in (r.colaborador, r.motivo, r.fecha) if v),
                 "data": {field: getattr(r, field) for field in config["mapping_fields"]}} for r in rows]
    conditions = [Catalogo.eliminado.is_(False), Catalogo.activo.is_(True)]
    if term:
        conditions.append(_matches(term, Catalogo.codigo, Catalogo.valor))
    stmt = select(Catalogo).where(*conditions)
    if catalog_type:
        stmt = stmt.where(Catalogo.tipo == catalog_type.strip().upper())
    rows = session.scalars(stmt.order_by(Catalogo.orden, Catalogo.valor).limit(capped)).all()
    return [{"id": r.id_catalogo, "label": f"{r.codigo} — {r.valor}",
             "data": {field: getattr(r, field) for field in config["mapping_fields"]}} for r in rows]
