"""Servicio de Documentos. Equivalente a Base Sistema/DriveService.gs, con
almacenamiento en BLOB comprimido de SQLite en vez de Google Drive — decisión explícita
del usuario ("que los archivos esten en blob sqlite y comprimidos para bajar el
espacio"), en vez del almacenamiento privado en disco que proponía MIGRACION_FASE_1.md.

Controles preservados del legacy: extensión + MIME + firma binaria
(DriveService.gs:51-63), tamaño máximo por archivo y máximo de archivos por registro
(Config.gs:20-21), saneo de nombre de archivo (safeFileName), y autorización AND —el
módulo del registro padre Y DOCUMENTOS— nunca el OR de SearchService.gs (hallazgo de
Fase 1 §6).

tipo_registro/id_registro son una referencia polimórfica: no hay FK real, se valida la
existencia del registro padre en el servicio (Fase 1 §4 línea 109).
"""

import hashlib
import re
import zlib
from urllib.parse import quote
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.config import get_settings
from app.core.permissions import AuthenticatedUser, authorize
from app.core.time import utc_now_iso
from app.models import (
    Atencion, Beneficio, Caso, Cierre, Compromiso, Derivacion, Documento, EnvioFormulario,
    HallazgoRecorrido, Novedad, Persona, Prestamo, Recorrido, Seguimiento, Seguro,
)
from app.services.audit import log_change
from app.services.records import apply_soft_delete, check_expected_version, get_active, mark_updated
from app.services.sensitivity import is_sensitive_record

MODULE = "DOCUMENTOS"
MAX_FILE_BYTES = get_settings().max_upload_bytes
MAX_FILES_PER_RECORD = get_settings().max_documents_per_record

# La primera whitelist BLOB aprobada es deliberadamente pequeña. La relación
# extensión--MIME evita aceptar, por ejemplo, un PDF presentado como JPEG.
MIME_BY_EXTENSION = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "webp": "image/webp", "pdf": "application/pdf",
}
ALLOWED_EXTENSIONS = frozenset(MIME_BY_EXTENSION)
ALLOWED_MIME_TYPES = frozenset(MIME_BY_EXTENSION.values())

# (modelo, módulo de permisos, nombre del campo id) por tipo_registro admitido.
TIPO_REGISTRO_MODELOS: dict[str, tuple[type, str, str]] = {
    "PERSONAS": (Persona, "PERSONAS", "id_persona"),
    "ATENCIONES": (Atencion, "ATENCIONES", "id_atencion"),
    "BENEFICIOS": (Beneficio, "BENEFICIOS", "id_beneficio"),
    "PRESTAMOS": (Prestamo, "PRESTAMOS", "id_prestamo"),
    "SEGUROS": (Seguro, "SEGUROS", "id_seguro"),
    "CASOS": (Caso, "CASOS", "id_caso"),
    "NOVEDADES": (Novedad, "NOVEDADES", "id_novedad"),
    "RECORRIDOS": (Recorrido, "RECORRIDOS", "id_recorrido"),
    "HALLAZGOS_RECORRIDO": (HallazgoRecorrido, "RECORRIDOS", "id_hallazgo"),
    "SEGUIMIENTOS": (Seguimiento, "SEGUIMIENTOS", "id_seguimiento"),
    "DERIVACIONES": (Derivacion, "DERIVACIONES", "id_derivacion"),
    "COMPROMISOS": (Compromiso, "COMPROMISOS", "id_compromiso"),
    "CIERRES": (Cierre, "CASOS", "id_cierre"),
    "RESPUESTAS_FORMULARIO": (EnvioFormulario, "RESPUESTAS", "id_respuesta"),
}

_FIRMAS: dict[str, tuple[bytes, ...]] = {
    "jpg": (b"\xff\xd8\xff",), "jpeg": (b"\xff\xd8\xff",),
    "png": (b"\x89PNG\r\n\x1a\n",), "webp": (b"RIFF",),
    "pdf": (b"%PDF-",),
}

