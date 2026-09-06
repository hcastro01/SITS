"""Documentos (Config.gs:66, Fase 1 §4 línea 100) como BLOB comprimido en SQLite —
decisión explícita del usuario en vez de almacenamiento privado en disco."""
from alembic import op
import sqlalchemy as sa

revision = "0008_documentos"
down_revision = "0007_sesiones"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "documentos",
        sa.Column("id_archivo", sa.String(), primary_key=True),
        sa.Column("tipo_registro", sa.String(), nullable=False),
        sa.Column("id_registro", sa.String(), nullable=False),
        sa.Column("nombre_archivo", sa.String(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=False),
        sa.Column("extension", sa.String(), nullable=False),
        sa.Column("tamano_bytes", sa.Integer(), nullable=False),
        sa.Column("tamano_comprimido_bytes", sa.Integer(), nullable=False),
        sa.Column("contenido_comprimido", sa.LargeBinary(), nullable=False),
        sa.Column("sha256", sa.String(), nullable=False),
        sa.Column("categoria_documento", sa.String(), nullable=True),
        sa.Column("sensibilidad", sa.String(), nullable=True),
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
    op.create_index("ix_documentos_tipo_registro", "documentos", ["tipo_registro"])
    op.create_index("ix_documentos_id_registro", "documentos", ["id_registro"])
    op.create_index("ix_documentos_sha256", "documentos", ["sha256"])


def downgrade():
    op.drop_table("documentos")
