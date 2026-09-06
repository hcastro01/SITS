from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.security import Base, MetadatosComunes


class Caso(MetadatosComunes, Base):
    """Config.gs:57 (Casos), Fase 1 §4 línea 91."""

    __tablename__ = "casos"
    __table_args__ = (
        Index("ix_casos_estado_caso_fecha_apertura", "estado_caso", "fecha_apertura"),
        CheckConstraint("version >= 1", name="version_positive"),
    )

    id_caso: Mapped[str] = mapped_column(String, primary_key=True)
    codigo_caso: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    fecha_apertura: Mapped[str | None] = mapped_column(String)
    id_persona: Mapped[str | None] = mapped_column(ForeignKey("personas.id_persona"), index=True)
    colaborador: Mapped[str | None] = mapped_column(String)
    responsable: Mapped[str | None] = mapped_column(String, index=True)
    tipo_caso: Mapped[str | None] = mapped_column(String)
    subtipo_caso: Mapped[str | None] = mapped_column(String)
    prioridad: Mapped[str | None] = mapped_column(String)
    nivel_sensibilidad: Mapped[str | None] = mapped_column(String)
    estado_caso: Mapped[str | None] = mapped_column(String)
    tipo_gestion: Mapped[str | None] = mapped_column(String)
    tipo_evento: Mapped[str | None] = mapped_column(String)
    area: Mapped[str | None] = mapped_column(String)
    turno: Mapped[str | None] = mapped_column(String)
    condicion_laboral: Mapped[str | None] = mapped_column(String)
    restriccion: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=False)
    fecha_inicio_restriccion: Mapped[str | None] = mapped_column(String)
    derivacion: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=False)
    ultimo_seguimiento: Mapped[str | None] = mapped_column(String)
    fecha_cierre: Mapped[str | None] = mapped_column(String)
    motivo_cierre: Mapped[str | None] = mapped_column(String)
    resultado: Mapped[str | None] = mapped_column(String)
    evidencias: Mapped[str | None] = mapped_column(String)


class DetalleCasoSensible(MetadatosComunes, Base):
    """Config.gs:58 (DetalleCasosSensibles), Fase 1 §4 línea 92. Relación 1:1 con Casos."""

    __tablename__ = "detalle_casos_sensibles"
    __table_args__ = (CheckConstraint("version >= 1", name="version_positive"),)

    id_detalle_sensible: Mapped[str] = mapped_column(String, primary_key=True)
    id_caso: Mapped[str] = mapped_column(ForeignKey("casos.id_caso"), unique=True, nullable=False)
    descripcion_sensible: Mapped[str | None] = mapped_column(String)
    antecedentes: Mapped[str | None] = mapped_column(String)
    diagnostico_social: Mapped[str | None] = mapped_column(String)
    intervencion: Mapped[str | None] = mapped_column(String)
    notas_privadas: Mapped[str | None] = mapped_column(String)


class Seguimiento(MetadatosComunes, Base):
    """Config.gs:62 (Seguimientos), Fase 1 §4 línea 96."""

    __tablename__ = "seguimientos"
    __table_args__ = (CheckConstraint("version >= 1", name="version_positive"),)

    id_seguimiento: Mapped[str] = mapped_column(String, primary_key=True)
    id_caso: Mapped[str] = mapped_column(ForeignKey("casos.id_caso"), index=True, nullable=False)
    fecha: Mapped[str | None] = mapped_column(String)
    hora: Mapped[str | None] = mapped_column(String)
    responsable: Mapped[str | None] = mapped_column(String)
    tipo_seguimiento: Mapped[str | None] = mapped_column(String)
    canal: Mapped[str | None] = mapped_column(String)
    tecnica: Mapped[str | None] = mapped_column(String)
    descripcion: Mapped[str | None] = mapped_column(String)
    resultado: Mapped[str | None] = mapped_column(String)
    proxima_accion: Mapped[str | None] = mapped_column(String)
    fecha_proxima_accion: Mapped[str | None] = mapped_column(String)
    estado: Mapped[str | None] = mapped_column(String)
    evidencias: Mapped[str | None] = mapped_column(String)


class Derivacion(MetadatosComunes, Base):
    """Config.gs:63 (Derivaciones), Fase 1 §4 línea 97."""

    __tablename__ = "derivaciones"
    __table_args__ = (CheckConstraint("version >= 1", name="version_positive"),)

    id_derivacion: Mapped[str] = mapped_column(String, primary_key=True)
    id_caso: Mapped[str] = mapped_column(ForeignKey("casos.id_caso"), index=True, nullable=False)
    fecha: Mapped[str | None] = mapped_column(String)
    area_destino: Mapped[str | None] = mapped_column(String)
    responsable_destino: Mapped[str | None] = mapped_column(String)
    motivo: Mapped[str | None] = mapped_column(String)
    estado: Mapped[str | None] = mapped_column(String)
    fecha_respuesta: Mapped[str | None] = mapped_column(String)
    resultado: Mapped[str | None] = mapped_column(String)
    fecha_cierre: Mapped[str | None] = mapped_column(String)
    observaciones: Mapped[str | None] = mapped_column(String)


class Compromiso(MetadatosComunes, Base):
    """Config.gs:64 (Compromisos), Fase 1 §4 línea 98."""

    __tablename__ = "compromisos"
    __table_args__ = (CheckConstraint("version >= 1", name="version_positive"),)

    id_compromiso: Mapped[str] = mapped_column(String, primary_key=True)
    id_caso: Mapped[str] = mapped_column(ForeignKey("casos.id_caso"), index=True, nullable=False)
    id_seguimiento: Mapped[str | None] = mapped_column(ForeignKey("seguimientos.id_seguimiento"), index=True)
    fecha_creacion_compromiso: Mapped[str | None] = mapped_column(String)
    responsable: Mapped[str | None] = mapped_column(String)
    descripcion: Mapped[str | None] = mapped_column(String)
    fecha_limite: Mapped[str | None] = mapped_column(String)
    estado: Mapped[str | None] = mapped_column(String)
    fecha_cumplimiento: Mapped[str | None] = mapped_column(String)
    evidencia: Mapped[str | None] = mapped_column(String)
    observacion: Mapped[str | None] = mapped_column(String)


class Cierre(MetadatosComunes, Base):
    """Config.gs:65 (Cierres), Fase 1 §4 línea 99."""

    __tablename__ = "cierres"
    __table_args__ = (CheckConstraint("version >= 1", name="version_positive"),)

    id_cierre: Mapped[str] = mapped_column(String, primary_key=True)
    id_caso: Mapped[str] = mapped_column(ForeignKey("casos.id_caso"), index=True, nullable=False)
    fecha_cierre_caso: Mapped[str | None] = mapped_column(String)
    responsable: Mapped[str | None] = mapped_column(String)
    motivo_cierre: Mapped[str | None] = mapped_column(String)
    resultado_final: Mapped[str | None] = mapped_column(String)
    evidencia: Mapped[str | None] = mapped_column(String)
    requiere_monitoreo: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=False)
    observacion: Mapped[str | None] = mapped_column(String)
