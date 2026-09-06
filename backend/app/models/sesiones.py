from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.security import Base


class Sesion(Base):
    """Fase 1 §4 línea 105 — como Auditoria/Configuracion, sin bloque META.

    Nunca se guarda el token en claro: solo su hash (token_hash). El valor que viaja en la
    cookie del navegador es el único lugar donde existe el token real.
    """

    __tablename__ = "sesiones"

    id_sesion: Mapped[str] = mapped_column(String, primary_key=True)
    token_hash: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    id_usuario: Mapped[str] = mapped_column(ForeignKey("usuarios.id_usuario"), index=True, nullable=False)
    fecha_creacion: Mapped[str] = mapped_column(String, nullable=False)
    expira_en: Mapped[str] = mapped_column(String, nullable=False)
    revocada_en: Mapped[str | None] = mapped_column(String)
