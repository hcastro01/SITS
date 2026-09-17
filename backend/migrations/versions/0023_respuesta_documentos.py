"""Adjuntos repetibles por detalle de respuesta de formulario.

Revision ID: 0023_respuesta_documentos
Revises: 0022_beneficios_prestamos_seguros
"""
from alembic import op
import sqlalchemy as sa

revision = "0023_respuesta_documentos"
down_revision = "0022_beneficios_prestamos_seguros"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "respuesta_documentos",
        sa.Column("id_respuesta_documento", sa.String(), primary_key=True),
        sa.Column("id_detalle_respuesta", sa.String(), sa.ForeignKey("respuestas_formulario.id_detalle_respuesta"), nullable=False),
        sa.Column("id_archivo", sa.String(), sa.ForeignKey("documentos.id_archivo"), nullable=False),
        sa.UniqueConstraint("id_detalle_respuesta", "id_archivo"),
    )
    op.create_index("ix_respuesta_documentos_detalle", "respuesta_documentos", ["id_detalle_respuesta"])
    op.create_index("ix_respuesta_documentos_archivo", "respuesta_documentos", ["id_archivo"])


def downgrade():
    op.drop_table("respuesta_documentos")
