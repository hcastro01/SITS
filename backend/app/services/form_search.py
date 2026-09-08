"""Fuentes allowlist para preguntas de búsqueda/autocompletado."""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, authorize
from app.models import Atencion, Caso, Catalogo, Persona

SOURCES = {
    "PERSONAS": {"label": "Personas", "module": "PERSONAS", "search_fields": ["Cédula", "Nombre"],
                 "mapping_fields": ["cedula", "nombre", "cargo", "area", "departamento", "centro", "sub_centro"]},
    "CASOS": {"label": "Casos", "module": "CASOS", "search_fields": ["Código", "Colaborador"],
              "mapping_fields": ["codigo_caso", "colaborador", "responsable", "tipo_caso", "prioridad"]},
    "ATENCIONES": {"label": "Atenciones", "module": "ATENCIONES", "search_fields": ["Colaborador", "Motivo"],
                    "mapping_fields": ["colaborador", "responsable", "tipo_atencion", "motivo", "fecha"]},
    "CATALOGOS": {"label": "Catálogos", "module": "CATALOGOS", "search_fields": ["Código", "Valor"],
                   "mapping_fields": ["codigo", "valor", "descripcion"]},
}


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
                   *, limit: int = 15, catalog_type: str | None = None) -> list[dict]:
    code = (source or "").strip().upper()
    config = SOURCES.get(code)
    if config is None:
        raise AppError("INVALID_SEARCH_SOURCE", "Fuente de búsqueda no permitida.", 422)
    authorize(user, config["module"], "read")
    term = (query or "").strip()
    if len(term) < 2:
        return []
    pattern = f"%{term}%"
    capped = max(1, min(limit, 20))
    if code == "PERSONAS":
        rows = session.scalars(select(Persona).where(
            Persona.eliminado.is_(False), Persona.activo.is_(True),
            or_(Persona.cedula.ilike(pattern), Persona.nombre.ilike(pattern)),
        ).order_by(Persona.nombre).limit(capped)).all()
        return [{"id": r.id_persona, "label": " — ".join(v for v in (r.cedula, r.nombre) if v),
                 "data": {field: getattr(r, field) for field in config["mapping_fields"]}} for r in rows]
    if code == "CASOS":
        rows = session.scalars(select(Caso).where(
            Caso.eliminado.is_(False), Caso.activo.is_(True),
            or_(Caso.codigo_caso.ilike(pattern), Caso.colaborador.ilike(pattern)),
        ).order_by(Caso.codigo_caso.desc()).limit(capped)).all()
        return [{"id": r.id_caso, "label": " — ".join(v for v in (r.codigo_caso, r.colaborador) if v),
                 "data": {field: getattr(r, field) for field in config["mapping_fields"]}} for r in rows]
    if code == "ATENCIONES":
        rows = session.scalars(select(Atencion).where(
            Atencion.eliminado.is_(False), Atencion.activo.is_(True),
            or_(Atencion.colaborador.ilike(pattern), Atencion.motivo.ilike(pattern)),
        ).order_by(Atencion.fecha.desc()).limit(capped)).all()
        return [{"id": r.id_atencion, "label": " — ".join(v for v in (r.colaborador, r.motivo, r.fecha) if v),
                 "data": {field: getattr(r, field) for field in config["mapping_fields"]}} for r in rows]
    stmt = select(Catalogo).where(Catalogo.eliminado.is_(False), Catalogo.activo.is_(True),
        or_(Catalogo.codigo.ilike(pattern), Catalogo.valor.ilike(pattern)))
    if catalog_type:
        stmt = stmt.where(Catalogo.tipo == catalog_type.strip().upper())
    rows = session.scalars(stmt.order_by(Catalogo.orden, Catalogo.valor).limit(capped)).all()
    return [{"id": r.id_catalogo, "label": f"{r.codigo} — {r.valor}",
             "data": {field: getattr(r, field) for field in config["mapping_fields"]}} for r in rows]
