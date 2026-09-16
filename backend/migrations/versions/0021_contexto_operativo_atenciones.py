"""Contexto explícito y opcional para Atenciones.

Revision ID: 0021_contexto_operativo_atenciones
Revises: 0020_indice_casos_riesgos
"""

from alembic import op
import sqlalchemy as sa

revision = "0021_contexto_operativo_atenciones"
down_revision = "0020_indice_casos_riesgos"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("atenciones", sa.Column("contexto_operativo", sa.String(),
                  sa.CheckConstraint("contexto_operativo IS NULL OR contexto_operativo IN ('PRODUCCION', 'OFICINA')", name="contexto_operativo_valido"), nullable=True))
    op.create_index("ix_atenciones_contexto_fecha", "atenciones", ["contexto_operativo", "fecha"])


def downgrade():
    op.drop_index("ix_atenciones_contexto_fecha", table_name="atenciones")
    op.drop_column("atenciones", "contexto_operativo")
