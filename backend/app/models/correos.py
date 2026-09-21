from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.security import Base, MetadatosComunes


class LoteImportacionCorreo(MetadatosComunes, Base):
    __tablename__ = "lotes_importacion_correo"
    __table_args__ = (CheckConstraint("version >= 1", name="version_positive"),)

    id_lote: Mapped[str] = mapped_column(String, primary_key=True)
    nombre_archivo: Mapped[str] = mapped_column(String, nullable=False)
    contenido_archivo: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id_usuario"), index=True, nullable=False)
    estado: Mapped[str] = mapped_column(String, nullable=False)
    total_filas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    filas_clasificadas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    filas_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    filas_importadas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    filas_procesadas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    filas_duplicadas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    filas_omitidas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    filas_error: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    origen: Mapped[str] = mapped_column(String, nullable=False, default="XLSX")
    duracion_ms: Mapped[int | None] = mapped_column(Integer)


class Correo(MetadatosComunes, Base):
    __tablename__ = "correos"
    __table_args__ = (
        UniqueConstraint("id_externo_correo", name="uq_correos_id_externo"),
        UniqueConstraint("idempotency_key", name="uq_correos_idempotency"),
        CheckConstraint("estado_clasificacion IN ('CLASIFICADO', 'REVISION')", name="estado_clasificacion_valido"),
        CheckConstraint("estado_requerimiento IN ('PENDIENTE', 'EN_PROCESO', 'EN_ESPERA', 'RESUELTO', 'CERRADO')", name="estado_requerimiento_valido"),
        CheckConstraint("version >= 1", name="version_positive"),
        Index("ix_correos_recibido", "fecha_recibido"),
        Index("ix_correos_estado_categoria", "estado_requerimiento", "categoria_macro"),
    )

    id_correo: Mapped[str] = mapped_column(String, primary_key=True)
    id_externo_correo: Mapped[str] = mapped_column(String, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String, nullable=False)
    asunto: Mapped[str] = mapped_column(String, nullable=False, default="")
    remitente: Mapped[str | None] = mapped_column(String)
    destinatarios: Mapped[str | None] = mapped_column(Text)
    cc: Mapped[str | None] = mapped_column(Text)
    fecha_recibido: Mapped[str | None] = mapped_column(String)
    importancia: Mapped[str | None] = mapped_column(String)
    cuerpo: Mapped[str | None] = mapped_column(Text)
    tiene_adjuntos: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=False)
    leido: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=False)
    categoria_macro: Mapped[str | None] = mapped_column(String, index=True)
    categoria_nombre: Mapped[str | None] = mapped_column(String)
    estado_categoria: Mapped[str] = mapped_column(String, nullable=False, default="SIN_CATEGORIA", index=True)
    regla_disparadora: Mapped[str | None] = mapped_column(String)
    estado_clasificacion: Mapped[str] = mapped_column(String, nullable=False, default="REVISION")
    estado_requerimiento: Mapped[str] = mapped_column(String, nullable=False, default="PENDIENTE", index=True)
    responsable_seguimiento: Mapped[str | None] = mapped_column(String, index=True)
    lote_id: Mapped[str | None] = mapped_column(ForeignKey("lotes_importacion_correo.id_lote"), index=True)


class SeguimientoCorreo(MetadatosComunes, Base):
    __tablename__ = "seguimientos_correo"
    __table_args__ = (
        CheckConstraint("estado_requerimiento IN ('PENDIENTE', 'EN_PROCESO', 'EN_ESPERA', 'RESUELTO', 'CERRADO')", name="estado_requerimiento_valido"),
        CheckConstraint("version >= 1", name="version_positive"),
        Index("ix_seguimientos_correo_correo_fecha", "correo_id", "fecha_seguimiento"),
    )

    id_seguimiento: Mapped[str] = mapped_column(String, primary_key=True)
    correo_id: Mapped[str] = mapped_column(ForeignKey("correos.id_correo"), nullable=False, index=True)
    fecha_seguimiento: Mapped[str | None] = mapped_column(String)
    detalle_seguimiento: Mapped[str] = mapped_column(Text, nullable=False)
    seguimiento_por: Mapped[str | None] = mapped_column(String)
    estado_requerimiento: Mapped[str] = mapped_column(String, nullable=False)


class ErrorImportacionCorreo(MetadatosComunes, Base):
    """Error por fila; conserva trazabilidad sin guardar el contenido sensible del correo."""

    __tablename__ = "errores_importacion_correo"
    __table_args__ = (
        CheckConstraint("version >= 1", name="version_positive"),
        Index("ix_errores_importacion_correo_lote_fila", "lote_id", "fila"),
    )

    id_error: Mapped[str] = mapped_column(String, primary_key=True)
    lote_id: Mapped[str] = mapped_column(ForeignKey("lotes_importacion_correo.id_lote"), nullable=False, index=True)
    fila: Mapped[int | None] = mapped_column(Integer)
    id_externo_correo: Mapped[str | None] = mapped_column(String)
    codigo: Mapped[str] = mapped_column(String, nullable=False)
    detalle: Mapped[str] = mapped_column(String, nullable=False)
