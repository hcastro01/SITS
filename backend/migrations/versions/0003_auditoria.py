"""Auditoria transaccional (Base Sistema/Config.gs:68 — 11 columnas, sin bloque META)."""
from alembic import op
import sqlalchemy as sa

revision = "0003_auditoria"
down_revision = "0002_nomenclatura_es"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "auditoria",
        sa.Column("id_auditoria", sa.String(), primary_key=True),
        sa.Column("tabla", sa.String(), nullable=False),
        sa.Column("id_registro", sa.String(), nullable=False),
        sa.Column("accion", sa.String(), nullable=False),
        sa.Column("usuario", sa.String(), nullable=False),
        sa.Column("fecha_hora", sa.String(), nullable=False),
        sa.Column("campo", sa.String(), nullable=False),
        sa.Column("valor_anterior", sa.String(), nullable=True),
        sa.Column("valor_nuevo", sa.String(), nullable=True),
        sa.Column("motivo", sa.String(), nullable=True),
        sa.Column("correlation_id", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_auditoria_tabla_id_registro_fecha_hora", "auditoria",
        ["tabla", "id_registro", "fecha_hora"],
    )


def downgrade():
    op.drop_table("auditoria")
