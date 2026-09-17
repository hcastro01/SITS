"""Entidades operativas mínimas de Oficina.

Los tres conceptos conservan su propia tabla, pero comparten únicamente los
metadatos, la relación opcional con Persona y el ciclo de vida común de SITS.
No modelan estados, montos ni datos de dependientes que no fueron definidos.
"""

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.security import Base, MetadatosComunes


class Beneficio(MetadatosComunes, Base):
    __tablename__ = "beneficios"
    __table_args__ = (
        CheckConstraint("version >= 1", name="version_positive"),
        CheckConstraint("tipo_beneficio IN ('TIA', 'FARMACIA')", name="tipo_beneficio_valido"),
        CheckConstraint("tipo_gestion IN ('ACTIVACION', 'BLOQUEO', 'ANULACION')", name="tipo_gestion_valido"),
        Index("ix_beneficios_tipo_fecha", "tipo_beneficio", "fecha"),
    )

    id_beneficio: Mapped[str] = mapped_column(String, primary_key=True)
    fecha: Mapped[str | None] = mapped_column(String)
    persona_id: Mapped[str | None] = mapped_column(ForeignKey("personas.id_persona"), index=True)
    tipo_beneficio: Mapped[str] = mapped_column(String, nullable=False)
    tipo_gestion: Mapped[str] = mapped_column(String, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String)
    observacion: Mapped[str | None] = mapped_column(String)
    responsable: Mapped[str | None] = mapped_column(String)


class Prestamo(MetadatosComunes, Base):
    __tablename__ = "prestamos"
    __table_args__ = (
        CheckConstraint("version >= 1", name="version_positive"),
        CheckConstraint("tipo IN ('PRESTAMO', 'ANTICIPO')", name="tipo_valido"),
        Index("ix_prestamos_tipo_fecha", "tipo", "fecha"),
    )

    id_prestamo: Mapped[str] = mapped_column(String, primary_key=True)
    fecha: Mapped[str | None] = mapped_column(String)
    persona_id: Mapped[str | None] = mapped_column(ForeignKey("personas.id_persona"), index=True)
    tipo: Mapped[str] = mapped_column(String, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String)
    observacion: Mapped[str | None] = mapped_column(String)
    responsable: Mapped[str | None] = mapped_column(String)


class Seguro(MetadatosComunes, Base):
    __tablename__ = "seguros"
    __table_args__ = (
        CheckConstraint("version >= 1", name="version_positive"),
        CheckConstraint(
            "tipo_gestion IN ('AFILIACION', 'ENROLAMIENTO', 'COBERTURA', 'REEMBOLSO', 'PRIMA', 'DEPENDIENTE')",
            name="tipo_gestion_valido",
        ),
        Index("ix_seguros_tipo_gestion_fecha", "tipo_gestion", "fecha"),
    )

    id_seguro: Mapped[str] = mapped_column(String, primary_key=True)
    fecha: Mapped[str | None] = mapped_column(String)
    persona_id: Mapped[str | None] = mapped_column(ForeignKey("personas.id_persona"), index=True)
    tipo_gestion: Mapped[str] = mapped_column(String, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String)
    observacion: Mapped[str | None] = mapped_column(String)
    responsable: Mapped[str | None] = mapped_column(String)
