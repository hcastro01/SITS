from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.security import Base, MetadatosComunes


class Atencion(MetadatosComunes, Base):
    """Config.gs:56 (Atenciones), Fase 1 §4 línea 90."""

    __tablename__ = "atenciones"
    __table_args__ = (CheckConstraint("version >= 1", name="version_positive"),)

    id_atencion: Mapped[str] = mapped_column(String, primary_key=True)
    fecha: Mapped[str | None] = mapped_column(String)
    hora: Mapped[str | None] = mapped_column(String)
    id_persona: Mapped[str | None] = mapped_column(ForeignKey("personas.id_persona"), index=True)
    colaborador: Mapped[str | None] = mapped_column(String)
    responsable: Mapped[str | None] = mapped_column(String)
    tipo_atencion: Mapped[str | None] = mapped_column(String)
    motivo: Mapped[str | None] = mapped_column(String)
    canal: Mapped[str | None] = mapped_column(String)
    gestion: Mapped[str | None] = mapped_column(String)
    resultado: Mapped[str | None] = mapped_column(String)
    requiere_seguimiento: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=False)
    genera_caso: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=False)
    observaciones: Mapped[str | None] = mapped_column(String)
    evidencias: Mapped[str | None] = mapped_column(String)
    estado: Mapped[str | None] = mapped_column(String)


class Novedad(MetadatosComunes, Base):
    """Config.gs:59 (Novedades), Fase 1 §4 línea 93."""

    __tablename__ = "novedades"
    __table_args__ = (CheckConstraint("version >= 1", name="version_positive"),)

    id_novedad: Mapped[str] = mapped_column(String, primary_key=True)
    fecha: Mapped[str | None] = mapped_column(String)
    hora: Mapped[str | None] = mapped_column(String)
    responsable: Mapped[str | None] = mapped_column(String)
    fuente: Mapped[str | None] = mapped_column(String)
    tipo: Mapped[str | None] = mapped_column(String)
    subtipo: Mapped[str | None] = mapped_column(String)
    area: Mapped[str | None] = mapped_column(String)
    turno: Mapped[str | None] = mapped_column(String)
    lugar: Mapped[str | None] = mapped_column(String)
    descripcion: Mapped[str | None] = mapped_column(String)
    impacto: Mapped[str | None] = mapped_column(String)
    prioridad: Mapped[str | None] = mapped_column(String)
    accion_inmediata: Mapped[str | None] = mapped_column(String)
    genera_atencion: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=False)
    genera_caso: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=False)
    estado: Mapped[str | None] = mapped_column(String)
    evidencias: Mapped[str | None] = mapped_column(String)


class Recorrido(MetadatosComunes, Base):
    """Config.gs:60 (Recorridos), Fase 1 §4 línea 94.

    personas_contactadas y novedades_detectadas quedan en TEXT: Fase 1 §4 señala
    explícitamente que su contenido real debe revisarse antes de tipar como numérico.
    """

    __tablename__ = "recorridos"
    __table_args__ = (CheckConstraint("version >= 1", name="version_positive"),)

    id_recorrido: Mapped[str] = mapped_column(String, primary_key=True)
    fecha: Mapped[str | None] = mapped_column(String)
    hora_inicio: Mapped[str | None] = mapped_column(String)
    hora_fin: Mapped[str | None] = mapped_column(String)
    responsable: Mapped[str | None] = mapped_column(String)
    planta: Mapped[str | None] = mapped_column(String)
    area: Mapped[str | None] = mapped_column(String)
    turno: Mapped[str | None] = mapped_column(String)
    objetivo: Mapped[str | None] = mapped_column(String)
    observaciones: Mapped[str | None] = mapped_column(String)
    personas_contactadas: Mapped[str | None] = mapped_column(String)
    novedades_detectadas: Mapped[str | None] = mapped_column(String)
    acciones: Mapped[str | None] = mapped_column(String)
    evidencias: Mapped[str | None] = mapped_column(String)


class HallazgoRecorrido(MetadatosComunes, Base):
    """Config.gs:61 (HallazgosRecorrido), Fase 1 §4 línea 95."""

    __tablename__ = "hallazgos_recorrido"
    __table_args__ = (CheckConstraint("version >= 1", name="version_positive"),)

    id_hallazgo: Mapped[str] = mapped_column(String, primary_key=True)
    id_recorrido: Mapped[str] = mapped_column(ForeignKey("recorridos.id_recorrido"), index=True, nullable=False)
    tipo_hallazgo: Mapped[str | None] = mapped_column(String)
    categoria: Mapped[str | None] = mapped_column(String)
    subcategoria: Mapped[str | None] = mapped_column(String)
    area: Mapped[str | None] = mapped_column(String)
    descripcion: Mapped[str | None] = mapped_column(String)
    prioridad: Mapped[str | None] = mapped_column(String)
    accion: Mapped[str | None] = mapped_column(String)
    genera_novedad: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=False)
    id_novedad: Mapped[str | None] = mapped_column(ForeignKey("novedades.id_novedad"), index=True)
    genera_caso: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=False)
    id_caso: Mapped[str | None] = mapped_column(ForeignKey("casos.id_caso"), index=True)
    estado: Mapped[str | None] = mapped_column(String)
