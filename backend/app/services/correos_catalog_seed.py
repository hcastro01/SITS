"""Catálogos explícitos para clasificación y estado de correos."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Catalogo

CATEGORIAS_CORREO = (
    ("AUSENTISMO_ASISTENCIA", "Ausentismo y asistencia"),
    ("PERMISOS_VACACIONES_LICENCIAS", "Permisos, vacaciones y licencias"),
    ("ACCIDENTES_RIESGOS_TRABAJO", "Accidentes y riesgos de trabajo"),
    ("SALUD_OCUPACIONAL", "Salud ocupacional"),
    ("NOMINA_PAGOS_DESCUENTOS", "Nómina, pagos y descuentos"),
    ("BENEFICIOS_CREDITOS_SEGUROS", "Beneficios, créditos y seguros"),
    ("CASOS_TALENTO_HUMANO", "Casos de talento humano"),
    ("DISCIPLINA_CUMPLIMIENTO", "Disciplina y cumplimiento"),
    ("MOVILIZACION_TRASLADOS", "Movilización y traslados"),
    ("OPERACION_JORNADA", "Operación, jornada y turnos"),
    ("SEGURIDAD_INDUSTRIAL_CALIDAD", "Seguridad industrial y calidad"),
    ("DOTACION_UNIFORMES", "Dotación, uniformes y equipos"),
    ("COMUNICACION_INTERNA_EVENTOS", "Comunicación interna y eventos"),
    ("REVISION_MANUAL", "Revisión manual"),
)


def seed_email_catalogs(session: Session) -> None:
    existing = set(session.scalars(select(Catalogo.id_catalogo)))
    rows = [("CATEGORIA_CORREO", code, label) for code, label in CATEGORIAS_CORREO]
    rows.extend(("ESTADO_REQUERIMIENTO_CORREO", code, code.replace("_", " ").title()) for code in ("PENDIENTE", "EN_PROCESO", "EN_ESPERA", "RESUELTO", "CERRADO"))
    for order, (kind, code, label) in enumerate(rows, start=1):
        catalog_id = f"CAT-CORREO-{kind}-{code}"
        if catalog_id not in existing:
            session.add(Catalogo(id_catalogo=catalog_id, tipo=kind, codigo=code, valor=label, orden=order, activo=True, eliminado=False, version=1))
