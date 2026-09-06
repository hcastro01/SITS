"""Añade credencial local segura sin invalidar usuarios existentes.

Revision ID: 0009_password_auth
Revises: 0008_documentos
"""

from alembic import op
import sqlalchemy as sa

revision = "0009_password_auth"
down_revision = "0008_documentos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("usuarios") as batch_op:
        batch_op.add_column(sa.Column("password_hash", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("usuarios") as batch_op:
        batch_op.drop_column("password_hash")
