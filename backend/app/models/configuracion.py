from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.security import Base


class Configuracion(Base):
    """Config.gs:69 (Configuracion) — como Auditoria, sin bloque META (Fase 1 §4)."""

    __tablename__ = "configuracion"

    clave: Mapped[str] = mapped_column(String, primary_key=True)
    valor: Mapped[str | None] = mapped_column(String)
    descripcion: Mapped[str | None] = mapped_column(String)
    tipo: Mapped[str | None] = mapped_column(String)
    editable: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=True)
    fecha_actualizacion: Mapped[str | None] = mapped_column(String)
    actualizado_por: Mapped[str | None] = mapped_column(String)
