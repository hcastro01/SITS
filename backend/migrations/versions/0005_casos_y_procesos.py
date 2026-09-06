"""Atenciones, Casos, DetalleCasosSensibles, Novedades, Recorridos, HallazgosRecorrido,
Seguimientos, Derivaciones, Compromisos, Cierres (Config.gs:56-65, Fase 1 §4 líneas 90-99)."""
from alembic import op
import sqlalchemy as sa

revision = "0005_casos_y_procesos"
down_revision = "0004_catalogos_configuracion_personas"
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
        "novedades",
        sa.Column("id_novedad", sa.String(), primary_key=True),
        sa.Column("fecha", sa.String(), nullable=True),
        sa.Column("hora", sa.String(), nullable=True),
        sa.Column("responsable", sa.String(), nullable=True),
        sa.Column("fuente", sa.String(), nullable=True),
        sa.Column("tipo", sa.String(), nullable=True),
        sa.Column("subtipo", sa.String(), nullable=True),
        sa.Column("area", sa.String(), nullable=True),
        sa.Column("turno", sa.String(), nullable=True),
        sa.Column("lugar", sa.String(), nullable=True),
        sa.Column("descripcion", sa.String(), nullable=True),
        sa.Column("impacto", sa.String(), nullable=True),
        sa.Column("prioridad", sa.String(), nullable=True),
        sa.Column("accion_inmediata", sa.String(), nullable=True),
        sa.Column("genera_atencion", sa.Boolean(create_constraint=True), nullable=False),
        sa.Column("genera_caso", sa.Boolean(create_constraint=True), nullable=False),
        sa.Column("estado", sa.String(), nullable=True),
        sa.Column("evidencias", sa.String(), nullable=True),
        *_metadatos_comunes(),
        sa.CheckConstraint("version >= 1", name="version_positive"),
    )

    op.create_table(
        "recorridos",
        sa.Column("id_recorrido", sa.String(), primary_key=True),
        sa.Column("fecha", sa.String(), nullable=True),
        sa.Column("hora_inicio", sa.String(), nullable=True),
        sa.Column("hora_fin", sa.String(), nullable=True),
        sa.Column("responsable", sa.String(), nullable=True),
        sa.Column("planta", sa.String(), nullable=True),
        sa.Column("area", sa.String(), nullable=True),
        sa.Column("turno", sa.String(), nullable=True),
        sa.Column("objetivo", sa.String(), nullable=True),
        sa.Column("observaciones", sa.String(), nullable=True),
        sa.Column("personas_contactadas", sa.String(), nullable=True),
        sa.Column("novedades_detectadas", sa.String(), nullable=True),
        sa.Column("acciones", sa.String(), nullable=True),
        sa.Column("evidencias", sa.String(), nullable=True),
        *_metadatos_comunes(),
        sa.CheckConstraint("version >= 1", name="version_positive"),
    )

    op.create_table(
        "atenciones",
        sa.Column("id_atencion", sa.String(), primary_key=True),
        sa.Column("fecha", sa.String(), nullable=True),
        sa.Column("hora", sa.String(), nullable=True),
        sa.Column("id_persona", sa.String(), sa.ForeignKey("personas.id_persona"), nullable=True),
        sa.Column("colaborador", sa.String(), nullable=True),
        sa.Column("responsable", sa.String(), nullable=True),
        sa.Column("tipo_atencion", sa.String(), nullable=True),
        sa.Column("motivo", sa.String(), nullable=True),
        sa.Column("canal", sa.String(), nullable=True),
        sa.Column("gestion", sa.String(), nullable=True),
        sa.Column("resultado", sa.String(), nullable=True),
        sa.Column("requiere_seguimiento", sa.Boolean(create_constraint=True), nullable=False),
        sa.Column("genera_caso", sa.Boolean(create_constraint=True), nullable=False),
        sa.Column("observaciones", sa.String(), nullable=True),
        sa.Column("evidencias", sa.String(), nullable=True),
        sa.Column("estado", sa.String(), nullable=True),
        *_metadatos_comunes(),
        sa.CheckConstraint("version >= 1", name="version_positive"),
    )
    op.create_index("ix_atenciones_id_persona", "atenciones", ["id_persona"])

    op.create_table(
        "casos",
        sa.Column("id_caso", sa.String(), primary_key=True),
        sa.Column("codigo_caso", sa.String(), nullable=False, unique=True),
        sa.Column("fecha_apertura", sa.String(), nullable=True),
        sa.Column("id_persona", sa.String(), sa.ForeignKey("personas.id_persona"), nullable=True),
        sa.Column("colaborador", sa.String(), nullable=True),
        sa.Column("responsable", sa.String(), nullable=True),
        sa.Column("tipo_caso", sa.String(), nullable=True),
        sa.Column("subtipo_caso", sa.String(), nullable=True),
        sa.Column("prioridad", sa.String(), nullable=True),
        sa.Column("nivel_sensibilidad", sa.String(), nullable=True),
        sa.Column("estado_caso", sa.String(), nullable=True),
        sa.Column("tipo_gestion", sa.String(), nullable=True),
        sa.Column("tipo_evento", sa.String(), nullable=True),
        sa.Column("area", sa.String(), nullable=True),
        sa.Column("turno", sa.String(), nullable=True),
        sa.Column("condicion_laboral", sa.String(), nullable=True),
        sa.Column("restriccion", sa.Boolean(create_constraint=True), nullable=False),
        sa.Column("fecha_inicio_restriccion", sa.String(), nullable=True),
        sa.Column("derivacion", sa.Boolean(create_constraint=True), nullable=False),
        sa.Column("ultimo_seguimiento", sa.String(), nullable=True),
        sa.Column("fecha_cierre", sa.String(), nullable=True),
        sa.Column("motivo_cierre", sa.String(), nullable=True),
        sa.Column("resultado", sa.String(), nullable=True),
        sa.Column("evidencias", sa.String(), nullable=True),
        *_metadatos_comunes(),
        sa.CheckConstraint("version >= 1", name="version_positive"),
    )
    op.create_index("ix_casos_id_persona", "casos", ["id_persona"])
    op.create_index("ix_casos_responsable", "casos", ["responsable"])
    op.create_index("ix_casos_estado_caso_fecha_apertura", "casos", ["estado_caso", "fecha_apertura"])

    op.create_table(
        "hallazgos_recorrido",
        sa.Column("id_hallazgo", sa.String(), primary_key=True),
        sa.Column("id_recorrido", sa.String(), sa.ForeignKey("recorridos.id_recorrido"), nullable=False),
        sa.Column("tipo_hallazgo", sa.String(), nullable=True),
        sa.Column("categoria", sa.String(), nullable=True),
        sa.Column("subcategoria", sa.String(), nullable=True),
        sa.Column("area", sa.String(), nullable=True),
        sa.Column("descripcion", sa.String(), nullable=True),
        sa.Column("prioridad", sa.String(), nullable=True),
        sa.Column("accion", sa.String(), nullable=True),
        sa.Column("genera_novedad", sa.Boolean(create_constraint=True), nullable=False),
        sa.Column("id_novedad", sa.String(), sa.ForeignKey("novedades.id_novedad"), nullable=True),
        sa.Column("genera_caso", sa.Boolean(create_constraint=True), nullable=False),
        sa.Column("id_caso", sa.String(), sa.ForeignKey("casos.id_caso"), nullable=True),
        sa.Column("estado", sa.String(), nullable=True),
        *_metadatos_comunes(),
        sa.CheckConstraint("version >= 1", name="version_positive"),
    )
    op.create_index("ix_hallazgos_recorrido_id_recorrido", "hallazgos_recorrido", ["id_recorrido"])
    op.create_index("ix_hallazgos_recorrido_id_novedad", "hallazgos_recorrido", ["id_novedad"])
    op.create_index("ix_hallazgos_recorrido_id_caso", "hallazgos_recorrido", ["id_caso"])

    op.create_table(
        "detalle_casos_sensibles",
        sa.Column("id_detalle_sensible", sa.String(), primary_key=True),
        sa.Column("id_caso", sa.String(), sa.ForeignKey("casos.id_caso"), nullable=False, unique=True),
        sa.Column("descripcion_sensible", sa.String(), nullable=True),
        sa.Column("antecedentes", sa.String(), nullable=True),
        sa.Column("diagnostico_social", sa.String(), nullable=True),
        sa.Column("intervencion", sa.String(), nullable=True),
        sa.Column("notas_privadas", sa.String(), nullable=True),
        *_metadatos_comunes(),
        sa.CheckConstraint("version >= 1", name="version_positive"),
    )

    op.create_table(
        "seguimientos",
        sa.Column("id_seguimiento", sa.String(), primary_key=True),
        sa.Column("id_caso", sa.String(), sa.ForeignKey("casos.id_caso"), nullable=False),
        sa.Column("fecha", sa.String(), nullable=True),
        sa.Column("hora", sa.String(), nullable=True),
        sa.Column("responsable", sa.String(), nullable=True),
        sa.Column("tipo_seguimiento", sa.String(), nullable=True),
        sa.Column("canal", sa.String(), nullable=True),
        sa.Column("tecnica", sa.String(), nullable=True),
        sa.Column("descripcion", sa.String(), nullable=True),
        sa.Column("resultado", sa.String(), nullable=True),
        sa.Column("proxima_accion", sa.String(), nullable=True),
        sa.Column("fecha_proxima_accion", sa.String(), nullable=True),
        sa.Column("estado", sa.String(), nullable=True),
        sa.Column("evidencias", sa.String(), nullable=True),
        *_metadatos_comunes(),
        sa.CheckConstraint("version >= 1", name="version_positive"),
    )
    op.create_index("ix_seguimientos_id_caso", "seguimientos", ["id_caso"])

    op.create_table(
        "derivaciones",
        sa.Column("id_derivacion", sa.String(), primary_key=True),
        sa.Column("id_caso", sa.String(), sa.ForeignKey("casos.id_caso"), nullable=False),
        sa.Column("fecha", sa.String(), nullable=True),
        sa.Column("area_destino", sa.String(), nullable=True),
        sa.Column("responsable_destino", sa.String(), nullable=True),
        sa.Column("motivo", sa.String(), nullable=True),
        sa.Column("estado", sa.String(), nullable=True),
        sa.Column("fecha_respuesta", sa.String(), nullable=True),
        sa.Column("resultado", sa.String(), nullable=True),
        sa.Column("fecha_cierre", sa.String(), nullable=True),
        sa.Column("observaciones", sa.String(), nullable=True),
        *_metadatos_comunes(),
        sa.CheckConstraint("version >= 1", name="version_positive"),
    )
    op.create_index("ix_derivaciones_id_caso", "derivaciones", ["id_caso"])

    op.create_table(
        "compromisos",
        sa.Column("id_compromiso", sa.String(), primary_key=True),
        sa.Column("id_caso", sa.String(), sa.ForeignKey("casos.id_caso"), nullable=False),
        sa.Column("id_seguimiento", sa.String(), sa.ForeignKey("seguimientos.id_seguimiento"), nullable=True),
        sa.Column("fecha_creacion_compromiso", sa.String(), nullable=True),
        sa.Column("responsable", sa.String(), nullable=True),
        sa.Column("descripcion", sa.String(), nullable=True),
        sa.Column("fecha_limite", sa.String(), nullable=True),
        sa.Column("estado", sa.String(), nullable=True),
        sa.Column("fecha_cumplimiento", sa.String(), nullable=True),
        sa.Column("evidencia", sa.String(), nullable=True),
        sa.Column("observacion", sa.String(), nullable=True),
        *_metadatos_comunes(),
        sa.CheckConstraint("version >= 1", name="version_positive"),
    )
    op.create_index("ix_compromisos_id_caso", "compromisos", ["id_caso"])
    op.create_index("ix_compromisos_id_seguimiento", "compromisos", ["id_seguimiento"])

    op.create_table(
        "cierres",
        sa.Column("id_cierre", sa.String(), primary_key=True),
        sa.Column("id_caso", sa.String(), sa.ForeignKey("casos.id_caso"), nullable=False),
        sa.Column("fecha_cierre_caso", sa.String(), nullable=True),
        sa.Column("responsable", sa.String(), nullable=True),
        sa.Column("motivo_cierre", sa.String(), nullable=True),
        sa.Column("resultado_final", sa.String(), nullable=True),
        sa.Column("evidencia", sa.String(), nullable=True),
        sa.Column("requiere_monitoreo", sa.Boolean(create_constraint=True), nullable=False),
        sa.Column("observacion", sa.String(), nullable=True),
        *_metadatos_comunes(),
        sa.CheckConstraint("version >= 1", name="version_positive"),
    )
    op.create_index("ix_cierres_id_caso", "cierres", ["id_caso"])


def downgrade():
    op.drop_table("cierres")
    op.drop_table("compromisos")
    op.drop_table("derivaciones")
    op.drop_table("seguimientos")
    op.drop_table("detalle_casos_sensibles")
    op.drop_table("hallazgos_recorrido")
    op.drop_table("casos")
    op.drop_table("atenciones")
    op.drop_table("recorridos")
    op.drop_table("novedades")
