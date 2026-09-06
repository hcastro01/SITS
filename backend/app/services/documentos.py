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
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, authorize
from app.core.time import utc_now_iso
from app.models import (
    Atencion, Caso, Cierre, Compromiso, Derivacion, Documento, HallazgoRecorrido, Novedad, Persona, Recorrido,
    Seguimiento,
)
from app.services.audit import log_change
from app.services.records import apply_soft_delete, check_expected_version, get_active, mark_updated
from app.services.sensitivity import is_sensitive_record

MODULE = "DOCUMENTOS"
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_FILES_PER_RECORD = 10

ALLOWED_EXTENSIONS = frozenset({"jpg", "jpeg", "png", "pdf", "doc", "docx", "xls", "xlsx"})
ALLOWED_MIME_TYPES = frozenset({
    "image/jpeg", "image/png", "application/pdf", "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
})

# (modelo, módulo de permisos, nombre del campo id) por tipo_registro admitido.
TIPO_REGISTRO_MODELOS: dict[str, tuple[type, str, str]] = {
    "PERSONAS": (Persona, "PERSONAS", "id_persona"),
    "ATENCIONES": (Atencion, "ATENCIONES", "id_atencion"),
    "CASOS": (Caso, "CASOS", "id_caso"),
    "NOVEDADES": (Novedad, "NOVEDADES", "id_novedad"),
    "RECORRIDOS": (Recorrido, "RECORRIDOS", "id_recorrido"),
    "HALLAZGOS_RECORRIDO": (HallazgoRecorrido, "RECORRIDOS", "id_hallazgo"),
    "SEGUIMIENTOS": (Seguimiento, "SEGUIMIENTOS", "id_seguimiento"),
    "DERIVACIONES": (Derivacion, "DERIVACIONES", "id_derivacion"),
    "COMPROMISOS": (Compromiso, "COMPROMISOS", "id_compromiso"),
    "CIERRES": (Cierre, "CASOS", "id_cierre"),
}

_FIRMAS: dict[str, tuple[bytes, ...]] = {
    "jpg": (b"\xff\xd8\xff",), "jpeg": (b"\xff\xd8\xff",),
    "png": (b"\x89PNG\r\n\x1a\n",),
    "pdf": (b"%PDF-",),
    "doc": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",), "xls": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
    "docx": (b"PK\x03\x04",), "xlsx": (b"PK\x03\x04",),
}

_NOMBRE_INVALIDO = re.compile(r'[\x00-\x1f\x7f\\/:*?"<>|]')


def _nombre_seguro(nombre: str) -> str:
    limpio = _NOMBRE_INVALIDO.sub("_", (nombre or "")).replace("..", "_").strip()
    return limpio[:200] or "archivo"


def _firma_valida(contenido: bytes, extension: str) -> bool:
    firmas = _FIRMAS.get(extension)
    return bool(firmas) and any(contenido.startswith(firma) for firma in firmas)


def _resolver_registro_padre(session: Session, tipo_registro: str, id_registro: str):
    tipo = (tipo_registro or "").strip().upper()
    entrada = TIPO_REGISTRO_MODELOS.get(tipo)
    if entrada is None:
        raise AppError("INVALID_ENTITY", f"Tipo de registro no admitido: {tipo_registro!r}.", 422)
    modelo, modulo, id_field = entrada
    registro = get_active(session, modelo, id_registro, getattr(modelo, id_field))
    return registro, modulo, tipo


def upload_documento(
    session: Session, user: AuthenticatedUser, *,
    tipo_registro: str, id_registro: str, nombre_archivo: str, mime_type: str, contenido: bytes,
    categoria_documento: str | None = None, correlation_id: str = "",
) -> Documento:
    registro_padre, modulo, tipo = _resolver_registro_padre(session, tipo_registro, id_registro)
    sensible = is_sensitive_record(session, registro_padre)
    authorize(user, modulo, "edit", sensitive=sensible)
    authorize(user, MODULE, "create", sensitive=sensible)

    if len(contenido) > MAX_FILE_BYTES:
        raise AppError("FILE_TOO_LARGE", "El archivo supera el tamaño máximo permitido.", 422)

    extension = nombre_archivo.rsplit(".", 1)[-1].lower() if "." in nombre_archivo else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise AppError("INVALID_FILE_TYPE", "Extensión de archivo no permitida.", 422)
    if mime_type not in ALLOWED_MIME_TYPES:
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


def list_documentos(session: Session, user: AuthenticatedUser, *, tipo_registro: str, id_registro: str) -> list[Documento]:
    registro_padre, modulo, tipo = _resolver_registro_padre(session, tipo_registro, id_registro)
    sensible = is_sensitive_record(session, registro_padre)
    authorize(user, modulo, "read", sensitive=sensible)
    authorize(user, MODULE, "read", sensitive=sensible)
    return list(session.scalars(
        select(Documento).where(
            Documento.tipo_registro == tipo, Documento.id_registro == id_registro,
            Documento.eliminado.is_(False),
        )
    ))


def download_documento(session: Session, user: AuthenticatedUser, id_archivo: str, *, correlation_id: str = "") -> tuple[Documento, bytes]:
    documento = get_active(session, Documento, id_archivo, Documento.id_archivo)
    registro_padre, modulo, _tipo = _resolver_registro_padre(session, documento.tipo_registro, documento.id_registro)
    sensible = is_sensitive_record(session, registro_padre)
    authorize(user, modulo, "read", sensitive=sensible)
    authorize(user, MODULE, "read", sensitive=sensible)
    log_change(session, "documentos", id_archivo, "DOWNLOAD_FILE", {}, {}, user.correo,
               "Descarga de documento", correlation_id, sensitive_record=sensible)
    return documento, zlib.decompress(documento.contenido_comprimido)


def soft_delete_documento(
    session: Session, user: AuthenticatedUser, id_archivo: str, *,
    expected_version: int | None, motivo: str, correlation_id: str = "",
) -> Documento:
    documento = get_active(session, Documento, id_archivo, Documento.id_archivo)
    registro_padre, modulo, _tipo = _resolver_registro_padre(session, documento.tipo_registro, documento.id_registro)
    sensible = is_sensitive_record(session, registro_padre)
    authorize(user, modulo, "edit", sensitive=sensible)
    authorize(user, MODULE, "delete", sensitive=sensible)
    check_expected_version(documento, expected_version)
    before = {"nombre_archivo": documento.nombre_archivo}
    apply_soft_delete(documento, user.correo, motivo)
    mark_updated(documento, user.correo)
    log_change(session, "documentos", id_archivo, "DELETE", before, {"nombre_archivo": documento.nombre_archivo},
               user.correo, motivo, correlation_id, sensitive_record=sensible)
    return documento
