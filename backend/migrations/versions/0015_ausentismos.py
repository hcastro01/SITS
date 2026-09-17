"""Ausentismos importables vinculados a Personas."""

from alembic import op
import sqlalchemy as sa

revision = "0015_ausentismos"
down_revision = "0014_actividades"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ausentismos",
        sa.Column("id_ausentismo", sa.String(), primary_key=True),
        sa.Column("persona_id", sa.String(), sa.ForeignKey("personas.id_persona"), nullable=False),
        sa.Column("fecha_inicio", sa.String(), nullable=False),
        sa.Column("fecha_fin", sa.String(), nullable=False),
        sa.Column("tipo_ausentismo", sa.String(), nullable=False),
        sa.Column("motivo", sa.String(), nullable=False),
        sa.Column("observacion", sa.String(), nullable=True),
        sa.Column("activo", sa.Boolean(create_constraint=True), nullable=False),
        sa.Column("eliminado", sa.Boolean(create_constraint=True), nullable=False),
        sa.Column("fecha_creacion", sa.String(), nullable=True),
        sa.Column("creado_por", sa.String(), nullable=True),
        sa.Column("fecha_actualizacion", sa.String(), nullable=True),
        sa.Column("actualizado_por", sa.String(), nullable=True),
        sa.Column("fecha_eliminacion", sa.String(), nullable=True),
        sa.Column("usuario_eliminacion", sa.String(), nullable=True),
        sa.Column("motivo_eliminacion", sa.String(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("archivo_fuente", sa.String(), nullable=True),
        sa.Column("hoja_fuente", sa.String(), nullable=True),
        sa.Column("registro_fuente", sa.String(), nullable=True),
        sa.Column("fecha_importacion", sa.String(), nullable=True),
        sa.Column("usuario_importacion", sa.String(), nullable=True),
        sa.UniqueConstraint("persona_id", "fecha_inicio", "fecha_fin", "tipo_ausentismo", name="uq_ausentismos_persona_fechas_tipo"),
        sa.CheckConstraint("version >= 1", name="version_positive"),
    )


def downgrade() -> None:
    op.drop_table("ausentismos")
