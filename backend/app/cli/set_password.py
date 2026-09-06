"""Establece o rota una contraseña sin exponerla en argumentos ni registros."""

import argparse
from getpass import getpass

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import User
from app.services.passwords import hash_password


def main() -> None:
    parser = argparse.ArgumentParser(description="Establece la contraseña de un usuario existente.")
    parser.add_argument("--correo", required=True)
    args = parser.parse_args()
    password = getpass("Nueva contraseña (mínimo 12 caracteres): ")
    confirmation = getpass("Repita la contraseña: ")
    if password != confirmation:
        raise ValueError("Las contraseñas no coinciden.")
    with SessionLocal.begin() as session:
        user = session.scalar(select(User).where(User.correo == args.correo.strip().lower()))
        if user is None:
            raise LookupError("Usuario no encontrado.")
        user.password_hash = hash_password(password)
    print("Contraseña actualizada correctamente.")


if __name__ == "__main__":
    main()
