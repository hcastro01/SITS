"""Catálogo base de módulos para el menú jerárquico de Fase 1."""

from alembic import op
import sqlalchemy as sa

revision = "0013_catalogo_modulos"
down_revision = "0012_integracion_modulos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "modulos",
        sa.Column("id_modulo", sa.String(), primary_key=True),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("permiso", sa.String(), nullable=True),
        sa.Column("ruta", sa.String(), nullable=True),
        sa.Column("icono", sa.String(), nullable=True),
        sa.Column("padre_id_modulo", sa.String(), sa.ForeignKey("modulos.id_modulo"), nullable=True),
        sa.Column("orden", sa.Integer(), nullable=False, default=0),
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
    op.create_index("ix_modulos_permiso", "modulos", ["permiso"])
    op.create_index("ix_modulos_padre_id_modulo", "modulos", ["padre_id_modulo"])


def downgrade() -> None:
    op.drop_index("ix_modulos_padre_id_modulo", table_name="modulos")
    op.drop_index("ix_modulos_permiso", table_name="modulos")
    op.drop_table("modulos")
