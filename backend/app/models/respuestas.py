from sqlalchemy import Boolean, CheckConstraint, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.security import Base, MetadatosComunes


class EnvioFormulario(MetadatosComunes, Base):
    """Fase 1 §4 línea 88 — cabecera NUEVA que no existe en el legacy: agrupa IdRespuesta y
    separa la identidad del envío del contenido, sustituyendo a RespuestasFormulario
    (Config.gs:55), que mezclaba ambas cosas en una sola fila por pregunta.

    UNIQUE(usuario_respuesta, id_envio_cliente) — a diferencia de la clave GLOBAL del
    legacy (Base Sistema/FormService.gs:418-421, hallazgo de Fase 1 §6), la unicidad es
    por usuario: un id_envio_cliente ajeno ya no puede colisionar ni actuar como oráculo
    de otra respuesta. SQLite no exige unicidad entre NULLs, así que las filas sin clave
    de cliente (id_envio_cliente=None) nunca compiten entre sí.
    """

    __tablename__ = "envios_formulario"
    __table_args__ = (
        UniqueConstraint("usuario_respuesta", "id_envio_cliente"),
        Index("ux_envios_formulario_numero_secuencial", "numero_secuencial", unique=True),
        Index("ux_envios_formulario_codigo_respuesta", "codigo_respuesta", unique=True),
        CheckConstraint("version >= 1", name="version_positive"),
    )

    id_respuesta: Mapped[str] = mapped_column(String, primary_key=True)
    id_formulario: Mapped[str] = mapped_column(ForeignKey("formularios.id_formulario"), index=True, nullable=False)
    id_version_formulario: Mapped[str | None] = mapped_column(ForeignKey("versiones_formulario.id_version_formulario"), index=True)
    usuario_respuesta: Mapped[str] = mapped_column(String, nullable=False)
    id_envio_cliente: Mapped[str | None] = mapped_column(String)
    estado: Mapped[str | None] = mapped_column(String)
    fecha_respuesta: Mapped[str | None] = mapped_column(String)
    # Referencia polimórfica (Fase 1 §4 línea 109): puede apuntar a Casos u otro proceso.
    # Se valida en servicio, nunca como FK real.
    id_registro_proceso: Mapped[str | None] = mapped_column(String)
    contexto_tipo: Mapped[str | None] = mapped_column(String, index=True)
    contexto_id: Mapped[str | None] = mapped_column(String, index=True)
    contexto_creado_dinamicamente: Mapped[bool] = mapped_column(Boolean, default=False)
    numero_secuencial: Mapped[int | None] = mapped_column(Integer)
    codigo_respuesta: Mapped[str | None] = mapped_column(String(21))


class SecuenciaRespuestaFormulario(Base):
    """Contador técnico global; no se elimina ni se reinicia por formulario o contexto."""

    __tablename__ = "secuencias_respuestas_formulario"
    __table_args__ = (
        CheckConstraint("ultimo_numero >= 0", name="secuencia_respuesta_non_negative"),
        CheckConstraint("ultimo_numero <= 99999999999", name="secuencia_respuesta_max_11_digits"),
    )

    nombre: Mapped[str] = mapped_column(String, primary_key=True)
    ultimo_numero: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class RespuestaFormulario(MetadatosComunes, Base):
    """Fase 1 §4 línea 89 — detalle tipado, una fila por pregunta (o por valor, en
    selección múltiple). No lleva UNIQUE(id_respuesta, id_pregunta): Fase 1 §4 línea 107
    es explícito en que las respuestas múltiples conservan varias filas por pregunta.
    """

    __tablename__ = "respuestas_formulario"
    __table_args__ = (CheckConstraint("version >= 1", name="version_positive"),)

    id_detalle_respuesta: Mapped[str] = mapped_column(String, primary_key=True)
    id_respuesta: Mapped[str] = mapped_column(ForeignKey("envios_formulario.id_respuesta"), index=True, nullable=False)
    id_pregunta: Mapped[str] = mapped_column(ForeignKey("preguntas.id_pregunta"), index=True, nullable=False)
    valor_texto: Mapped[str | None] = mapped_column(String)
    valor_numero: Mapped[float | None] = mapped_column(Float)
    valor_fecha: Mapped[str | None] = mapped_column(String)
    valor_booleano: Mapped[bool | None] = mapped_column(Boolean(create_constraint=True))
    valor_opcion: Mapped[str | None] = mapped_column(String)
