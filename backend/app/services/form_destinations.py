"""Catálogo jerárquico y asignaciones de destinos de Formularios."""

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, authorize
from app.core.time import utc_now_iso
from app.models import DestinoFormulario, EnvioFormulario, Formulario, FormularioDestino
from app.services.audit import log_change
from app.services.records import creation_metadata, get_active, mark_updated
from app.services.response_contexts import response_action_allowed

MODULE = "FORMULARIOS"
ROOT_CODE = "TRABAJO_SOCIAL"
LEAF_LEVEL = "SUBPROCESO"

# IDs independientes de los módulos y de los textos históricos de formulario_destinos.
DESTINOS_INICIALES = (
    ("destino-trabajo-social", "TRABAJO_SOCIAL", "Trabajo Social", "MACROPROCESO", None, 10),
    ("destino-actividades", "ACTIVIDADES", "Actividades", "PROCESO", "destino-trabajo-social", 20),
    ("destino-actividades-general", "ACTIVIDADES_GENERAL", "General", "SUBPROCESO", "destino-actividades", 21),
    ("destino-departamento-medico", "DEPARTAMENTO_MEDICO", "Departamento Médico", "PROCESO", "destino-trabajo-social", 30),
    ("destino-riesgos-trabajo", "RIESGOS_TRABAJO", "Riesgos de trabajo", "SUBPROCESO", "destino-departamento-medico", 31),
    ("destino-ausentismos", "AUSENTISMOS", "Ausentismos", "SUBPROCESO", "destino-departamento-medico", 32),
    ("destino-accidentes", "ACCIDENTES", "Accidentes", "SUBPROCESO", "destino-departamento-medico", 33),
    ("destino-produccion", "PRODUCCION", "Producción", "PROCESO", "destino-trabajo-social", 40),
    ("destino-produccion-atenciones", "PRODUCCION_ATENCIONES", "Atenciones", "SUBPROCESO", "destino-produccion", 41),
    ("destino-recorridos", "RECORRIDOS", "Recorridos", "SUBPROCESO", "destino-produccion", 42),
    ("destino-novedades-planta", "NOVEDADES_PLANTA", "Novedades de planta", "SUBPROCESO", "destino-produccion", 43),
    ("destino-oficina", "OFICINA", "Oficina", "PROCESO", "destino-trabajo-social", 50),
    ("destino-beneficios", "BENEFICIOS", "Beneficios", "SUBPROCESO", "destino-oficina", 51),
    ("destino-oficina-atenciones", "OFICINA_ATENCIONES", "Atenciones", "SUBPROCESO", "destino-oficina", 52),
    ("destino-prestamos", "PRESTAMOS", "Préstamos", "SUBPROCESO", "destino-oficina", 53),
    ("destino-seguro", "SEGURO", "Seguro", "SUBPROCESO", "destino-oficina", 54),
)


def seed_form_destinations(session: Session) -> None:
    """Inserta únicamente códigos ausentes; nunca reescribe catálogo existente."""
    existing = set(session.scalars(select(DestinoFormulario.codigo)))
    for id_destino, codigo, nombre, nivel, padre_id_destino, orden in DESTINOS_INICIALES:
        if codigo not in existing:
            session.add(DestinoFormulario(
                id_destino=id_destino, codigo=codigo, nombre=nombre, nivel=nivel,
                padre_id_destino=padre_id_destino, orden=orden,
            ))


def _serialize(destination: DestinoFormulario, children: list[dict] | None = None) -> dict:
    return {
        "id_destino": destination.id_destino, "codigo": destination.codigo,
        "nombre": destination.nombre, "nivel": destination.nivel,
        "padre_id_destino": destination.padre_id_destino, "activo": destination.activo,
        "orden": destination.orden, "hijos": children or [],
    }


def list_destination_tree(session: Session, user: AuthenticatedUser, *, active_only: bool = True) -> list[dict]:
    authorize(user, MODULE, "read")
    rows = list(session.scalars(select(DestinoFormulario).where(
        DestinoFormulario.eliminado.is_(False),
        DestinoFormulario.activo.is_(True) if active_only else True,
    ).order_by(DestinoFormulario.orden, DestinoFormulario.codigo)))
    children: dict[str | None, list[DestinoFormulario]] = {}
    for row in rows:
        children.setdefault(row.padre_id_destino, []).append(row)

    def build(row: DestinoFormulario) -> dict:
        return _serialize(row, [build(child) for child in children.get(row.id_destino, [])])

    return [build(row) for row in children.get(None, [])]


def list_active_destinations(session: Session, user: AuthenticatedUser) -> list[dict]:
    authorize(user, MODULE, "read")
    return [_serialize(row) for row in session.scalars(select(DestinoFormulario).where(
        DestinoFormulario.nivel == LEAF_LEVEL, DestinoFormulario.activo.is_(True),
        DestinoFormulario.eliminado.is_(False),
    ).order_by(DestinoFormulario.orden, DestinoFormulario.codigo)) if _is_valid_branch(session, row)]


def _is_valid_branch(session: Session, destination: DestinoFormulario) -> bool:
    current = destination
    visited: set[str] = set()
    while current is not None:
        if current.id_destino in visited or current.eliminado or not current.activo:
            return False
        visited.add(current.id_destino)
        if current.padre_id_destino is None:
            return current.codigo == ROOT_CODE and current.nivel == "MACROPROCESO"
        current = session.get(DestinoFormulario, current.padre_id_destino)
    return False


