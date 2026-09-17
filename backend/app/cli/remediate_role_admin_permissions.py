"""CLI explícita para la remediación puntual de ROLE_ADMIN.

Ejemplo (sólo después de respaldo y autorización):
``python -m app.cli.remediate_role_admin_permissions --apply``
"""

import argparse

from app.db.session import SessionLocal
from app.services.admin_permission_remediation import (
    ROLE_ADMIN,
    insert_missing_role_admin_permissions,
    missing_target_modules,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inserta sólo permisos faltantes autorizados para ROLE_ADMIN.")
    parser.add_argument("--apply", action="store_true", help="confirma la transacción; sin esta bandera sólo inspecciona")
    args = parser.parse_args()
    with SessionLocal() as session:
        if not args.apply:
            missing = missing_target_modules(session)
            print(f"ROLE_ADMIN filas ausentes: {', '.join(missing) if missing else 'ninguna'}")
            print("No se realizaron cambios. Use --apply únicamente con autorización explícita.")
            return
        with session.begin():
            inserted = insert_missing_role_admin_permissions(
                session, correlation_id="maintenance:role-admin-missing-permissions",
            )
        print(f"ROLE_ADMIN filas insertadas: {', '.join(inserted) if inserted else 'ninguna'}")


if __name__ == "__main__":
    main()
