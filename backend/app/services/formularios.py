"""Servicio de Formularios (Config.gs:51, Fase 1 §4 línea 84).

`estado` nunca se acepta en create()/update(): solo change_status() lo cambia, y exige al
menos una pregunta activa para publicar (Base Sistema/FormService.gs:257-259). Preguntas,
OpcionesPregunta y ReglasFormulario no tienen esta protección de estado y usan la fábrica
genérica (app/services/preguntas.py, etc.).
"""

from app.core.time import utc_now_iso
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, authorize
from app.models import EnvioFormulario, Formulario, Pregunta
from app.services.audit import log_change
from app.services.records import apply_soft_delete, check_expected_version, creation_metadata, get_active, mark_updated

MODULE = "FORMULARIOS"
ESTADOS_VALIDOS = ("BORRADOR", "PUBLICADO", "INACTIVO", "ARCHIVADO")
CAMPOS = ("nombre", "descripcion", "proceso", "responsable", "permite_multiples_respuestas")


def _snapshot(record: Formulario) -> dict:
    return {campo: getattr(record, campo) for campo in (*CAMPOS, "estado", "fecha_publicacion", "version_publicada")}


def _deletion_snapshot(record: Formulario) -> dict:
    return {**_snapshot(record), "activo": record.activo, "eliminado": record.eliminado}


def _rechazar_desconocidos(campos: dict) -> None:
    desconocidos = set(campos) - set(CAMPOS)
    if desconocidos:
        raise AppError("INVALID_FIELD", f"Campos no admitidos: {', '.join(sorted(desconocidos))}.", 422)


def create_formulario(session: Session, user: AuthenticatedUser, *, motivo_auditoria: str,
                       correlation_id: str, destinos: list[str] | None = None, **campos) -> Formulario:
    _rechazar_desconocidos(campos)
    authorize(user, MODULE, "create")
    record = Formulario(id_formulario=str(uuid4()), estado="BORRADOR",
                         **creation_metadata(user.correo), **campos)
    session.add(record)
    session.flush()
    from app.services.form_builder import sync_destinations
    proceso = str(campos.get("proceso") or "").strip().upper()
    aliases = {"CASO": "CASOS", "ATENCION": "ATENCIONES", "NOVEDAD": "NOVEDADES",
               "RECORRIDO": "RECORRIDOS", "PERSONA": "PERSONAS"}
    sync_destinations(session, record.id_formulario, destinos or [aliases.get(proceso, proceso or "GENERAL")], user.correo)
    log_change(session, "formularios", record.id_formulario, "CREATE", {}, _snapshot(record),
               user.correo, motivo_auditoria, correlation_id)
    return record


def update_formulario(session: Session, user: AuthenticatedUser, id_formulario: str, *,
                       expected_version: int | None, motivo_auditoria: str,
                       correlation_id: str, **campos) -> Formulario:
    _rechazar_desconocidos(campos)
    authorize(user, MODULE, "edit")
    record = get_active(session, Formulario, id_formulario, Formulario.id_formulario)
    check_expected_version(record, expected_version)
    before = _snapshot(record)
    for campo, valor in campos.items():
        setattr(record, campo, valor)
    mark_updated(record, user.correo)
    log_change(session, "formularios", id_formulario, "UPDATE", before, _snapshot(record),
               user.correo, motivo_auditoria, correlation_id)
    return record


def change_status(session: Session, user: AuthenticatedUser, id_formulario: str, nuevo_estado: str, *,
                   expected_version: int | None, correlation_id: str) -> Formulario:
    """Equivalente a Base Sistema/FormService.gs:252-265 (changeStatus)."""
    authorize(user, MODULE, "edit")
    estado_normalizado = (nuevo_estado or "").strip().upper()
    if estado_normalizado not in ESTADOS_VALIDOS:
        raise AppError("INVALID_FORM_STATUS", "Estado de formulario inválido.", 422)
    record = get_active(session, Formulario, id_formulario, Formulario.id_formulario)
    check_expected_version(record, expected_version)
    if estado_normalizado == "PUBLICADO":
        total_preguntas = session.scalar(
            select(func.count()).select_from(Pregunta).where(
                Pregunta.id_formulario == id_formulario,
                Pregunta.eliminado.is_(False),
                Pregunta.activo.is_(True),
            )
        )
        if not total_preguntas:
            raise AppError("FORM_WITHOUT_QUESTIONS", "Agregue al menos una pregunta antes de publicar.", 422)
        from app.services.form_builder import create_version, get_definition
        if not get_definition(session, id_formulario)["destinos"]:
            raise AppError("FORM_WITHOUT_DESTINATIONS", "Seleccione al menos un módulo de destino.", 422)
    before = _snapshot(record)
    record.estado = estado_normalizado
    record.fecha_publicacion = utc_now_iso() if estado_normalizado == "PUBLICADO" else None
    record.activo = estado_normalizado != "ARCHIVADO"
    mark_updated(record, user.correo)
    if estado_normalizado == "PUBLICADO":
        create_version(session, record, user)
    log_change(session, "formularios", id_formulario, "UPDATE", before, _snapshot(record),
               user.correo, f"Cambio de estado a {estado_normalizado}", correlation_id)
    return record


def soft_delete_formulario(session: Session, user: AuthenticatedUser, id_formulario: str, *,
                           expected_version: int | None, motivo: str,
                           correlation_id: str) -> Formulario:
    authorize(user, MODULE, "delete")
    record = get_active(session, Formulario, id_formulario, Formulario.id_formulario)
    check_expected_version(record, expected_version)
    if record.estado == "PUBLICADO":
        raise AppError(
            "PUBLISHED_FORM_DELETE_FORBIDDEN",
            "Debe despublicar el formulario antes de eliminarlo.",
            409,
        )
    response_count = session.scalar(
        select(func.count()).select_from(EnvioFormulario).where(
            EnvioFormulario.id_formulario == id_formulario,
        )
    ) or 0
    if response_count:
        raise AppError(
            "FORM_HAS_RESPONSES",
            "Este formulario no puede eliminarse porque contiene respuestas registradas. "
            "Puede archivarlo para conservar su historial.",
            409,
        )
    before = _deletion_snapshot(record)
    apply_soft_delete(record, user.correo, motivo)
    mark_updated(record, user.correo)
    log_change(
        session, "formularios", id_formulario, "DELETE", before, _deletion_snapshot(record),
        user.correo, motivo, correlation_id,
    )
    return record
