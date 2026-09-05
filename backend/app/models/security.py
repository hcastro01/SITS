from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=True)


class Permission(Base):
    __tablename__ = "permisos"
    __table_args__ = (UniqueConstraint("role_id", "module"),)
    id: Mapped[str] = mapped_column(String, primary_key=True)
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"), index=True)
    module: Mapped[str] = mapped_column(String)
    can_create: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=False)
    can_read: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=False)
    can_edit: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=False)
    can_delete: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=False)
    can_sensitive: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=False)
    can_export: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=False)
    active: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=True)


class User(Base):
    __tablename__ = "usuarios"
    __table_args__ = (CheckConstraint("version >= 1"),)
    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String)
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"), index=True)
    google_sub: Mapped[str | None] = mapped_column(String, unique=True)
    active: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=True)
    deleted: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)

