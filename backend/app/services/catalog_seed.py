"""Catálogos técnicos. Equivalente a Base Sistema/Setup.gs:143-156 (seedTechnicalCatalogs_).

NIVEL_SENSIBILIDAD no se siembra aquí: Base Sistema nunca definió sus valores (ni en código
ni en documentación) — es el hallazgo H2 de la auditoría. Sembrar códigos ahora sería
inventar una categorización de negocio; queda pendiente de que el usuario los provea.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Catalogo

# (id_catalogo, tipo, codigo, valor, orden) — verbatim de Setup.gs:144-152.
TECHNICAL_CATALOGS = [
    ("CAT-ESTFORM-BORRADOR", "ESTADO_FORMULARIO", "BORRADOR", "Borrador", 10),
    ("CAT-ESTFORM-PUBLICADO", "ESTADO_FORMULARIO", "PUBLICADO", "Publicado", 20),
    ("CAT-ESTFORM-INACTIVO", "ESTADO_FORMULARIO", "INACTIVO", "Inactivo", 30),
    ("CAT-ESTCASO-BORRADOR", "ESTADO_CASO", "BORRADOR", "Borrador", 10),
    ("CAT-ESTCASO-REGISTRADO", "ESTADO_CASO", "REGISTRADO", "Registrado", 20),
    ("CAT-ESTCASO-GESTION", "ESTADO_CASO", "EN_GESTION", "En Gestion", 30),
    ("CAT-ESTCASO-CERRADO", "ESTADO_CASO", "CERRADO", "Cerrado", 40),
]


def seed_technical_catalogs(session: Session) -> None:
    # Solo inserta faltantes, igual que seed_security (Setup.gs es idempotente por findById).
    existing = set(session.scalars(select(Catalogo.id_catalogo)))
    for id_catalogo, tipo, codigo, valor, orden in TECHNICAL_CATALOGS:
        if id_catalogo not in existing:
            session.add(Catalogo(id_catalogo=id_catalogo, tipo=tipo, codigo=codigo, valor=valor, orden=orden))
