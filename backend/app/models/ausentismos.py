from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.security import Base, MetadatosComunes


class Ausentismo(MetadatosComunes, Base):
    """Ausencia laboral importable, vinculada a una Persona por su cédula."""

    __tablename__ = "ausentismos"
    __table_args__ = (
        UniqueConstraint(
            "persona_id",
            "fecha_inicio",
            "fecha_fin",
            "tipo_ausentismo",
            name="uq_ausentismos_persona_fechas_tipo",
        ),
        CheckConstraint("version >= 1", name="version_positive"),
    )

    id_ausentismo: Mapped[str] = mapped_column(String, primary_key=True)
    persona_id: Mapped[str] = mapped_column(ForeignKey("personas.id_persona"), nullable=False)
    fecha_inicio: Mapped[str] = mapped_column(String, nullable=False)
    fecha_fin: Mapped[str] = mapped_column(String, nullable=False)
    tipo_ausentismo: Mapped[str] = mapped_column(String, nullable=False)
    motivo: Mapped[str] = mapped_column(String, nullable=False)
    observacion: Mapped[str | None] = mapped_column(String)


class LoteImportacionAusentismo(MetadatosComunes, Base):
    """Archivo XLSX analizado; su contenido permite revalidar antes de confirmar."""

    __tablename__ = "lotes_importacion_ausentismo"
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


class ErrorImportacionAusentismo(MetadatosComunes, Base):
    """Incidencia por fila; duplicados se conservan como incidencias visibles."""

    __tablename__ = "errores_importacion_ausentismo"
    __table_args__ = (
        CheckConstraint("version >= 1", name="version_positive"),
        Index("ix_errores_importacion_ausentismo_lote_fila", "lote_id", "numero_fila"),
    )

    id_error: Mapped[str] = mapped_column(String, primary_key=True)
    lote_id: Mapped[str] = mapped_column(ForeignKey("lotes_importacion_ausentismo.id_lote"), nullable=False, index=True)
    numero_fila: Mapped[int] = mapped_column(Integer, nullable=False)
    codigo: Mapped[str] = mapped_column(String, nullable=False)
    mensaje: Mapped[str] = mapped_column(String, nullable=False)
    datos_fila: Mapped[str | None] = mapped_column(String)
