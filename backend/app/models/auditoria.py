from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.security import Base


class Auditoria(Base):
    """Config.gs:68 — única de las 24 hojas legacy sin bloque META: append-only, sin soft delete."""

    __tablename__ = "auditoria"
    __table_args__ = (
        Index("ix_auditoria_tabla_id_registro_fecha_hora", "tabla", "id_registro", "fecha_hora"),
    )

    id_auditoria: Mapped[str] = mapped_column(String, primary_key=True)
    tabla: Mapped[str] = mapped_column(String, nullable=False)
    id_registro: Mapped[str] = mapped_column(String, nullable=False)
    accion: Mapped[str] = mapped_column(String, nullable=False)
    usuario: Mapped[str] = mapped_column(String, nullable=False)
    fecha_hora: Mapped[str] = mapped_column(String, nullable=False)
    campo: Mapped[str] = mapped_column(String, nullable=False)
    valor_anterior: Mapped[str | None] = mapped_column(String)
    valor_nuevo: Mapped[str | None] = mapped_column(String)
    motivo: Mapped[str | None] = mapped_column(String)
    correlation_id: Mapped[str | None] = mapped_column(String)
