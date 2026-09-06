"""Mecanismo de sesión (Fase 1 §4 línea 105, Fase 1 §3). Tabla, cookie, expiración y
revocación reales — la única pieza deliberadamente temporal es CÓMO se verifica la
identidad antes de crear la sesión (ver app/api/auth.py: login de desarrollo por correo,
sin Google OIDC). Reemplazar esa verificación no debería requerir tocar este módulo.

El token nunca se guarda en claro: solo su hash SHA-256 (`token_hash`). El valor real
viaja únicamente en la cookie HttpOnly del navegador.
"""

import hashlib
import secrets
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.time import utc_now, utc_now_iso
from app.models import Sesion

COOKIE_NAME = "sits_session"


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(session: Session, id_usuario: str) -> str:
    """Crea la sesión y devuelve el token en claro (solo existe aquí y en la cookie)."""
    token = secrets.token_urlsafe(32)
    ahora = utc_now()
    expira = ahora + timedelta(hours=get_settings().session_ttl_hours)
    session.add(Sesion(
        id_sesion=str(uuid4()),
        token_hash=_hash_token(token),
        id_usuario=id_usuario,
        fecha_creacion=ahora.isoformat(),
        expira_en=expira.isoformat(),
    ))
    return token


def resolve_session_user_id(session: Session, token: str) -> str | None:
    """Devuelve id_usuario si el token es válido, vigente y no revocado; si no, None."""
    if not token:
        return None
    fila = session.scalar(select(Sesion).where(Sesion.token_hash == _hash_token(token)))
    if fila is None or fila.revocada_en is not None:
        return None
    if fila.expira_en < utc_now_iso():
        return None
    return fila.id_usuario


def revoke_session(session: Session, token: str) -> None:
    if not token:
        return
    fila = session.scalar(select(Sesion).where(Sesion.token_hash == _hash_token(token)))
    if fila is not None and fila.revocada_en is None:
        fila.revocada_en = utc_now_iso()
