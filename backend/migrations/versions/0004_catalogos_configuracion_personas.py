"""Catalogos, Configuracion y Personas (Config.gs:50,67,69 — Fase 1 §4)."""
from alembic import op
import sqlalchemy as sa

revision = "0004_catalogos_configuracion_personas"
down_revision = "0003_auditoria"
branch_labels = None
depends_on = None


def _metadatos_comunes():
    return [
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
    ]


def upgrade():
    op.create_table(
        "catalogos",
        sa.Column("id_catalogo", sa.String(), primary_key=True),
        sa.Column("tipo", sa.String(), nullable=False),
        sa.Column("codigo", sa.String(), nullable=False),
        sa.Column("valor", sa.String(), nullable=False),
        sa.Column("descripcion", sa.String(), nullable=True),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("id_catalogo_padre", sa.String(), sa.ForeignKey("catalogos.id_catalogo"), nullable=True),
        sa.Column("tipo_padre", sa.String(), nullable=True),
        sa.Column("codigo_padre", sa.String(), nullable=True),
        sa.Column("es_sensible", sa.Boolean(create_constraint=True), nullable=False),
        *_metadatos_comunes(),
        sa.UniqueConstraint("tipo", "codigo", name="uq_catalogos_tipo"),
        sa.CheckConstraint("version >= 1", name="version_positive"),
    )
    op.create_index("ix_catalogos_id_catalogo_padre", "catalogos", ["id_catalogo_padre"])

    op.create_table(
        "configuracion",
        sa.Column("clave", sa.String(), primary_key=True),
        sa.Column("valor", sa.String(), nullable=True),
        sa.Column("descripcion", sa.String(), nullable=True),
        sa.Column("tipo", sa.String(), nullable=True),
        sa.Column("editable", sa.Boolean(create_constraint=True), nullable=False),
        sa.Column("fecha_actualizacion", sa.String(), nullable=True),
        sa.Column("actualizado_por", sa.String(), nullable=True),
    )

    op.create_table(
        "personas",
        sa.Column("id_persona", sa.String(), primary_key=True),
        sa.Column("codigo_empleado", sa.String(), nullable=True),
        sa.Column("cedula", sa.String(), nullable=True),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("cargo", sa.String(), nullable=True),
        sa.Column("area", sa.String(), nullable=True),
        sa.Column("departamento", sa.String(), nullable=True),
        sa.Column("centro", sa.String(), nullable=True),
        sa.Column("sub_centro", sa.String(), nullable=True),
        sa.Column("turno", sa.String(), nullable=True),
        sa.Column("estado_laboral", sa.String(), nullable=True),
        *_metadatos_comunes(),
        sa.CheckConstraint("version >= 1", name="version_positive"),
    )
    # Sin UNIQUE: MIGRACION_FASE_1.md §4 exige auditar duplicados reales antes de declararlo.
    op.create_index("ix_personas_cedula", "personas", ["cedula"])
    op.create_index("ix_personas_codigo_empleado", "personas", ["codigo_empleado"])


def downgrade():
    op.drop_table("personas")
    op.drop_table("configuracion")
    op.drop_table("catalogos")