def _get_assignable_destinations(session: Session, ids: list[str]) -> dict[str, DestinoFormulario]:
    normalized = [str(value).strip() for value in ids]
    if len(normalized) != len(set(normalized)):
        raise AppError("DUPLICATE_FORM_DESTINATION", "Un destino no puede asignarse dos veces.", 422)
    rows = {row.id_destino: row for row in session.scalars(select(DestinoFormulario).where(
        DestinoFormulario.id_destino.in_(normalized),
    ))}
    if len(rows) != len(normalized):
        raise AppError("FORM_DESTINATION_NOT_FOUND", "Uno o más destinos no existen.", 404)
    for row in rows.values():
        if row.nivel != LEAF_LEVEL or not _is_valid_branch(session, row):
            raise AppError("INVALID_FORM_DESTINATION", "Solo se pueden asignar subprocesos activos del árbol de Trabajo Social.", 422)
    return rows


def serialize_assignment(row: FormularioDestino, destination: DestinoFormulario) -> dict:
    return {
        "id_asignacion": row.id_destino, "id_formulario": row.id_formulario,
        "id_destino_catalogo": destination.id_destino, "activo": row.activo,
        "eliminado": row.eliminado, "version": row.version,
        "destino": _serialize(destination),
    }


def list_form_destinations(session: Session, user: AuthenticatedUser, form_id: str, *, include_inactive: bool = False) -> list[dict]:
    authorize(user, MODULE, "read")
    get_active(session, Formulario, form_id, Formulario.id_formulario)
    conditions = [FormularioDestino.id_formulario == form_id, FormularioDestino.id_destino_catalogo.is_not(None)]
    if not include_inactive:
        conditions.extend([FormularioDestino.activo.is_(True), FormularioDestino.eliminado.is_(False)])
    rows = list(session.scalars(select(FormularioDestino).where(*conditions)))
    return [serialize_assignment(row, session.get(DestinoFormulario, row.id_destino_catalogo)) for row in rows]


def set_form_destinations(session: Session, user: AuthenticatedUser, form_id: str, destination_ids: list[str], *, correlation_id: str = "") -> list[dict]:
    authorize(user, MODULE, "edit")
    get_active(session, Formulario, form_id, Formulario.id_formulario)
    requested = _get_assignable_destinations(session, destination_ids)
    existing = {row.id_destino_catalogo: row for row in session.scalars(select(FormularioDestino).where(
        FormularioDestino.id_formulario == form_id, FormularioDestino.id_destino_catalogo.is_not(None),
    ))}
    for destination_id, row in existing.items():
        enabled = destination_id in requested
        if row.activo != enabled or row.eliminado == enabled:
            before = {"id_destino_catalogo": destination_id, "activo": row.activo, "eliminado": row.eliminado}
            row.activo, row.eliminado = enabled, not enabled
            if not enabled:
                row.fecha_eliminacion, row.usuario_eliminacion = utc_now_iso(), user.correo
                row.motivo_eliminacion = "Retiro de destino jerárquico"
            else:
                row.fecha_eliminacion = row.usuario_eliminacion = row.motivo_eliminacion = None
            mark_updated(row, user.correo)
            log_change(session, "formulario_destinos", row.id_destino, "UPDATE", before,
                       {"id_destino_catalogo": destination_id, "activo": row.activo, "eliminado": row.eliminado},
                       user.correo, "Actualización de destino jerárquico", correlation_id)
    for destination_id, destination in requested.items():
        if destination_id not in existing:
            row = FormularioDestino(id_destino=str(uuid4()), id_formulario=form_id, modulo=destination.codigo,
                                    id_destino_catalogo=destination_id, **creation_metadata(user.correo))
            session.add(row)
            session.flush()
            log_change(session, "formulario_destinos", row.id_destino, "CREATE", {},
                       {"id_formulario": form_id, "id_destino_catalogo": destination_id, "activo": True},
                       user.correo, "Asignación de destino jerárquico", correlation_id)
    session.flush()
    return list_form_destinations(session, user, form_id)


def validate_response_destination(session: Session, form_id: str, destination_id: str | None) -> DestinoFormulario | None:
    if destination_id is None:
        return None
    destination = session.get(DestinoFormulario, destination_id)
    if destination is None:
        raise AppError("RESPONSE_DESTINATION_NOT_FOUND", "El destino de respuesta no existe.", 404)
    if destination.nivel != LEAF_LEVEL or not _is_valid_branch(session, destination):
        raise AppError("INVALID_RESPONSE_DESTINATION", "El destino de respuesta no está activo o no es un subproceso válido.", 422)
    assignment = session.scalar(select(FormularioDestino).where(
        FormularioDestino.id_formulario == form_id, FormularioDestino.id_destino_catalogo == destination_id,
        FormularioDestino.activo.is_(True), FormularioDestino.eliminado.is_(False),
    ))
    if assignment is None:
        raise AppError("RESPONSE_DESTINATION_NOT_ALLOWED", "El destino no está asignado al formulario.", 403)
    return destination


def list_destination_responses(session: Session, user: AuthenticatedUser, destination_id: str) -> list[EnvioFormulario]:
    authorize(user, "RESPUESTAS", "read")
    if session.get(DestinoFormulario, destination_id) is None:
        raise AppError("FORM_DESTINATION_NOT_FOUND", "El destino no existe.", 404)
    return [response for response in session.scalars(select(EnvioFormulario).where(
        EnvioFormulario.id_destino_respuesta == destination_id,
        EnvioFormulario.eliminado.is_(False),
    ).order_by(EnvioFormulario.fecha_respuesta.desc())) if response_action_allowed(session, user, response, "read")]
