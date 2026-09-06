from sqlalchemy import CheckConstraint, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.security import Base, MetadatosComunes


class Documento(MetadatosComunes, Base):
    """Config.gs:66 (Documentos), Fase 1 §4 línea 100 — adaptado a BLOB comprimido en
    SQLite en vez de almacenamiento privado en disco (decisión explícita del usuario:
    archivos en BLOB de SQLite, comprimidos, para reducir espacio).

    tipo_registro/id_registro son una referencia polimórfica (Fase 1 §4 línea 109): se
    valida en servicio (app/services/documentos.py), nunca como FK real. `sha256` no es
    único: dos documentos distintos pueden compartir contenido byte-idéntico
    legítimamente (p. ej. una plantilla reutilizada).
    """

    __tablename__ = "documentos"
    __table_args__ = (CheckConstraint("version >= 1", name="version_positive"),)

    id_archivo: Mapped[str] = mapped_column(String, primary_key=True)
    tipo_registro: Mapped[str] = mapped_column(String, nullable=False, index=True)
    id_registro: Mapped[str] = mapped_column(String, nullable=False, index=True)
    nombre_archivo: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    extension: Mapped[str] = mapped_column(String, nullable=False)
    tamano_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    tamano_comprimido_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    contenido_comprimido: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    sha256: Mapped[str] = mapped_column(String, nullable=False, index=True)
    categoria_documento: Mapped[str | None] = mapped_column(String)
    sensibilidad: Mapped[str | None] = mapped_column(String)
