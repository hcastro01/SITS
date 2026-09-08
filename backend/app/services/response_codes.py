"""Asignación atómica del identificador funcional de respuestas definitivas."""

from sqlalchemy import update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import EnvioFormulario, SecuenciaRespuestaFormulario

RESPONSE_CODE_PREFIX = "TTHH_RRLL_"
RESPONSE_SEQUENCE_NAME = "GLOBAL"
MAX_RESPONSE_SEQUENCE = 99_999_999_999


def format_response_code(sequence: int) -> str:
    if sequence < 1 or sequence > MAX_RESPONSE_SEQUENCE:
        raise ValueError("La secuencia de respuesta debe caber en 11 dígitos.")
    return f"{RESPONSE_CODE_PREFIX}{sequence:011d}"


def _next_sequence(session: Session) -> int:
    """Incrementa el único contador con una sentencia UPDATE atómica en SQLite."""
    if session.get_bind().dialect.name != "sqlite":
        raise AppError("UNSUPPORTED_DATABASE", "El correlativo requiere SQLite.", 500)
    session.execute(
        sqlite_insert(SecuenciaRespuestaFormulario)
        .values(nombre=RESPONSE_SEQUENCE_NAME, ultimo_numero=0)
        .on_conflict_do_nothing(index_elements=["nombre"])
    )
    sequence = session.scalar(
        update(SecuenciaRespuestaFormulario)
        .where(
            SecuenciaRespuestaFormulario.nombre == RESPONSE_SEQUENCE_NAME,
            SecuenciaRespuestaFormulario.ultimo_numero < MAX_RESPONSE_SEQUENCE,
        )
        .values(ultimo_numero=SecuenciaRespuestaFormulario.ultimo_numero + 1)
        .returning(SecuenciaRespuestaFormulario.ultimo_numero)
    )
    if sequence is None:
        raise AppError("RESPONSE_SEQUENCE_EXHAUSTED", "Se agotó el correlativo de respuestas.", 500)
    return int(sequence)


def assign_response_code(session: Session, response: EnvioFormulario) -> str:
    """Asigna una vez; una respuesta que ya tiene código jamás consume otro número."""
    if response.codigo_respuesta is not None or response.numero_secuencial is not None:
        if (response.codigo_respuesta is None or response.numero_secuencial is None
                or response.codigo_respuesta != format_response_code(response.numero_secuencial)):
            raise AppError("INVALID_RESPONSE_CODE", "El código persistido de la respuesta es inconsistente.", 500)
        return response.codigo_respuesta
    sequence = _next_sequence(session)
    response.numero_secuencial = sequence
    response.codigo_respuesta = format_response_code(sequence)
    return response.codigo_respuesta
