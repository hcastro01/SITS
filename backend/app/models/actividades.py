from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.security import Base, MetadatosComunes


class Actividad(MetadatosComunes, Base):
    __tablename__ = "actividades"
    __table_args__ = (
        CheckConstraint("version >= 1", name="version_positive"),
        Index("ix_actividades_estado_fecha_objetivo", "estado", "fecha_objetivo"),
    )

    id_actividad: Mapped[str] = mapped_column(String, primary_key=True)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    descripcion: Mapped[str] = mapped_column(String, nullable=False)
    responsable_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id_usuario"), index=True, nullable=False)
    tipo_fecha: Mapped[str] = mapped_column(String, nullable=False)
    fecha_objetivo: Mapped[str] = mapped_column(String, nullable=False)
    estado: Mapped[str] = mapped_column(String, nullable=False, default="PENDIENTE")
    persona_id: Mapped[str | None] = mapped_column(ForeignKey("personas.id_persona"), index=True)
    creado_por_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id_usuario"), index=True, nullable=False)
    fecha_finalizacion: Mapped[str | None] = mapped_column(String)
