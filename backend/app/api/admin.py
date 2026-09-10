"""Router de Administración: usuarios, roles y permisos."""

from typing import Literal

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, ConfigDict, StrictBool
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.permissions import AuthenticatedUser
from app.services.admin import create_user, list_administration, save_permission, save_user_role

router = APIRouter(prefix="/api/v1/admin", tags=["Administración"])


class CrearUsuarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correo: str
    nombre: str
    rol_id: str
    password: str


class ActualizarUsuarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rol_id: str
    estado: Literal["ACTIVO", "INACTIVO"] = "ACTIVO"
    expected_version: int


class DerechosRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    create: StrictBool | None = None
    read: StrictBool | None = None
    edit: StrictBool | None = None
    delete: StrictBool | None = None
    sensitive: StrictBool | None = None
    export: StrictBool | None = None


class ActualizarPermisoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    derechos: DerechosRequest
    expected_version: int


@router.get("/usuarios")
def listar(db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return list_administration(db, user)


@router.post("/usuarios", status_code=status.HTTP_201_CREATED)
def crear_usuario(
    payload: CrearUsuarioRequest, request: Request, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    return create_user(
        db, user, correo=payload.correo, nombre=payload.nombre, rol_id=payload.rol_id,
        password=payload.password, correlation_id=getattr(request.state, "correlation_id", ""),
    )


@router.patch("/usuarios/{id_usuario}")
def actualizar_usuario(
    id_usuario: str, payload: ActualizarUsuarioRequest, request: Request, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    return save_user_role(
        db, user, id_usuario, rol_id=payload.rol_id, estado=payload.estado,
        expected_version=payload.expected_version,
        correlation_id=getattr(request.state, "correlation_id", ""),
    )


@router.put("/roles/{rol_id}/permisos/{modulo}")
def actualizar_permiso(
    rol_id: str, modulo: str, payload: ActualizarPermisoRequest, request: Request,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    return save_permission(
        db, user, rol_id, modulo, derechos=payload.derechos.model_dump(exclude_none=True),
        expected_version=payload.expected_version,
        correlation_id=getattr(request.state, "correlation_id", ""),
    )
