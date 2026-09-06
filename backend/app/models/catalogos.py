from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.security import Base, MetadatosComunes


class Catalogo(MetadatosComunes, Base):
    """Config.gs:67 (Catalogos), Fase 1 §4 línea 101. Jerárquico vía id_catalogo_padre."""

    __tablename__ = "catalogos"
    __table_args__ = (
        UniqueConstraint("tipo", "codigo"),
        CheckConstraint("version >= 1", name="version_positive"),
    )

    id_catalogo: Mapped[str] = mapped_column(String, primary_key=True)
    tipo: Mapped[str] = mapped_column(String, nullable=False)
    codigo: Mapped[str] = mapped_column(String, nullable=False)
    valor: Mapped[str] = mapped_column(String, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String)
    orden: Mapped[int] = mapped_column(Integer, default=0)
    id_catalogo_padre: Mapped[str | None] = mapped_column(ForeignKey("catalogos.id_catalogo"), index=True)
    tipo_padre: Mapped[str | None] = mapped_column(String)
    codigo_padre: Mapped[str | None] = mapped_column(String)
    es_sensible: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=False)
