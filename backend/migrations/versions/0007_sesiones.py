"""Sesiones (Fase 1 §4 línea 105) — nueva tabla, sin equivalente legacy."""
from alembic import op
import sqlalchemy as sa

revision = "0007_sesiones"
down_revision = "0006_formularios"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sesiones",
        sa.Column("id_sesion", sa.String(), primary_key=True),
        sa.Column("token_hash", sa.String(), nullable=False, unique=True),
        sa.Column("id_usuario", sa.String(), sa.ForeignKey("usuarios.id_usuario"), nullable=False),
        sa.Column("fecha_creacion", sa.String(), nullable=False),
        sa.Column("expira_en", sa.String(), nullable=False),
        sa.Column("revocada_en", sa.String(), nullable=True),
    )
    op.create_index("ix_sesiones_id_usuario", "sesiones", ["id_usuario"])


def downgrade():
    op.drop_table("sesiones")
