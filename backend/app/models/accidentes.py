from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.security import Base, MetadatosComunes


class Accidente(MetadatosComunes, Base):
    __tablename__ = "accidentes"
    __table_args__ = (
        UniqueConstraint("persona_id", "fecha_accidente", "clasificacion", name="uq_accidentes_persona_fecha_clasificacion"),
        CheckConstraint("version >= 1", name="version_positive"),
    )
    id_accidente: Mapped[str] = mapped_column(String, primary_key=True)
    persona_id: Mapped[str] = mapped_column(ForeignKey("personas.id_persona"), nullable=False, index=True)
    lote_id: Mapped[str | None] = mapped_column(ForeignKey("lotes_importacion_accidente.id_lote"), index=True)
    fecha_accidente: Mapped[str] = mapped_column(String, nullable=False)
    clasificacion: Mapped[str] = mapped_column(String, nullable=False)
    estado: Mapped[str] = mapped_column(String, nullable=False, default="ABIERTO")
    descripcion: Mapped[str] = mapped_column(String, nullable=False)
    observacion: Mapped[str | None] = mapped_column(String)


class LoteImportacionAccidente(MetadatosComunes, Base):
    __tablename__ = "lotes_importacion_accidente"
    __table_args__ = (CheckConstraint("version >= 1", name="version_positive"),)
    id_lote: Mapped[str] = mapped_column(String, primary_key=True)
    nombre_archivo: Mapped[str] = mapped_column(String, nullable=False)
    contenido_archivo: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id_usuario"), nullable=False, index=True)
    estado: Mapped[str] = mapped_column(String, nullable=False, default="ANALIZADO")
    total_filas: Mapped[int] = mapped_column(Integer, nullable=False)
    filas_validas: Mapped[int] = mapped_column(Integer, nullable=False)
    filas_con_error: Mapped[int] = mapped_column(Integer, nullable=False)
    filas_duplicadas: Mapped[int] = mapped_column(Integer, nullable=False)
    filas_importadas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ErrorImportacionAccidente(MetadatosComunes, Base):
    __tablename__ = "errores_importacion_accidente"
    __table_args__ = (CheckConstraint("version >= 1", name="version_positive"), Index("ix_errores_importacion_accidente_lote_fila", "lote_id", "numero_fila"))
    id_error: Mapped[str] = mapped_column(String, primary_key=True)
    lote_id: Mapped[str] = mapped_column(ForeignKey("lotes_importacion_accidente.id_lote"), nullable=False, index=True)
    numero_fila: Mapped[int] = mapped_column(Integer, nullable=False)
    codigo: Mapped[str] = mapped_column(String, nullable=False)
    mensaje: Mapped[str] = mapped_column(String, nullable=False)
    datos_fila: Mapped[str | None] = mapped_column(String)
