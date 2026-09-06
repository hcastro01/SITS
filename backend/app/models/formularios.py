from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.security import Base, MetadatosComunes


class Formulario(MetadatosComunes, Base):
    """Config.gs:51 (Formularios), Fase 1 §4 línea 84."""

    __tablename__ = "formularios"
    __table_args__ = (CheckConstraint("version >= 1", name="version_positive"),)

    id_formulario: Mapped[str] = mapped_column(String, primary_key=True)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String)
    proceso: Mapped[str | None] = mapped_column(String)
    estado: Mapped[str | None] = mapped_column(String)
    responsable: Mapped[str | None] = mapped_column(String)
    fecha_publicacion: Mapped[str | None] = mapped_column(String)


class Pregunta(MetadatosComunes, Base):
    """Config.gs:52 (Preguntas), Fase 1 §4 línea 85.

    validacion y condicion_visibilidad son JSON serializado a TEXT (Fase 1 §4): la
    validación de su estructura ocurre en el servicio, no en la base de datos.
    """

    __tablename__ = "preguntas"
    __table_args__ = (CheckConstraint("version >= 1", name="version_positive"),)

    id_pregunta: Mapped[str] = mapped_column(String, primary_key=True)
    id_formulario: Mapped[str] = mapped_column(ForeignKey("formularios.id_formulario"), index=True, nullable=False)
    etiqueta: Mapped[str] = mapped_column(String, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String)
    tipo: Mapped[str | None] = mapped_column(String)
    obligatoria: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=False)
    orden: Mapped[int] = mapped_column(Integer, default=0)
    categoria: Mapped[str | None] = mapped_column(String)
    subcategoria: Mapped[str | None] = mapped_column(String)
    valor_predeterminado: Mapped[str | None] = mapped_column(String)
    texto_ayuda: Mapped[str | None] = mapped_column(String)
    visible: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=True)
    solo_lectura: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=False)
    longitud_maxima: Mapped[int | None] = mapped_column(Integer)
    validacion: Mapped[str | None] = mapped_column(String)
    sensibilidad: Mapped[str | None] = mapped_column(String)
    condicion_visibilidad: Mapped[str | None] = mapped_column(String)
    campo_dependiente: Mapped[str | None] = mapped_column(ForeignKey("preguntas.id_pregunta"), index=True)
    valor_dependiente: Mapped[str | None] = mapped_column(String)
    formula: Mapped[str | None] = mapped_column(String)


class OpcionPregunta(MetadatosComunes, Base):
    """Config.gs:53 (OpcionesPregunta), Fase 1 §4 línea 86."""

    __tablename__ = "opciones_pregunta"
    __table_args__ = (CheckConstraint("version >= 1", name="version_positive"),)

    id_opcion: Mapped[str] = mapped_column(String, primary_key=True)
    id_pregunta: Mapped[str] = mapped_column(ForeignKey("preguntas.id_pregunta"), index=True, nullable=False)
    valor: Mapped[str] = mapped_column(String, nullable=False)
    etiqueta: Mapped[str] = mapped_column(String, nullable=False)
    orden: Mapped[int] = mapped_column(Integer, default=0)
    id_catalogo: Mapped[str | None] = mapped_column(ForeignKey("catalogos.id_catalogo"), index=True)
    id_opcion_padre: Mapped[str | None] = mapped_column(ForeignKey("opciones_pregunta.id_opcion"), index=True)


class ReglaFormulario(MetadatosComunes, Base):
    """Config.gs:54 (ReglasFormulario), Fase 1 §4 línea 87.

    Fase 1 §4 línea 109: "Las reglas solo podrán enlazar preguntas del mismo formulario" —
    se valida en servicio; SQLite no puede expresar esa restricción cruzada por FK.
    """

    __tablename__ = "reglas_formulario"
    __table_args__ = (CheckConstraint("version >= 1", name="version_positive"),)

    id_regla: Mapped[str] = mapped_column(String, primary_key=True)
    id_formulario: Mapped[str] = mapped_column(ForeignKey("formularios.id_formulario"), index=True, nullable=False)
    id_pregunta_origen: Mapped[str] = mapped_column(ForeignKey("preguntas.id_pregunta"), index=True, nullable=False)
    operador: Mapped[str | None] = mapped_column(String)
    valor_comparacion: Mapped[str | None] = mapped_column(String)
    id_pregunta_destino: Mapped[str | None] = mapped_column(ForeignKey("preguntas.id_pregunta"), index=True)
    accion: Mapped[str | None] = mapped_column(String)
    mensaje: Mapped[str | None] = mapped_column(String)
    orden: Mapped[int] = mapped_column(Integer, default=0)
