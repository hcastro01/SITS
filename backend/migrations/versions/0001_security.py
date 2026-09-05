"""Base de roles y usuarios. No crea cuentas ni habilita acceso público."""
from alembic import op
import sqlalchemy as sa

revision = "0001_security"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("roles", sa.Column("id", sa.String(), primary_key=True),
                    sa.Column("name", sa.String(), nullable=False),
                    sa.Column("active", sa.Boolean(create_constraint=True), nullable=False))
    op.create_table("permisos", sa.Column("id", sa.String(), primary_key=True),
                    sa.Column("role_id", sa.String(), sa.ForeignKey("roles.id"), nullable=False),
                    sa.Column("module", sa.String(), nullable=False),
                    *[sa.Column(f"can_{action}", sa.Boolean(create_constraint=True), nullable=False)
                      for action in ("create", "read", "edit", "delete", "sensitive", "export")],
                    sa.Column("active", sa.Boolean(create_constraint=True), nullable=False),
                    sa.UniqueConstraint("role_id", "module"))
    op.create_index("ix_permisos_role_id", "permisos", ["role_id"])
    op.create_table("usuarios", sa.Column("id", sa.String(), primary_key=True),
                    sa.Column("email", sa.String(), nullable=False, unique=True),
                    sa.Column("name", sa.String(), nullable=False),
                    sa.Column("role_id", sa.String(), sa.ForeignKey("roles.id"), nullable=False),
                    sa.Column("google_sub", sa.String(), unique=True, nullable=True),
                    sa.Column("active", sa.Boolean(create_constraint=True), nullable=False),
                    sa.Column("deleted", sa.Boolean(create_constraint=True), nullable=False),
                    sa.Column("version", sa.Integer(), nullable=False), sa.CheckConstraint("version >= 1"))
    op.create_index("ix_usuarios_role_id", "usuarios", ["role_id"])


def downgrade():
    op.drop_table("usuarios")
    op.drop_table("permisos")
    op.drop_table("roles")

