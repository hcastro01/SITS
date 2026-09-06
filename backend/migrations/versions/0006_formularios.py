"""Formularios, Preguntas, OpcionesPregunta, ReglasFormulario, EnviosFormulario,
RespuestasFormulario (Config.gs:51-55, Fase 1 §4 líneas 84-89).

EnviosFormulario/RespuestasFormulario son la reestructuración explícita de Fase 1 §4:
sustituyen a la única hoja RespuestasFormulario del legacy por una cabecera de envío y un
detalle tipado, en vez de repetir la identidad del envío en cada fila de respuesta.
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_formularios"
down_revision = "0005_casos_y_procesos"
branch_labels = None
depends_on = None


def _metadatos_comunes():
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
    op.create_table(
        "formularios",
        sa.Column("id_formulario", sa.String(), primary_key=True),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("descripcion", sa.String(), nullable=True),
        sa.Column("proceso", sa.String(), nullable=True),
        sa.Column("estado", sa.String(), nullable=True),
        sa.Column("responsable", sa.String(), nullable=True),
        sa.Column("fecha_publicacion", sa.String(), nullable=True),
        *_metadatos_comunes(),
        sa.CheckConstraint("version >= 1", name="version_positive"),
    )

    op.create_table(
        "preguntas",
        sa.Column("id_pregunta", sa.String(), primary_key=True),
        sa.Column("id_formulario", sa.String(), sa.ForeignKey("formularios.id_formulario"), nullable=False),
        sa.Column("etiqueta", sa.String(), nullable=False),
        sa.Column("descripcion", sa.String(), nullable=True),
        sa.Column("tipo", sa.String(), nullable=True),
        sa.Column("obligatoria", sa.Boolean(create_constraint=True), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("categoria", sa.String(), nullable=True),
        sa.Column("subcategoria", sa.String(), nullable=True),
        sa.Column("valor_predeterminado", sa.String(), nullable=True),
        sa.Column("texto_ayuda", sa.String(), nullable=True),
        sa.Column("visible", sa.Boolean(create_constraint=True), nullable=False),
        sa.Column("solo_lectura", sa.Boolean(create_constraint=True), nullable=False),
        sa.Column("longitud_maxima", sa.Integer(), nullable=True),
        sa.Column("validacion", sa.String(), nullable=True),
        sa.Column("sensibilidad", sa.String(), nullable=True),
        sa.Column("condicion_visibilidad", sa.String(), nullable=True),
        sa.Column("campo_dependiente", sa.String(), sa.ForeignKey("preguntas.id_pregunta"), nullable=True),
        sa.Column("valor_dependiente", sa.String(), nullable=True),
        sa.Column("formula", sa.String(), nullable=True),
        *_metadatos_comunes(),
        sa.CheckConstraint("version >= 1", name="version_positive"),
    )
    op.create_index("ix_preguntas_id_formulario", "preguntas", ["id_formulario"])
    op.create_index("ix_preguntas_campo_dependiente", "preguntas", ["campo_dependiente"])

    op.create_table(
        "opciones_pregunta",
        sa.Column("id_opcion", sa.String(), primary_key=True),
        sa.Column("id_pregunta", sa.String(), sa.ForeignKey("preguntas.id_pregunta"), nullable=False),
        sa.Column("valor", sa.String(), nullable=False),
        sa.Column("etiqueta", sa.String(), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("id_catalogo", sa.String(), sa.ForeignKey("catalogos.id_catalogo"), nullable=True),
        sa.Column("id_opcion_padre", sa.String(), sa.ForeignKey("opciones_pregunta.id_opcion"), nullable=True),
        *_metadatos_comunes(),
        sa.CheckConstraint("version >= 1", name="version_positive"),
    )
    op.create_index("ix_opciones_pregunta_id_pregunta", "opciones_pregunta", ["id_pregunta"])
    op.create_index("ix_opciones_pregunta_id_catalogo", "opciones_pregunta", ["id_catalogo"])
    op.create_index("ix_opciones_pregunta_id_opcion_padre", "opciones_pregunta", ["id_opcion_padre"])

    op.create_table(
        "reglas_formulario",
        sa.Column("id_regla", sa.String(), primary_key=True),
        sa.Column("id_formulario", sa.String(), sa.ForeignKey("formularios.id_formulario"), nullable=False),
        sa.Column("id_pregunta_origen", sa.String(), sa.ForeignKey("preguntas.id_pregunta"), nullable=False),
        sa.Column("operador", sa.String(), nullable=True),
        sa.Column("valor_comparacion", sa.String(), nullable=True),
        sa.Column("id_pregunta_destino", sa.String(), sa.ForeignKey("preguntas.id_pregunta"), nullable=True),
        sa.Column("accion", sa.String(), nullable=True),
        sa.Column("mensaje", sa.String(), nullable=True),
        sa.Column("orden", sa.Integer(), nullable=False),
        *_metadatos_comunes(),
        sa.CheckConstraint("version >= 1", name="version_positive"),
    )
    op.create_index("ix_reglas_formulario_id_formulario", "reglas_formulario", ["id_formulario"])
    op.create_index("ix_reglas_formulario_id_pregunta_origen", "reglas_formulario", ["id_pregunta_origen"])
    op.create_index("ix_reglas_formulario_id_pregunta_destino", "reglas_formulario", ["id_pregunta_destino"])

    op.create_table(
        "envios_formulario",
        sa.Column("id_respuesta", sa.String(), primary_key=True),
        sa.Column("id_formulario", sa.String(), sa.ForeignKey("formularios.id_formulario"), nullable=False),
        sa.Column("usuario_respuesta", sa.String(), nullable=False),
        sa.Column("id_envio_cliente", sa.String(), nullable=True),
        sa.Column("estado", sa.String(), nullable=True),
        sa.Column("fecha_respuesta", sa.String(), nullable=True),
        sa.Column("id_registro_proceso", sa.String(), nullable=True),
        *_metadatos_comunes(),
        sa.UniqueConstraint("usuario_respuesta", "id_envio_cliente", name="uq_envios_formulario_usuario_respuesta"),
        sa.CheckConstraint("version >= 1", name="version_positive"),
    )
    op.create_index("ix_envios_formulario_id_formulario", "envios_formulario", ["id_formulario"])

    op.create_table(
        "respuestas_formulario",
        sa.Column("id_detalle_respuesta", sa.String(), primary_key=True),
        sa.Column("id_respuesta", sa.String(), sa.ForeignKey("envios_formulario.id_respuesta"), nullable=False),
        sa.Column("id_pregunta", sa.String(), sa.ForeignKey("preguntas.id_pregunta"), nullable=False),
        sa.Column("valor_texto", sa.String(), nullable=True),
        sa.Column("valor_numero", sa.Float(), nullable=True),
        sa.Column("valor_fecha", sa.String(), nullable=True),
        sa.Column("valor_booleano", sa.Boolean(create_constraint=True), nullable=True),
        sa.Column("valor_opcion", sa.String(), nullable=True),
        *_metadatos_comunes(),
        sa.CheckConstraint("version >= 1", name="version_positive"),
    )
    op.create_index("ix_respuestas_formulario_id_respuesta", "respuestas_formulario", ["id_respuesta"])
    op.create_index("ix_respuestas_formulario_id_pregunta", "respuestas_formulario", ["id_pregunta"])


def downgrade():
    op.drop_table("respuestas_formulario")
    op.drop_table("envios_formulario")
    op.drop_table("reglas_formulario")
    op.drop_table("opciones_pregunta")
    op.drop_table("preguntas")
    op.drop_table("formularios")
