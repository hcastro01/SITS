"""Dependencias FastAPI compartidas: sesión de base de datos por petición y usuario
vigente resuelto desde la cookie de sesión.
"""

from collections.abc import Generator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, resolve_current_user
from app.db.session import SessionLocal
from app.models import User
from app.services.sessions import COOKIE_NAME, resolve_session_user_id


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> AuthenticatedUser:
    token = request.cookies.get(COOKIE_NAME)
    id_usuario = resolve_session_user_id(db, token) if token else None
    if id_usuario is None:
        raise AppError("SESSION_REQUIRED", "Inicie sesión para continuar.", 401)
    user = db.get(User, id_usuario)
    if user is None:
        raise AppError("SESSION_REQUIRED", "Inicie sesión para continuar.", 401)
    return resolve_current_user(db, user.correo)
