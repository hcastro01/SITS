"""Endpoints de sesión con contraseña en producción y modo explícito de desarrollo."""

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, resolve_current_user
from app.models import User
from app.services.passwords import verify_password
from app.services.sessions import COOKIE_NAME, create_session, revoke_session

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticación"])


class LoginRequest(BaseModel):
    correo: str
    password: str | None = None


class UsuarioActual(BaseModel):
    id_usuario: str
    correo: str
    nombre: str
    rol_id: str
    rol_nombre: str


def _usuario_actual(user: AuthenticatedUser) -> UsuarioActual:
    return UsuarioActual(id_usuario=user.id_usuario, correo=user.correo, nombre=user.nombre,
                          rol_id=user.rol_id, rol_nombre=user.rol_nombre)


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=COOKIE_NAME, value=token, httponly=True, secure=settings.cookie_secure,
        samesite=settings.cookie_samesite, path="/", max_age=settings.session_ttl_hours * 3600,
    )


@router.post("/login", response_model=UsuarioActual)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> UsuarioActual:
    settings = get_settings()
    try:
        user = resolve_current_user(db, payload.correo)
    except AppError:
        if settings.auth_mode == "password":
            raise AppError("INVALID_CREDENTIALS", "Correo o contraseña incorrectos.", 401) from None
        raise
    if settings.auth_mode == "password":
        db_user = db.get(User, user.id_usuario)
        if not payload.password or db_user is None or not verify_password(payload.password, db_user.password_hash):
            raise AppError("INVALID_CREDENTIALS", "Correo o contraseña incorrectos.", 401)
    token = create_session(db, user.id_usuario)
    _set_session_cookie(response, token)
    return _usuario_actual(user)


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    token = request.cookies.get(COOKIE_NAME)
    if token:
        revoke_session(db, token)
    settings = get_settings()
    response.delete_cookie(COOKIE_NAME, path="/", secure=settings.cookie_secure, samesite=settings.cookie_samesite)
    return {"status": "ok"}


@router.get("/me", response_model=UsuarioActual)
def me(user: AuthenticatedUser = Depends(get_current_user)) -> UsuarioActual:
    return _usuario_actual(user)
