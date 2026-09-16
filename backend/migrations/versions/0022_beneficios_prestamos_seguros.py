"""Entidades operativas mínimas de Beneficios, Préstamos y Seguro.

Revision ID: 0022_beneficios_prestamos_seguros
Revises: 0021_contexto_operativo_atenciones
"""

from alembic import op
import sqlalchemy as sa

revision = "0022_beneficios_prestamos_seguros"
down_revision = "0021_contexto_operativo_atenciones"
branch_labels = None
depends_on = None


def _meta():
    return [sa.Column(name, typ, nullable=nullable) for name, typ, nullable in [
        ("activo", sa.Boolean(create_constraint=True), False), ("eliminado", sa.Boolean(create_constraint=True), False),
        ("fecha_creacion", sa.String(), True), ("creado_por", sa.String(), True),
        ("fecha_actualizacion", sa.String(), True), ("actualizado_por", sa.String(), True),
        ("fecha_eliminacion", sa.String(), True), ("usuario_eliminacion", sa.String(), True),
        ("motivo_eliminacion", sa.String(), True), ("version", sa.Integer(), False),
        ("archivo_fuente", sa.String(), True), ("hoja_fuente", sa.String(), True),
        ("registro_fuente", sa.String(), True), ("fecha_importacion", sa.String(), True),
        ("usuario_importacion", sa.String(), True),
    ]]


def upgrade():
    op.create_table("beneficios", sa.Column("id_beneficio", sa.String(), primary_key=True),
        sa.Column("fecha", sa.String(), nullable=True), sa.Column("persona_id", sa.String(), sa.ForeignKey("personas.id_persona"), nullable=True),
        sa.Column("tipo_beneficio", sa.String(), nullable=False), sa.Column("tipo_gestion", sa.String(), nullable=False),
        sa.Column("descripcion", sa.String(), nullable=True), sa.Column("observacion", sa.String(), nullable=True),
        sa.Column("responsable", sa.String(), nullable=True), *_meta(), sa.CheckConstraint("version >= 1", name="version_positive"),
        sa.CheckConstraint("tipo_beneficio IN ('TIA', 'FARMACIA')", name="tipo_beneficio_valido"),
        sa.CheckConstraint("tipo_gestion IN ('ACTIVACION', 'BLOQUEO', 'ANULACION')", name="tipo_gestion_valido"))
    op.create_index("ix_beneficios_persona_id", "beneficios", ["persona_id"])
    op.create_index("ix_beneficios_tipo_fecha", "beneficios", ["tipo_beneficio", "fecha"])
    op.create_table("prestamos", sa.Column("id_prestamo", sa.String(), primary_key=True),
        sa.Column("fecha", sa.String(), nullable=True), sa.Column("persona_id", sa.String(), sa.ForeignKey("personas.id_persona"), nullable=True),
        sa.Column("tipo", sa.String(), nullable=False), sa.Column("descripcion", sa.String(), nullable=True),
        sa.Column("observacion", sa.String(), nullable=True), sa.Column("responsable", sa.String(), nullable=True), *_meta(),
        sa.CheckConstraint("version >= 1", name="version_positive"), sa.CheckConstraint("tipo IN ('PRESTAMO', 'ANTICIPO')", name="tipo_valido"))
    op.create_index("ix_prestamos_persona_id", "prestamos", ["persona_id"])
    op.create_index("ix_prestamos_tipo_fecha", "prestamos", ["tipo", "fecha"])
    op.create_table("seguros", sa.Column("id_seguro", sa.String(), primary_key=True),
        sa.Column("fecha", sa.String(), nullable=True), sa.Column("persona_id", sa.String(), sa.ForeignKey("personas.id_persona"), nullable=True),
        sa.Column("tipo_gestion", sa.String(), nullable=False), sa.Column("descripcion", sa.String(), nullable=True),
        sa.Column("observacion", sa.String(), nullable=True), sa.Column("responsable", sa.String(), nullable=True), *_meta(),
        sa.CheckConstraint("version >= 1", name="version_positive"),
        sa.CheckConstraint("tipo_gestion IN ('AFILIACION', 'ENROLAMIENTO', 'COBERTURA', 'REEMBOLSO', 'PRIMA', 'DEPENDIENTE')", name="tipo_gestion_valido"))
    op.create_index("ix_seguros_persona_id", "seguros", ["persona_id"])
    op.create_index("ix_seguros_tipo_gestion_fecha", "seguros", ["tipo_gestion", "fecha"])


def downgrade():
    op.drop_table("seguros")
    op.drop_table("prestamos")
    op.drop_table("beneficios")
