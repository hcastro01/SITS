"""Endpoints de sesión.

POST /login es DELIBERADAMENTE temporal: exige únicamente que el correo pertenezca a un
usuario registrado y activo, sin verificar identidad real (sin contraseña, sin Google
OIDC) — decisión explícita para poder construir y probar el frontend antes de cerrar
MIGRACION_FASE_1.md §10 (bloqueo B4: dominio Google, credenciales OAuth). El mecanismo de
sesión (cookie, tabla `sesiones`, expiración, revocación) es el definitivo: sustituir esta
verificación por Google OIDC no debería requerir tocar /logout, /me, ni
app/services/sessions.py.

NO USAR ESTE ENDPOINT TAL CUAL EN UN DESPLIEGUE REAL: cualquiera que conozca un correo
registrado puede iniciar sesión como esa persona.
"""

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import get_settings
from app.core.permissions import AuthenticatedUser, resolve_current_user
from app.services.sessions import COOKIE_NAME, create_session, revoke_session

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticación"])


class LoginRequest(BaseModel):
    correo: str


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
        samesite="lax", path="/", max_age=settings.session_ttl_hours * 3600,
    )


@router.post("/login", response_model=UsuarioActual)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> UsuarioActual:
    user = resolve_current_user(db, payload.correo)
    token = create_session(db, user.id_usuario)
    _set_session_cookie(response, token)
    return _usuario_actual(user)


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    token = request.cookies.get(COOKIE_NAME)
    if token:
        revoke_session(db, token)
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"status": "ok"}


@router.get("/me", response_model=UsuarioActual)
def me(user: AuthenticatedUser = Depends(get_current_user)) -> UsuarioActual:
    return _usuario_actual(user)
