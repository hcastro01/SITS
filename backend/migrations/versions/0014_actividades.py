"""Actividades operativas independientes de Casos."""

from alembic import op
import sqlalchemy as sa

revision = "0014_actividades"
down_revision = "0013_catalogo_modulos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "actividades",
        sa.Column("id_actividad", sa.String(), primary_key=True),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("descripcion", sa.String(), nullable=False),
        sa.Column("responsable_id", sa.String(), sa.ForeignKey("usuarios.id_usuario"), nullable=False),
        sa.Column("tipo_fecha", sa.String(), nullable=False),
        sa.Column("fecha_objetivo", sa.String(), nullable=False),
        sa.Column("estado", sa.String(), nullable=False),
        sa.Column("persona_id", sa.String(), sa.ForeignKey("personas.id_persona"), nullable=True),
        sa.Column("creado_por_id", sa.String(), sa.ForeignKey("usuarios.id_usuario"), nullable=False),
        sa.Column("fecha_finalizacion", sa.String(), nullable=True),
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
        sa.CheckConstraint("version >= 1", name="version_positive"),
    )
    op.create_index("ix_actividades_responsable_id", "actividades", ["responsable_id"])
    op.create_index("ix_actividades_persona_id", "actividades", ["persona_id"])
    op.create_index("ix_actividades_creado_por_id", "actividades", ["creado_por_id"])
    op.create_index("ix_actividades_estado_fecha_objetivo", "actividades", ["estado", "fecha_objetivo"])


def downgrade() -> None:
    op.drop_index("ix_actividades_estado_fecha_objetivo", table_name="actividades")
    op.drop_index("ix_actividades_creado_por_id", table_name="actividades")
    op.drop_index("ix_actividades_persona_id", table_name="actividades")
    op.drop_index("ix_actividades_responsable_id", table_name="actividades")
    op.drop_table("actividades")
