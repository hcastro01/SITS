"""Nomenclatura en español y metadatos comunes de Config.gs. Sin datos productivos: recrea las tablas."""
from alembic import op
import sqlalchemy as sa

revision = "0002_nomenclatura_es"
down_revision = "0001_security"
branch_labels = None
depends_on = None


def _metadatos_comunes():
    # sa.Column no puede reutilizarse entre op.create_table; se reconstruye por tabla.
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


def upgrade():
    # No hay datos productivos (MIGRACION_LOCAL.md): se recrean las tablas en vez de
    # intentar un rename en caliente. seed_security() repuebla roles y permisos al reiniciar.
    op.drop_table("permisos")
    op.drop_table("usuarios")
    op.drop_table("roles")

    op.create_table(
        "roles",
        sa.Column("id_rol", sa.String(), primary_key=True),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("descripcion", sa.String(), nullable=True),
        *_metadatos_comunes(),
        sa.CheckConstraint("version >= 1", name="version_positive"),
    )
    op.create_table(
        "permisos",
        sa.Column("id_permiso", sa.String(), primary_key=True),
        sa.Column("rol_id", sa.String(), sa.ForeignKey("roles.id_rol"), nullable=False),
        sa.Column("modulo", sa.String(), nullable=False),
        sa.Column("puede_crear", sa.Boolean(create_constraint=True), nullable=False),
        sa.Column("puede_leer", sa.Boolean(create_constraint=True), nullable=False),
        sa.Column("puede_editar", sa.Boolean(create_constraint=True), nullable=False),
        sa.Column("puede_eliminar", sa.Boolean(create_constraint=True), nullable=False),
        sa.Column("puede_sensible", sa.Boolean(create_constraint=True), nullable=False),
        sa.Column("puede_exportar", sa.Boolean(create_constraint=True), nullable=False),
        *_metadatos_comunes(),
        sa.UniqueConstraint("rol_id", "modulo", name="uq_permisos_rol_id"),
        sa.CheckConstraint("version >= 1", name="version_positive"),
    )
    op.create_index("ix_permisos_rol_id", "permisos", ["rol_id"])

    op.create_table(
        "usuarios",
        sa.Column("id_usuario", sa.String(), primary_key=True),
        sa.Column("correo", sa.String(), nullable=False, unique=True),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("rol_id", sa.String(), sa.ForeignKey("roles.id_rol"), nullable=False),
        sa.Column("estado", sa.String(), nullable=False),
        sa.Column("ultimo_acceso", sa.String(), nullable=True),
        sa.Column("google_sub", sa.String(), unique=True, nullable=True),
        *_metadatos_comunes(),
        sa.CheckConstraint("version >= 1", name="version_positive"),
    )
    op.create_index("ix_usuarios_rol_id", "usuarios", ["rol_id"])


def downgrade():
    op.drop_table("usuarios")
    op.drop_table("permisos")
    op.drop_table("roles")

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
