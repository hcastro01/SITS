"""Trazabilidad por fila y consultas operativas de correos.

Revision ID: 0026_correos_operational_hardening
Revises: 0025_correos_seguimientos
"""
from alembic import op
import sqlalchemy as sa

revision = "0026_correos_operational_hardening"
down_revision = "0025_correos_seguimientos"
branch_labels = None
depends_on = None


def _meta():
    return [sa.Column(name, typ, nullable=nullable) for name, typ, nullable in [
        ("activo", sa.Boolean(create_constraint=True), False), ("eliminado", sa.Boolean(create_constraint=True), False),
        ("fecha_creacion", sa.String(), True), ("creado_por", sa.String(), True), ("fecha_actualizacion", sa.String(), True),
        ("actualizado_por", sa.String(), True), ("fecha_eliminacion", sa.String(), True), ("usuario_eliminacion", sa.String(), True),
        ("motivo_eliminacion", sa.String(), True), ("version", sa.Integer(), False), ("archivo_fuente", sa.String(), True),
        ("hoja_fuente", sa.String(), True), ("registro_fuente", sa.String(), True), ("fecha_importacion", sa.String(), True),
        ("usuario_importacion", sa.String(), True),
    ]]


def upgrade():
    with op.batch_alter_table("lotes_importacion_correo") as batch:
        batch.add_column(sa.Column("filas_procesadas", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("filas_duplicadas", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("filas_omitidas", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("filas_error", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("origen", sa.String(), nullable=False, server_default="XLSX"))
        batch.add_column(sa.Column("duracion_ms", sa.Integer(), nullable=True))
    with op.batch_alter_table("correos") as batch:
        batch.add_column(sa.Column("estado_categoria", sa.String(), nullable=False, server_default="SIN_CATEGORIA"))
    op.create_index("ix_correos_estado_categoria", "correos", ["estado_categoria"])
    op.create_table("errores_importacion_correo", sa.Column("id_error", sa.String(), primary_key=True), sa.Column("lote_id", sa.String(), sa.ForeignKey("lotes_importacion_correo.id_lote"), nullable=False), sa.Column("fila", sa.Integer()), sa.Column("id_externo_correo", sa.String()), sa.Column("codigo", sa.String(), nullable=False), sa.Column("detalle", sa.String(), nullable=False), *_meta(), sa.CheckConstraint("version >= 1", name="version_positive"))
    op.create_index("ix_errores_importacion_correo_lote_id", "errores_importacion_correo", ["lote_id"])
    op.create_index("ix_errores_importacion_correo_lote_fila", "errores_importacion_correo", ["lote_id", "fila"])


def downgrade():
    op.drop_table("errores_importacion_correo")
    op.drop_index("ix_correos_estado_categoria", table_name="correos")
    with op.batch_alter_table("correos") as batch:
        batch.drop_column("estado_categoria")
    with op.batch_alter_table("lotes_importacion_correo") as batch:
        batch.drop_column("duracion_ms")
        batch.drop_column("origen")
        batch.drop_column("filas_error")
        batch.drop_column("filas_omitidas")
        batch.drop_column("filas_duplicadas")
        batch.drop_column("filas_procesadas")
