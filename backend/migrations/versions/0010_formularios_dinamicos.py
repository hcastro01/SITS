"""Constructor dinámico de formularios, destinos, secciones y contexto.

Revision ID: 0010_formularios_dinamicos
Revises: 0009_password_auth
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "0010_formularios_dinamicos"
down_revision = "0009_password_auth"
branch_labels = None
depends_on = None


def _metadatos_comunes():
    return [
        sa.Column("activo", sa.Boolean(create_constraint=True), nullable=False, server_default=sa.true()),
        sa.Column("eliminado", sa.Boolean(create_constraint=True), nullable=False, server_default=sa.false()),
        sa.Column("fecha_creacion", sa.String(), nullable=True),
        sa.Column("creado_por", sa.String(), nullable=True),
        sa.Column("fecha_actualizacion", sa.String(), nullable=True),
        sa.Column("actualizado_por", sa.String(), nullable=True),
        sa.Column("fecha_eliminacion", sa.String(), nullable=True),
        sa.Column("usuario_eliminacion", sa.String(), nullable=True),
        sa.Column("motivo_eliminacion", sa.String(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("archivo_fuente", sa.String(), nullable=True),
        sa.Column("hoja_fuente", sa.String(), nullable=True),
        sa.Column("registro_fuente", sa.String(), nullable=True),
        sa.Column("fecha_importacion", sa.String(), nullable=True),
        sa.Column("usuario_importacion", sa.String(), nullable=True),
    ]


def upgrade() -> None:
    op.add_column("formularios", sa.Column("permite_multiples_respuestas", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("formularios", sa.Column("version_publicada", sa.Integer(), nullable=False, server_default="0"))

    op.create_table(
        "formulario_destinos",
        sa.Column("id_destino", sa.String(), primary_key=True),
        sa.Column("id_formulario", sa.String(), sa.ForeignKey("formularios.id_formulario"), nullable=False),
        sa.Column("modulo", sa.String(), nullable=False),
        *_metadatos_comunes(),
        sa.UniqueConstraint("id_formulario", "modulo"),
        sa.CheckConstraint("version >= 1", name="version_positive"),
    )
    op.create_index("ix_formulario_destinos_id_formulario", "formulario_destinos", ["id_formulario"])
    op.create_index("ix_formulario_destinos_modulo", "formulario_destinos", ["modulo"])

    op.create_table(
        "secciones_formulario",
        sa.Column("id_seccion", sa.String(), primary_key=True),
        sa.Column("id_formulario", sa.String(), sa.ForeignKey("formularios.id_formulario"), nullable=False),
        sa.Column("titulo", sa.String(), nullable=False),
        sa.Column("descripcion", sa.String(), nullable=True),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        *_metadatos_comunes(),
        sa.CheckConstraint("version >= 1", name="version_positive"),
    )
    op.create_index("ix_secciones_formulario_id_formulario", "secciones_formulario", ["id_formulario"])

    op.create_table(
        "versiones_formulario",
        sa.Column("id_version_formulario", sa.String(), primary_key=True),
        sa.Column("id_formulario", sa.String(), sa.ForeignKey("formularios.id_formulario"), nullable=False),
        sa.Column("numero_version", sa.Integer(), nullable=False),
        sa.Column("definicion_json", sa.String(), nullable=False),
        sa.Column("fecha_publicacion_version", sa.String(), nullable=False),
        sa.Column("publicado_por", sa.String(), nullable=False),
        *_metadatos_comunes(),
        sa.UniqueConstraint("id_formulario", "numero_version"),
        sa.CheckConstraint("version >= 1", name="version_positive"),
    )
    op.create_index("ix_versiones_formulario_id_formulario", "versiones_formulario", ["id_formulario"])

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        # Evita recrear tablas padre con datos: SQLite bloquearía el DROP temporal
        # por las FKs históricas de respuestas/opciones.
        op.execute(sa.text("ALTER TABLE preguntas ADD COLUMN id_seccion VARCHAR REFERENCES secciones_formulario(id_seccion)"))
        op.execute(sa.text("ALTER TABLE reglas_formulario ADD COLUMN id_seccion_destino VARCHAR REFERENCES secciones_formulario(id_seccion)"))
        op.execute(sa.text("ALTER TABLE envios_formulario ADD COLUMN id_version_formulario VARCHAR REFERENCES versiones_formulario(id_version_formulario)"))
    else:
        op.add_column("preguntas", sa.Column("id_seccion", sa.String(), sa.ForeignKey("secciones_formulario.id_seccion"), nullable=True))
        op.add_column("reglas_formulario", sa.Column("id_seccion_destino", sa.String(), sa.ForeignKey("secciones_formulario.id_seccion"), nullable=True))
        op.add_column("envios_formulario", sa.Column("id_version_formulario", sa.String(), sa.ForeignKey("versiones_formulario.id_version_formulario"), nullable=True))
    op.add_column("preguntas", sa.Column("configuracion", sa.String(), nullable=True))
    op.add_column("preguntas", sa.Column("fuente_datos", sa.String(), nullable=True))
    op.add_column("preguntas", sa.Column("mapping", sa.String(), nullable=True))
    op.create_index("ix_preguntas_id_seccion", "preguntas", ["id_seccion"])
    op.add_column("reglas_formulario", sa.Column("grupo", sa.String(), nullable=True, server_default="TODAS"))
    op.create_index("ix_reglas_formulario_id_seccion_destino", "reglas_formulario", ["id_seccion_destino"])
    op.add_column("envios_formulario", sa.Column("contexto_tipo", sa.String(), nullable=True))
    op.add_column("envios_formulario", sa.Column("contexto_id", sa.String(), nullable=True))
    op.create_index("ix_envios_formulario_id_version_formulario", "envios_formulario", ["id_version_formulario"])
    op.create_index("ix_envios_formulario_contexto_tipo", "envios_formulario", ["contexto_tipo"])
    op.create_index("ix_envios_formulario_contexto_id", "envios_formulario", ["contexto_id"])

    formularios = sa.table("formularios", sa.column("id_formulario"), sa.column("proceso"), sa.column("creado_por"), sa.column("fecha_creacion"))
    destinos = sa.table("formulario_destinos", sa.column("id_destino"), sa.column("id_formulario"), sa.column("modulo"), sa.column("creado_por"), sa.column("fecha_creacion"))
    envios = sa.table("envios_formulario", sa.column("id_formulario"), sa.column("id_registro_proceso"),
                      sa.column("contexto_tipo"), sa.column("contexto_id"))
    aliases = {"CASO": "CASOS", "ATENCION": "ATENCIONES", "NOVEDAD": "NOVEDADES", "RECORRIDO": "RECORRIDOS", "PERSONA": "PERSONAS", "GENERAL": "GENERAL"}
    for fila in bind.execute(sa.select(formularios.c.id_formulario, formularios.c.proceso, formularios.c.creado_por, formularios.c.fecha_creacion)):
        proceso = (fila.proceso or "").strip().upper()
        modulo = aliases.get(proceso, proceso if proceso in aliases.values() else "GENERAL")
        bind.execute(destinos.insert().values(id_destino=str(uuid4()), id_formulario=fila.id_formulario,
                     modulo=modulo, creado_por=fila.creado_por, fecha_creacion=fila.fecha_creacion))
        bind.execute(envios.update().where(envios.c.id_formulario == fila.id_formulario).values(
            contexto_tipo=modulo,
            contexto_id=envios.c.id_registro_proceso if modulo != "GENERAL" else None,
        ))


def downgrade() -> None:
    op.drop_index("ix_envios_formulario_contexto_id", table_name="envios_formulario")
    op.drop_index("ix_envios_formulario_contexto_tipo", table_name="envios_formulario")
    op.drop_index("ix_envios_formulario_id_version_formulario", table_name="envios_formulario")
    op.drop_column("envios_formulario", "contexto_id")
    op.drop_column("envios_formulario", "contexto_tipo")
    op.drop_column("envios_formulario", "id_version_formulario")
    op.drop_index("ix_reglas_formulario_id_seccion_destino", table_name="reglas_formulario")
    op.drop_column("reglas_formulario", "grupo")
    op.drop_column("reglas_formulario", "id_seccion_destino")
    op.drop_index("ix_preguntas_id_seccion", table_name="preguntas")
    op.drop_column("preguntas", "mapping")
    op.drop_column("preguntas", "fuente_datos")
    op.drop_column("preguntas", "configuracion")
    op.drop_column("preguntas", "id_seccion")
    op.drop_table("versiones_formulario")
    op.drop_table("secciones_formulario")
    op.drop_table("formulario_destinos")
    op.drop_column("formularios", "version_publicada")
    op.drop_column("formularios", "permite_multiples_respuestas")