_NOMBRE_INVALIDO = re.compile(r'[\x00-\x1f\x7f\\/:*?"<>|]')


def _nombre_seguro(nombre: str) -> str:
    limpio = _NOMBRE_INVALIDO.sub("_", (nombre or "")).replace("..", "_").strip()
    return limpio[:200] or "archivo"


def _firma_valida(contenido: bytes, extension: str) -> bool:
    if extension == "webp":
        return contenido.startswith(b"RIFF") and contenido[8:12] == b"WEBP"
    firmas = _FIRMAS.get(extension)
    return bool(firmas) and any(contenido.startswith(firma) for firma in firmas)


def content_response_headers(nombre_archivo: str) -> dict[str, str]:
    """Cabeceras uniformes para contenido privado, nunca cacheable públicamente."""
    return {
        "Cache-Control": "private, no-store",
        "Pragma": "no-cache",
        "X-Content-Type-Options": "nosniff",
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(_nombre_seguro(nombre_archivo))}",
    }


def _resolver_registro_padre(session: Session, tipo_registro: str, id_registro: str):
    tipo = (tipo_registro or "").strip().upper()
    entrada = TIPO_REGISTRO_MODELOS.get(tipo)
    if entrada is None:
        raise AppError("INVALID_ENTITY", f"Tipo de registro no admitido: {tipo_registro!r}.", 422)
    modelo, modulo, id_field = entrada
    registro = get_active(session, modelo, id_registro, getattr(modelo, id_field))
    return registro, modulo, tipo


def _autorizar_propietario_respuesta(user: AuthenticatedUser, registro_padre) -> None:
    """Una respuesta solo admite documentos de su autor o de un administrador."""
    if (isinstance(registro_padre, EnvioFormulario)
            and registro_padre.usuario_respuesta != user.correo
            and user.rol_id != "ROLE_ADMIN"):
        raise AppError("FORBIDDEN", "No tiene permisos sobre los archivos de esta respuesta.", 403)


def upload_documento(
    session: Session, user: AuthenticatedUser, *,
    tipo_registro: str, id_registro: str, nombre_archivo: str, mime_type: str, contenido: bytes,
    categoria_documento: str | None = None, correlation_id: str = "", parent_module: str | None = None,
) -> Documento:
    registro_padre, modulo, tipo = _resolver_registro_padre(session, tipo_registro, id_registro)
    _autorizar_propietario_respuesta(user, registro_padre)
    sensible = is_sensitive_record(session, registro_padre)
    authorize(user, parent_module or modulo, "edit", sensitive=sensible)
    authorize(user, MODULE, "create", sensitive=sensible)

    if len(contenido) > MAX_FILE_BYTES:
        raise AppError("FILE_TOO_LARGE", "El archivo supera el tamaño máximo permitido.", 422)

    extension = nombre_archivo.rsplit(".", 1)[-1].lower() if "." in nombre_archivo else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise AppError("INVALID_FILE_TYPE", "Extensión de archivo no permitida.", 422)
    if mime_type != MIME_BY_EXTENSION.get(extension):
        raise AppError("INVALID_FILE_TYPE", "Tipo MIME no permitido.", 422)
    if not _firma_valida(contenido, extension):
        raise AppError("FILE_SIGNATURE_MISMATCH", "El contenido del archivo no coincide con su extensión.", 422)

    total_actual = session.scalar(
        select(func.count()).select_from(Documento).where(
            Documento.tipo_registro == tipo, Documento.id_registro == id_registro,
            Documento.eliminado.is_(False),
        )
    )
    if total_actual >= MAX_FILES_PER_RECORD:
        raise AppError("TOO_MANY_FILES", "Se alcanzó el máximo de archivos para este registro.", 422)

    comprimido = zlib.compress(contenido, level=9)
    ahora = utc_now_iso()
    documento = Documento(
        id_archivo=str(uuid4()), tipo_registro=tipo, id_registro=id_registro,
        nombre_archivo=_nombre_seguro(nombre_archivo), mime_type=mime_type, extension=extension,
        tamano_bytes=len(contenido), tamano_comprimido_bytes=len(comprimido),
        contenido_comprimido=comprimido, sha256=hashlib.sha256(contenido).hexdigest(),
        categoria_documento=categoria_documento,
        fecha_creacion=ahora, creado_por=user.correo,
    )
    session.add(documento)
    session.flush()
    log_change(
        session, "documentos", documento.id_archivo, "CREATE", {},
        {"nombre_archivo": documento.nombre_archivo, "tipo_registro": tipo, "id_registro": id_registro,
         "tamano_bytes": documento.tamano_bytes, "sha256": documento.sha256},
        user.correo, "Carga de documento", correlation_id, sensitive_record=sensible,
    )
    return documento


