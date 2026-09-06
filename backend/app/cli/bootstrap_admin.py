"""Comando administrativo de arranque. Equivalente restringido a Base Sistema/Setup.gs:36-43.

No expone HTTP: se invoca desde la línea de comandos del servidor, nunca desde la API
(MIGRACION_FASE_1.md §5: "No exponer runSetup como endpoint público"). A diferencia del
legacy, el correo y el nombre los indica explícitamente el operador — no se infiere de una
sesión activa de Google, y el nombre nunca se rellena con el correo.
"""

import argparse
from getpass import getpass
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import Role, User
from app.services.passwords import hash_password

ADMIN_ROLE_ID = "ROLE_ADMIN"


class AdminAlreadyBootstrapped(RuntimeError):
    """Ya existe al menos un usuario; el arranque debe venir de la migración de cuentas."""


def bootstrap_admin(session: Session, correo: str, nombre: str, password: str | None = None) -> User:
    if session.scalars(select(User.id_usuario).limit(1)).first() is not None:
        raise AdminAlreadyBootstrapped(
            "Ya existen usuarios registrados. El primer administrador solo se crea sobre una "
            "base vacía; use la migración de cuentas existentes para instalaciones en marcha."
        )
    if session.get(Role, ADMIN_ROLE_ID) is None:
        raise LookupError(
            f"El rol {ADMIN_ROLE_ID} no existe todavía. Ejecute la siembra de seguridad "
            "(seed_security) antes de crear el primer administrador."
        )
    correo_normalizado = correo.strip().lower()
    nombre_normalizado = nombre.strip()
    if not correo_normalizado or not nombre_normalizado:
        raise ValueError("correo y nombre son obligatorios y no pueden estar en blanco.")
    user = User(
        id_usuario=str(uuid4()),
        correo=correo_normalizado,
        nombre=nombre_normalizado,
        rol_id=ADMIN_ROLE_ID,
        estado="ACTIVO",
        password_hash=hash_password(password) if password else None,
    )
    session.add(user)
    session.flush()
    return user


def main() -> None:
    parser = argparse.ArgumentParser(description="Crea el primer administrador. Falla si ya hay usuarios.")
    parser.add_argument("--correo", required=True, help="Correo del administrador inicial.")
    parser.add_argument("--nombre", required=True, help="Nombre real de la persona, no el correo.")
    args = parser.parse_args()
    password = getpass("Contraseña inicial (mínimo 12 caracteres): ")
    confirmation = getpass("Repita la contraseña: ")
    if password != confirmation:
        raise ValueError("Las contraseñas no coinciden.")
    with SessionLocal.begin() as session:
        user = bootstrap_admin(session, correo=args.correo, nombre=args.nombre, password=password)
        print(f"Administrador creado: {user.id_usuario} ({user.correo})")


if __name__ == "__main__":
    main()
