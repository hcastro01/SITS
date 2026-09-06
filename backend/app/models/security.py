from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, MetaData, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
# Sin clave "ck": los CHECK anónimos de Boolean(create_constraint=True) no tienen
# columna ni nombre asociado, y una convención "ck" con %(constraint_name)s exige
# que todo CHECK esté nombrado explícitamente (incluidos los que genera ese tipo).


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class MetadatosComunes:
    """Bloque META de Base Sistema/Config.gs:39-44, sin datos de importación aplicados aún."""

    activo: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=True)
    eliminado: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=False)
    fecha_creacion: Mapped[str | None] = mapped_column(String)
    creado_por: Mapped[str | None] = mapped_column(String)
    fecha_actualizacion: Mapped[str | None] = mapped_column(String)
    actualizado_por: Mapped[str | None] = mapped_column(String)
    fecha_eliminacion: Mapped[str | None] = mapped_column(String)
    usuario_eliminacion: Mapped[str | None] = mapped_column(String)
    motivo_eliminacion: Mapped[str | None] = mapped_column(String)
    version: Mapped[int] = mapped_column(Integer, default=1)
    archivo_fuente: Mapped[str | None] = mapped_column(String)
    hoja_fuente: Mapped[str | None] = mapped_column(String)
    registro_fuente: Mapped[str | None] = mapped_column(String)
    fecha_importacion: Mapped[str | None] = mapped_column(String)
    usuario_importacion: Mapped[str | None] = mapped_column(String)


class Role(MetadatosComunes, Base):
    __tablename__ = "roles"
    __table_args__ = (CheckConstraint("version >= 1", name="version_positive"),)
    id_rol: Mapped[str] = mapped_column(String, primary_key=True)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String)


class Permission(MetadatosComunes, Base):
    __tablename__ = "permisos"
    __table_args__ = (
        UniqueConstraint("rol_id", "modulo"),
        CheckConstraint("version >= 1", name="version_positive"),
    )
    id_permiso: Mapped[str] = mapped_column(String, primary_key=True)
    rol_id: Mapped[str] = mapped_column(ForeignKey("roles.id_rol"), index=True)
    modulo: Mapped[str] = mapped_column(String)
    puede_crear: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=False)
    puede_leer: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=False)
    puede_editar: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=False)
    puede_eliminar: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=False)
    puede_sensible: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=False)
    puede_exportar: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=False)


class User(MetadatosComunes, Base):
    __tablename__ = "usuarios"
    __table_args__ = (CheckConstraint("version >= 1", name="version_positive"),)
    id_usuario: Mapped[str] = mapped_column(String, primary_key=True)
    correo: Mapped[str] = mapped_column(String, unique=True)
    nombre: Mapped[str] = mapped_column(String)
    rol_id: Mapped[str] = mapped_column(ForeignKey("roles.id_rol"), index=True)
    estado: Mapped[str] = mapped_column(String, default="ACTIVO")
    ultimo_acceso: Mapped[str | None] = mapped_column(String)
    google_sub: Mapped[str | None] = mapped_column(String, unique=True)
    password_hash: Mapped[str | None] = mapped_column(String)
