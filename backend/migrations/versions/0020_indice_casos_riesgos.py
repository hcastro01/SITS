"""Índice para el listado contextual de Riesgos de trabajo.

Revision ID: 0020_indice_casos_riesgos
Revises: 0019_destinos_jerarquicos_formularios
"""

from alembic import op

revision = "0020_indice_casos_riesgos"
down_revision = "0019_destinos_jerarquicos_formularios"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_casos_tipo_estado_fecha_apertura", "casos",
        ["tipo_caso", "estado_caso", "fecha_apertura"],
    )


def downgrade():
    op.drop_index("ix_casos_tipo_estado_fecha_apertura", table_name="casos")
