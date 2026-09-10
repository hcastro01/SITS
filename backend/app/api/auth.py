"""Endpoints de sesión con contraseña en producción y modo explícito de desarrollo."""

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, resolve_current_user
from app.models import User
from app.services.passwords import hash_password, verify_password
from app.services.login_throttle import LoginThrottle, login_key
from app.services.sessions import COOKIE_NAME, create_session, revoke_session

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticación"])

# Igualar el coste de un correo inexistente con el de una contraseña incorrecta reduce
# la señal temporal que permitiría enumerar cuentas válidas.
_DUMMY_PASSWORD_HASH = hash_password("VerificacionTemporal123")
login_throttle = LoginThrottle()


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correo: str = Field(min_length=3, max_length=254)
    password: str | None = Field(default=None, max_length=1024)


class UsuarioActual(BaseModel):
    id_usuario: str
    correo: str
    nombre: str
    rol_id: str
    rol_nombre: str
    permisos: dict[str, dict[str, bool]]


def _usuario_actual(user: AuthenticatedUser) -> UsuarioActual:
    return UsuarioActual(id_usuario=user.id_usuario, correo=user.correo, nombre=user.nombre,
                          rol_id=user.rol_id, rol_nombre=user.rol_nombre, permisos=user.permisos)


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=COOKIE_NAME, value=token, httponly=True, secure=settings.cookie_secure,
        samesite=settings.cookie_samesite, path="/", max_age=settings.session_ttl_hours * 3600,
    )


@router.post("/login", response_model=UsuarioActual)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> UsuarioActual:
    settings = get_settings()
    throttle_key = login_key(payload.correo)
    if settings.auth_mode == "password":
        login_throttle.ensure_allowed(
            throttle_key,
            max_attempts=getattr(settings, "login_max_attempts", 5),
            window_seconds=getattr(settings, "login_window_seconds", 300),
        )
    try:
        user = resolve_current_user(db, payload.correo)
    except AppError:
        if settings.auth_mode == "password":
            verify_password(payload.password or "", _DUMMY_PASSWORD_HASH)
            login_throttle.register_failure(
                throttle_key, window_seconds=getattr(settings, "login_window_seconds", 300),
            )
            raise AppError("INVALID_CREDENTIALS", "Correo o contraseña incorrectos.", 401) from None
        raise
    if settings.auth_mode == "password":
        db_user = db.get(User, user.id_usuario)
        if not payload.password or db_user is None or not verify_password(payload.password, db_user.password_hash):
            login_throttle.register_failure(
                throttle_key, window_seconds=getattr(settings, "login_window_seconds", 300),
            )
            raise AppError("INVALID_CREDENTIALS", "Correo o contraseña incorrectos.", 401)
        login_throttle.clear(throttle_key)
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
