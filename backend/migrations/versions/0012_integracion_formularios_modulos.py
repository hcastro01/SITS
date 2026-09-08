"""Relaciones estructuradas para integrar formularios con módulos y Personas.

Revision ID: 0012_integracion_modulos
Revises: 0011_codigos_respuesta
"""

from alembic import op
import sqlalchemy as sa

revision = "0012_integracion_modulos"
down_revision = "0011_codigos_respuesta"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.execute(sa.text("ALTER TABLE novedades ADD COLUMN id_persona VARCHAR REFERENCES personas(id_persona)"))
        op.execute(sa.text("ALTER TABLE recorridos ADD COLUMN id_persona VARCHAR REFERENCES personas(id_persona)"))
    else:
        op.add_column("novedades", sa.Column("id_persona", sa.String(), sa.ForeignKey("personas.id_persona"), nullable=True))
        op.add_column("recorridos", sa.Column("id_persona", sa.String(), sa.ForeignKey("personas.id_persona"), nullable=True))
    op.create_index("ix_novedades_id_persona", "novedades", ["id_persona"])
    op.create_index("ix_recorridos_id_persona", "recorridos", ["id_persona"])
    op.add_column("envios_formulario", sa.Column(
        "contexto_creado_dinamicamente", sa.Boolean(), nullable=False, server_default=sa.false(),
    ))


def downgrade() -> None:
    op.drop_column("envios_formulario", "contexto_creado_dinamicamente")
    op.drop_index("ix_recorridos_id_persona", table_name="recorridos")
    op.drop_index("ix_novedades_id_persona", table_name="novedades")
    op.drop_column("recorridos", "id_persona")
    op.drop_column("novedades", "id_persona")
