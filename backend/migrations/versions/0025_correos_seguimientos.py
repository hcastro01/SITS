"""Correos importados, sus seguimientos y lotes XLSX de revisión previa.

Revision ID: 0025_correos_seguimientos
Revises: 0024_contexto_medico_atenciones
"""
from alembic import op
import sqlalchemy as sa

revision = "0025_correos_seguimientos"
down_revision = "0024_contexto_medico_atenciones"
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
    op.create_table("lotes_importacion_correo", sa.Column("id_lote", sa.String(), primary_key=True), sa.Column("nombre_archivo", sa.String(), nullable=False), sa.Column("contenido_archivo", sa.LargeBinary(), nullable=False), sa.Column("usuario_id", sa.String(), sa.ForeignKey("usuarios.id_usuario"), nullable=False), sa.Column("estado", sa.String(), nullable=False), sa.Column("total_filas", sa.Integer(), nullable=False), sa.Column("filas_clasificadas", sa.Integer(), nullable=False), sa.Column("filas_revision", sa.Integer(), nullable=False), sa.Column("filas_importadas", sa.Integer(), nullable=False), *_meta(), sa.CheckConstraint("version >= 1", name="version_positive"))
    op.create_index("ix_lotes_importacion_correo_usuario_id", "lotes_importacion_correo", ["usuario_id"])
    op.create_table("correos", sa.Column("id_correo", sa.String(), primary_key=True), sa.Column("id_externo_correo", sa.String(), nullable=False), sa.Column("idempotency_key", sa.String(), nullable=False), sa.Column("asunto", sa.String(), nullable=False), sa.Column("remitente", sa.String()), sa.Column("destinatarios", sa.Text()), sa.Column("cc", sa.Text()), sa.Column("fecha_recibido", sa.String()), sa.Column("importancia", sa.String()), sa.Column("cuerpo", sa.Text()), sa.Column("tiene_adjuntos", sa.Boolean(create_constraint=True), nullable=False), sa.Column("leido", sa.Boolean(create_constraint=True), nullable=False), sa.Column("categoria_macro", sa.String()), sa.Column("categoria_nombre", sa.String()), sa.Column("regla_disparadora", sa.String()), sa.Column("estado_clasificacion", sa.String(), nullable=False), sa.Column("estado_requerimiento", sa.String(), nullable=False), sa.Column("responsable_seguimiento", sa.String()), sa.Column("lote_id", sa.String(), sa.ForeignKey("lotes_importacion_correo.id_lote")), *_meta(), sa.UniqueConstraint("id_externo_correo", name="uq_correos_id_externo"), sa.UniqueConstraint("idempotency_key", name="uq_correos_idempotency"), sa.CheckConstraint("estado_clasificacion IN ('CLASIFICADO', 'REVISION')", name="estado_clasificacion_valido"), sa.CheckConstraint("estado_requerimiento IN ('PENDIENTE', 'EN_PROCESO', 'EN_ESPERA', 'RESUELTO', 'CERRADO')", name="estado_requerimiento_valido"), sa.CheckConstraint("version >= 1", name="version_positive"))
    op.create_index("ix_correos_fecha_recibido", "correos", ["fecha_recibido"])
    op.create_index("ix_correos_estado_requerimiento", "correos", ["estado_requerimiento"])
    op.create_index("ix_correos_categoria_macro", "correos", ["categoria_macro"])
    op.create_table("seguimientos_correo", sa.Column("id_seguimiento", sa.String(), primary_key=True), sa.Column("correo_id", sa.String(), sa.ForeignKey("correos.id_correo"), nullable=False), sa.Column("fecha_seguimiento", sa.String()), sa.Column("detalle_seguimiento", sa.Text(), nullable=False), sa.Column("seguimiento_por", sa.String()), sa.Column("estado_requerimiento", sa.String(), nullable=False), *_meta(), sa.CheckConstraint("estado_requerimiento IN ('PENDIENTE', 'EN_PROCESO', 'EN_ESPERA', 'RESUELTO', 'CERRADO')", name="estado_requerimiento_valido"), sa.CheckConstraint("version >= 1", name="version_positive"))
    op.create_index("ix_seguimientos_correo_correo_id", "seguimientos_correo", ["correo_id"])


def downgrade():
    op.drop_table("seguimientos_correo")
    op.drop_table("correos")
    op.drop_table("lotes_importacion_correo")
