from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
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