def list_documentos(session: Session, user: AuthenticatedUser, *, tipo_registro: str, id_registro: str,
                    parent_module: str | None = None) -> list[Documento]:
    registro_padre, modulo, tipo = _resolver_registro_padre(session, tipo_registro, id_registro)
    _autorizar_propietario_respuesta(user, registro_padre)
    sensible = is_sensitive_record(session, registro_padre)
    authorize(user, parent_module or modulo, "read", sensitive=sensible)
    authorize(user, MODULE, "read", sensitive=sensible)
    return list(session.scalars(
        select(Documento).where(
            Documento.tipo_registro == tipo, Documento.id_registro == id_registro,
            Documento.eliminado.is_(False),
        )
    ))


def download_documento(session: Session, user: AuthenticatedUser, id_archivo: str, *, correlation_id: str = "",
                       parent_module: str | None = None) -> tuple[Documento, bytes]:
    documento = get_active(session, Documento, id_archivo, Documento.id_archivo)
    registro_padre, modulo, _tipo = _resolver_registro_padre(session, documento.tipo_registro, documento.id_registro)
    _autorizar_propietario_respuesta(user, registro_padre)
    sensible = is_sensitive_record(session, registro_padre)
    authorize(user, parent_module or modulo, "read", sensitive=sensible)
    authorize(user, MODULE, "read", sensitive=sensible)
    if not documento.contenido_comprimido:
        raise AppError("DOCUMENT_CONTENT_UNAVAILABLE", "El documento histórico no tiene contenido recuperable.", 404)
    try:
        contenido = zlib.decompress(documento.contenido_comprimido)
    except zlib.error as error:
        raise AppError("DOCUMENT_CONTENT_CORRUPTED", "El contenido del documento no puede recuperarse.", 422) from error
    log_change(session, "documentos", id_archivo, "DOWNLOAD_FILE", {}, {}, user.correo,
               "Descarga de documento", correlation_id, sensitive_record=sensible)
    return documento, contenido


def soft_delete_documento(
    session: Session, user: AuthenticatedUser, id_archivo: str, *,
    expected_version: int | None, motivo: str, correlation_id: str = "", parent_module: str | None = None,
) -> Documento:
    documento = get_active(session, Documento, id_archivo, Documento.id_archivo)
    registro_padre, modulo, _tipo = _resolver_registro_padre(session, documento.tipo_registro, documento.id_registro)
    _autorizar_propietario_respuesta(user, registro_padre)
    sensible = is_sensitive_record(session, registro_padre)
    authorize(user, parent_module or modulo, "edit", sensitive=sensible)
    authorize(user, MODULE, "delete", sensitive=sensible)
    check_expected_version(documento, expected_version)
    before = {"nombre_archivo": documento.nombre_archivo}
    apply_soft_delete(documento, user.correo, motivo)
    mark_updated(documento, user.correo)
    log_change(session, "documentos", id_archivo, "DELETE", before, {"nombre_archivo": documento.nombre_archivo},
               user.correo, motivo, correlation_id, sensitive_record=sensible)
    return documento
