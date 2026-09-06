"""Guardado de respuestas de formulario. Equivalente simplificado a
Base Sistema/FormService.gs:389-441 (saveResponse).

Corrige el hallazgo de idempotencia de Fase 1 §6: la clave de idempotencia es
(usuario_respuesta, id_envio_cliente) — reforzada por UNIQUE en el esquema
(app/models/respuestas.py, EnvioFormulario) — no una clave global consultable por
cualquiera antes de comprobar propietario (Base Sistema/FormService.gs:418-421). La
búsqueda scoped por usuario hace que la comprobación de propietario sea innecesaria: nunca
se puede encontrar el envío de otra persona por esta vía.

Fuera de alcance de este incremento: motor de reglas de visibilidad/obligatoriedad,
validación de opciones por catálogo, campos calculados (SUM/CONCAT/TODAY) y validaciones
de formato (email/teléfono/regex). Se guardan los valores ya tipados que entrega el
llamador en `respuestas`.
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, authorize
from app.models import EnvioFormulario, Formulario, RespuestaFormulario
from app.services.records import creation_metadata, mark_updated

VALOR_CAMPOS = ("valor_texto", "valor_numero", "valor_fecha", "valor_booleano", "valor_opcion")


def _find_by_client_key(session: Session, usuario: str, id_envio_cliente: str) -> EnvioFormulario | None:
    return session.scalar(
        select(EnvioFormulario).where(
            EnvioFormulario.usuario_respuesta == usuario,
            EnvioFormulario.id_envio_cliente == id_envio_cliente,
        )
    )


def _retire_existing_details(session: Session, id_respuesta: str, usuario: str) -> None:
    existentes = session.scalars(
        select(RespuestaFormulario).where(
            RespuestaFormulario.id_respuesta == id_respuesta,
            RespuestaFormulario.eliminado.is_(False),
        )
    ).all()
    for fila in existentes:
        fila.activo = False
        fila.eliminado = True
        fila.fecha_eliminacion = datetime.now(UTC).isoformat()
        fila.usuario_eliminacion = usuario
        fila.motivo_eliminacion = "Nueva versión de respuesta"


def save_response(
    session: Session, user: AuthenticatedUser, id_formulario: str, *,
    draft: bool, respuestas: list[dict], id_envio_cliente: str | None = None,
    id_registro_proceso: str | None = None, correlation_id: str,
) -> EnvioFormulario:
    """`respuestas` es una lista de dicts `{id_pregunta, <uno de VALOR_CAMPOS>: valor}`."""
    authorize(user, "RESPUESTAS", "create")
    formulario = session.get(Formulario, id_formulario)
    if formulario is None or formulario.eliminado:
        raise AppError("FORM_NOT_FOUND", "Formulario no encontrado.", 404)
    if not draft and (formulario.estado or "").strip().upper() != "PUBLICADO":
        raise AppError("FORM_NOT_PUBLISHED", "El formulario no está publicado.", 422)
    if not respuestas:
        raise AppError("EMPTY_RESPONSE", "El formulario no contiene respuestas para guardar.", 422)

    envio = _find_by_client_key(session, user.correo, id_envio_cliente) if id_envio_cliente else None
    if envio is not None and not draft and (envio.estado or "").strip().upper() == "REGISTRADO":
        return envio  # idempotente: reenvío ya registrado con la misma clave, no se duplica.

    nuevo_estado = "BORRADOR" if draft else "REGISTRADO"
    if envio is None:
        envio = EnvioFormulario(
            id_respuesta=str(uuid4()), id_formulario=id_formulario, usuario_respuesta=user.correo,
            id_envio_cliente=id_envio_cliente, estado=nuevo_estado,
            fecha_respuesta=datetime.now(UTC).isoformat(), id_registro_proceso=id_registro_proceso,
            **creation_metadata(user.correo),
        )
        session.add(envio)
        session.flush()
    else:
        _retire_existing_details(session, envio.id_respuesta, user.correo)
        envio.estado = nuevo_estado
        envio.fecha_respuesta = datetime.now(UTC).isoformat()
        mark_updated(envio, user.correo)

    for respuesta in respuestas:
        id_pregunta = respuesta.get("id_pregunta")
        if not id_pregunta:
            raise AppError("INVALID_ANSWER", "Cada respuesta debe indicar id_pregunta.", 422)
        valores = {campo: respuesta[campo] for campo in VALOR_CAMPOS if campo in respuesta}
        session.add(RespuestaFormulario(
            id_detalle_respuesta=str(uuid4()), id_respuesta=envio.id_respuesta, id_pregunta=id_pregunta,
            **creation_metadata(user.correo), **valores,
        ))
    return envio
