"""CLI de reparación conjunta; por defecto sólo inspecciona la base configurada."""

from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy.engine import make_url

from app.db.session import SessionLocal
from app.services.catalog_role_admin_repair import (
    RepairAbort, apply_repair, inspect_repair, revert_repair,
)


def identify_target(session) -> Path:
    """Exige un SQLite existente; nunca crea una base para esta operación."""
    url = make_url(str(session.get_bind().url))
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        raise RepairAbort("La reparación requiere un archivo SQLite existente; memoria y otros motores no son válidos.")
    path = Path(url.database).expanduser().resolve()
    if not path.is_file():
        raise RepairAbort("La base SQLite configurada no existe; se aborta sin crear archivos.")
    return path


def _items(items: tuple[str, ...]) -> str:
    return ", ".join(items) if items else "ninguno"


def main() -> int:
    parser = argparse.ArgumentParser(description="Repara sólo cinco nodos y cuatro permisos ROLE_ADMIN.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="confirma la reparación dentro de una única transacción")
    mode.add_argument("--revert", metavar="CORRELATION_ID", help="revierte una ejecución efectiva concreta")
    args = parser.parse_args()
    try:
        with SessionLocal() as session:
            target = identify_target(session)
            print(f"Base objetivo verificada: {target}")
            if args.revert:
                result = revert_repair(session, args.revert)
                print("REVERSIÓN CONFIRMADA DESPUÉS DEL COMMIT")
                print(f"correlation_id: {result.correlation_id}")
                print(f"módulos eliminados: {_items(result.created_modules)}")
                print(f"permisos eliminados: {_items(result.created_permissions)}")
                return 0
            if args.apply:
                result = apply_repair(session)
                if not result.correlation_id:
                    print("EJECUCIÓN SIN CAMBIOS CONFIRMADOS: todas las filas autorizadas ya eran compatibles.")
                    return 0
                print("CAMBIOS CONFIRMADOS DESPUÉS DEL COMMIT")
                print(f"correlation_id: {result.correlation_id}")
                print(f"módulos creados: {_items(result.created_modules)}")
                print(f"permisos creados: {_items(result.created_permissions)}")
                return 0
            plan = inspect_repair(session)
            print("CAMBIOS PROPUESTOS (DRY-RUN, SOLO LECTURA)")
            print(f"módulos a crear: {_items(tuple(row['id_modulo'] for row in plan.missing_modules))}")
            print(f"permisos a crear: {_items(plan.missing_permissions)}")
            print("No se realizaron cambios ni se registró auditoría persistente.")
            return 0
    except RepairAbort as exc:
        print(f"EJECUCIÓN ABORTADA: {exc}")
        return 2
    except Exception as exc:  # no anuncia éxito si fallan flush, auditoría o commit
        print(f"EJECUCIÓN ABORTADA: {type(exc).__name__}.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
