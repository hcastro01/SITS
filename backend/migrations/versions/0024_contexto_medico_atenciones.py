"""Contexto explícito MEDICO para Atenciones.

NULL queda reservado para registros históricos sin clasificación.

Revision ID: 0024_contexto_medico_atenciones
Revises: 0023_respuesta_documentos
"""
from alembic import op

revision = "0024_contexto_medico_atenciones"
down_revision = "0023_respuesta_documentos"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("atenciones") as batch:
        batch.drop_constraint("contexto_operativo_valido", type_="check")
        batch.create_check_constraint("contexto_operativo_valido", "contexto_operativo IS NULL OR contexto_operativo IN ('MEDICO', 'PRODUCCION', 'OFICINA')")


def downgrade():
    with op.batch_alter_table("atenciones") as batch:
        batch.drop_constraint("contexto_operativo_valido", type_="check")
        batch.create_check_constraint("contexto_operativo_valido", "contexto_operativo IS NULL OR contexto_operativo IN ('PRODUCCION', 'OFICINA')")
