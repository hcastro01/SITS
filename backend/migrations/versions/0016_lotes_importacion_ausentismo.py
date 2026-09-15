"""Lotes e incidencias persistentes de importación de ausentismos."""

from alembic import op
import sqlalchemy as sa

revision = "0016_lotes_importacion_ausentismo"
down_revision = "0015_ausentismos"
branch_labels = None
depends_on = None


def _metadata_columns():
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


def upgrade() -> None:
    op.create_table(
        "lotes_importacion_ausentismo",
        sa.Column("id_lote", sa.String(), primary_key=True),
        sa.Column("nombre_archivo", sa.String(), nullable=False),
        sa.Column("contenido_archivo", sa.LargeBinary(), nullable=False),
        sa.Column("usuario_id", sa.String(), sa.ForeignKey("usuarios.id_usuario"), nullable=False),
        sa.Column("estado", sa.String(), nullable=False),
        sa.Column("total_filas", sa.Integer(), nullable=False),
        sa.Column("filas_validas", sa.Integer(), nullable=False),
        sa.Column("filas_con_error", sa.Integer(), nullable=False),
        sa.Column("filas_duplicadas", sa.Integer(), nullable=False),
        sa.Column("filas_importadas", sa.Integer(), nullable=False),
        *_metadata_columns(),
        sa.CheckConstraint("version >= 1", name="version_positive"),
    )
    op.create_index("ix_lotes_importacion_ausentismo_usuario_id", "lotes_importacion_ausentismo", ["usuario_id"])
    op.create_table(
        "errores_importacion_ausentismo",
        sa.Column("id_error", sa.String(), primary_key=True),
        sa.Column("lote_id", sa.String(), sa.ForeignKey("lotes_importacion_ausentismo.id_lote"), nullable=False),
        sa.Column("numero_fila", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(), nullable=False),
        sa.Column("mensaje", sa.String(), nullable=False),
        sa.Column("datos_fila", sa.String(), nullable=True),
        *_metadata_columns(),
        sa.CheckConstraint("version >= 1", name="version_positive"),
    )
    op.create_index("ix_errores_importacion_ausentismo_lote_id", "errores_importacion_ausentismo", ["lote_id"])
    op.create_index("ix_errores_importacion_ausentismo_lote_fila", "errores_importacion_ausentismo", ["lote_id", "numero_fila"])


def downgrade() -> None:
    op.drop_table("errores_importacion_ausentismo")
    op.drop_table("lotes_importacion_ausentismo")
