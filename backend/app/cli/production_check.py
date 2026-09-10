"""Comprobaciones de solo lectura previas a publicar el backend."""

import argparse
from dataclasses import dataclass
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings, get_settings
from app.models import User

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    detail: str


def expected_head(alembic_ini: Path = ALEMBIC_INI) -> str:
    return ScriptDirectory.from_config(Config(str(alembic_ini))).get_current_head()


def run_checks(settings: Settings, database_engine: Engine) -> list[CheckResult]:
    results: list[CheckResult] = []

    results.append(
        CheckResult(
            "configuración",
            "ok" if settings.environment == "production" else "error",
            "entorno de producción activo"
            if settings.environment == "production"
            else "ENVIRONMENT no es production",
        )
    )

    database_url = make_url(settings.database_url)
    database_path = Path(database_url.database).expanduser().resolve() if database_url.database else None
    is_persistent_sqlite = bool(
        database_url.get_backend_name() == "sqlite"
        and database_path
        and database_url.database != ":memory:"
        and database_path.is_file()
    )
    results.append(
        CheckResult(
            "almacenamiento",
            "ok" if is_persistent_sqlite else "error",
            "archivo SQLite persistente disponible"
            if is_persistent_sqlite
            else "el archivo SQLite configurado no existe",
        )
    )

    try:
        with database_engine.connect() as connection:
            quick_check = connection.exec_driver_sql("PRAGMA quick_check").scalar_one()
            foreign_key_errors = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchmany(10)
            current_revision = connection.exec_driver_sql(
                "SELECT version_num FROM alembic_version"
            ).scalar_one()
            journal_mode = connection.exec_driver_sql("PRAGMA journal_mode").scalar_one().lower()

        results.append(
            CheckResult(
                "integridad SQLite",
                "ok" if quick_check == "ok" and not foreign_key_errors else "error",
                "quick_check y claves foráneas correctos"
                if quick_check == "ok" and not foreign_key_errors
                else "SQLite reportó errores de integridad",
            )
        )
        results.append(
            CheckResult(
                "migraciones",
                "ok" if current_revision == expected_head() else "error",
                "esquema en la revisión vigente"
                if current_revision == expected_head()
                else "el esquema no coincide con la revisión vigente",
            )
        )
        results.append(
            CheckResult(
                "modo SQLite",
                "ok" if journal_mode == settings.sqlite_journal_mode else "warning",
                f"journal_mode={journal_mode}",
            )
        )

        with database_engine.connect() as connection:
            active_admins = connection.execute(
                select(func.count())
                .select_from(User)
                .where(
                    User.rol_id == "ROLE_ADMIN",
                    User.estado == "ACTIVO",
                    User.eliminado.is_(False),
                    User.password_hash.is_not(None),
                )
            ).scalar_one()
            users_without_password = connection.execute(
                select(func.count())
                .select_from(User)
                .where(
                    User.estado == "ACTIVO",
                    User.eliminado.is_(False),
                    User.password_hash.is_(None),
                )
            ).scalar_one()

        results.append(
            CheckResult(
                "administración",
                "ok" if active_admins else "error",
                "existe un administrador activo con contraseña"
                if active_admins
                else "no existe un administrador activo con contraseña",
            )
        )
        results.append(
            CheckResult(
                "credenciales de usuarios",
                "ok" if users_without_password == 0 else "warning",
                "todos los usuarios activos tienen contraseña"
                if users_without_password == 0
                else f"{users_without_password} usuario(s) activo(s) aún no tienen contraseña",
            )
        )
    except (SQLAlchemyError, OSError, ValueError) as exc:
        results.append(CheckResult("base de datos", "error", f"comprobación fallida: {type(exc).__name__}"))

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Valida que el backend esté listo para producción.")
    parser.parse_args()
    settings = get_settings()
    database = make_url(settings.database_url)
    database_path = Path(database.database).expanduser().resolve() if database.database else None
    if (
        database.get_backend_name() != "sqlite"
        or database.database == ":memory:"
        or database_path is None
        or not database_path.is_file()
    ):
        print("[ERROR] almacenamiento: el archivo SQLite configurado no existe")
        raise SystemExit(1)

    # Importar después de comprobar la ruta evita que la construcción del motor cree
    # accidentalmente un directorio o una base vacía durante este diagnóstico.
    from app.db.session import engine

    results = run_checks(settings, engine)
    for result in results:
        marker = {"ok": "OK", "warning": "AVISO", "error": "ERROR"}[result.status]
        print(f"[{marker}] {result.name}: {result.detail}")
    if any(result.status == "error" for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
