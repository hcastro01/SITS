from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.security import Base, MetadatosComunes


class Persona(MetadatosComunes, Base):
    """Config.gs:50 (Personas), Fase 1 §4 línea 83.

    cedula y codigo_empleado son TEXT (Fase 1 §4: "no convertir cédulas/códigos en números
    ni perder ceros iniciales") y NO son únicos todavía: MIGRACION_FASE_1.md §4 exige
    auditar duplicados reales antes de declarar esa restricción.
    """

    __tablename__ = "personas"
    __table_args__ = (CheckConstraint("version >= 1", name="version_positive"),)

    id_persona: Mapped[str] = mapped_column(String, primary_key=True)
    codigo_empleado: Mapped[str | None] = mapped_column(String, index=True)
    cedula: Mapped[str | None] = mapped_column(String, index=True)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    cargo: Mapped[str | None] = mapped_column(String)
    area: Mapped[str | None] = mapped_column(String)
    departamento: Mapped[str | None] = mapped_column(String)
    centro: Mapped[str | None] = mapped_column(String)
    sub_centro: Mapped[str | None] = mapped_column(String)
    turno: Mapped[str | None] = mapped_column(String)
    estado_laboral: Mapped[str | None] = mapped_column(String)
