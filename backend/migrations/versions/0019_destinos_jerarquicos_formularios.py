"""Destinos jerárquicos y destino concreto de respuestas de formularios.

Revision ID: 0019_destinos_jerarquicos_formularios
Revises: 0018_accidentes
"""

from alembic import op
import sqlalchemy as sa

revision = "0019_destinos_jerarquicos_formularios"
down_revision = "0018_accidentes"
branch_labels = None
depends_on = None


def _meta():
    return [
        sa.Column("activo", sa.Boolean(create_constraint=True), nullable=False, server_default=sa.true()),
        sa.Column("eliminado", sa.Boolean(create_constraint=True), nullable=False, server_default=sa.false()),
        sa.Column("fecha_creacion", sa.String(), nullable=True),
        sa.Column("creado_por", sa.String(), nullable=True),
        sa.Column("fecha_actualizacion", sa.String(), nullable=True),
        sa.Column("actualizado_por", sa.String(), nullable=True),
        sa.Column("fecha_eliminacion", sa.String(), nullable=True),
        sa.Column("usuario_eliminacion", sa.String(), nullable=True),
        sa.Column("motivo_eliminacion", sa.String(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("archivo_fuente", sa.String(), nullable=True),
        sa.Column("hoja_fuente", sa.String(), nullable=True),
        sa.Column("registro_fuente", sa.String(), nullable=True),
        sa.Column("fecha_importacion", sa.String(), nullable=True),
        sa.Column("usuario_importacion", sa.String(), nullable=True),
    ]


def upgrade():
    op.create_table(
        "destinos_formulario",
        sa.Column("id_destino", sa.String(), primary_key=True),
        sa.Column("codigo", sa.String(), nullable=False),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("nivel", sa.String(), nullable=False),
        sa.Column("padre_id_destino", sa.String(), sa.ForeignKey("destinos_formulario.id_destino"), nullable=True),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        *_meta(),
        sa.UniqueConstraint("codigo"),
        sa.CheckConstraint("nivel IN ('MACROPROCESO', 'PROCESO', 'SUBPROCESO')", name="destino_formulario_nivel"),
        sa.CheckConstraint("version >= 1", name="version_positive"),
    )
    op.create_index("ix_destinos_formulario_padre_id_destino", "destinos_formulario", ["padre_id_destino"])
    op.create_index("ix_destinos_formulario_activo_orden", "destinos_formulario", ["activo", "orden"])
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.execute(sa.text("ALTER TABLE formulario_destinos ADD COLUMN id_destino_catalogo VARCHAR REFERENCES destinos_formulario(id_destino)"))
        op.execute(sa.text("ALTER TABLE envios_formulario ADD COLUMN id_destino_respuesta VARCHAR REFERENCES destinos_formulario(id_destino)"))
    else:
        op.add_column("formulario_destinos", sa.Column("id_destino_catalogo", sa.String(), sa.ForeignKey("destinos_formulario.id_destino"), nullable=True))
        op.add_column("envios_formulario", sa.Column("id_destino_respuesta", sa.String(), sa.ForeignKey("destinos_formulario.id_destino"), nullable=True))
    op.create_index("ix_formulario_destinos_id_destino_catalogo", "formulario_destinos", ["id_destino_catalogo"])
    op.create_index("ux_formulario_destinos_formulario_catalogo", "formulario_destinos", ["id_formulario", "id_destino_catalogo"], unique=True)
    op.create_index("ix_envios_formulario_id_destino_respuesta", "envios_formulario", ["id_destino_respuesta"])


def downgrade():
    op.drop_index("ix_envios_formulario_id_destino_respuesta", table_name="envios_formulario")
    op.drop_index("ux_formulario_destinos_formulario_catalogo", table_name="formulario_destinos")
    op.drop_index("ix_formulario_destinos_id_destino_catalogo", table_name="formulario_destinos")
    op.drop_column("envios_formulario", "id_destino_respuesta")
    op.drop_column("formulario_destinos", "id_destino_catalogo")
    op.drop_index("ix_destinos_formulario_activo_orden", table_name="destinos_formulario")
    op.drop_index("ix_destinos_formulario_padre_id_destino", table_name="destinos_formulario")
    op.drop_table("destinos_formulario")
