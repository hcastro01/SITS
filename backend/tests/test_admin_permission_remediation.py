import io
import sys
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.db.session import build_engine
from app.models import Auditoria, Permission, Role
from app.services.admin_permission_remediation import (
    ALL_RIGHTS,
    ROLE_ADMIN,
    TARGET_MODULES,
    insert_missing_role_admin_permissions,
    missing_target_modules,
)


class RoleAdminPermissionRemediationTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.engine = build_engine(f"sqlite:///{self.directory.name}/test.db")
        self.original = db_session.engine
        db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")
        with Session(self.engine) as session, session.begin():
            session.add_all([
                Role(id_rol=ROLE_ADMIN, nombre="Administrador", descripcion=""),
                Role(id_rol="ROLE_OTHER", nombre="Otro", descripcion=""),
            ])
            session.flush()
            # Una fila existente con derechos falsos demuestra que no se actualiza.
            session.add(Permission(id_permiso="ROLE_ADMIN:PRODUCCION", rol_id=ROLE_ADMIN, modulo="PRODUCCION", puede_leer=False))
            session.add(Permission(id_permiso="ROLE_OTHER:OFICINA", rol_id="ROLE_OTHER", modulo="OFICINA", puede_leer=False))

    def tearDown(self):
        db_session.engine = self.original
        self.engine.dispose()
        self.directory.cleanup()

    def test_inspection_distinguishes_missing_rows_from_existing_false_rows(self):
        with Session(self.engine) as session:
            self.assertEqual(missing_target_modules(session), ("RIESGOS_TRABAJO", "AUSENTISMO", "ACCIDENTES", "OFICINA"))

    def test_inserts_only_missing_authorized_rows_with_full_rights_and_audit(self):
        with Session(self.engine) as session, session.begin():
            inserted = insert_missing_role_admin_permissions(session, correlation_id="test-remediation")
        self.assertEqual(inserted, ("RIESGOS_TRABAJO", "AUSENTISMO", "ACCIDENTES", "OFICINA"))
        with Session(self.engine) as session:
            admin = {row.modulo: row for row in session.scalars(select(Permission).where(Permission.rol_id == ROLE_ADMIN))}
            self.assertFalse(admin["PRODUCCION"].puede_leer)
            for module in inserted:
                self.assertEqual({field: getattr(admin[module], field) for field in ALL_RIGHTS}, ALL_RIGHTS)
            other = session.get(Permission, "ROLE_OTHER:OFICINA")
            self.assertFalse(other.puede_leer)
            audits = session.scalars(select(Auditoria).where(Auditoria.tabla == "permisos")).all()
            self.assertTrue(audits)
            self.assertTrue(all(row.usuario == "SYSTEM_MAINTENANCE" for row in audits))
            self.assertNotIn("PRODUCCION", {row.id_registro.removeprefix("ROLE_ADMIN:") for row in audits})

    def test_second_execution_is_idempotent(self):
        with Session(self.engine) as session, session.begin():
            first = insert_missing_role_admin_permissions(session, correlation_id="first")
        with Session(self.engine) as session, session.begin():
            second = insert_missing_role_admin_permissions(session, correlation_id="second")
        self.assertEqual(len(first), 4)
        self.assertEqual(second, ())
        with Session(self.engine) as session:
            count = session.scalar(select(func.count()).select_from(Permission).where(
                Permission.rol_id == ROLE_ADMIN, Permission.modulo.in_(TARGET_MODULES),
            ))
            self.assertEqual(count, len(TARGET_MODULES))

    def test_cli_without_apply_only_inspects_and_does_not_write(self):
        from app.cli.remediate_role_admin_permissions import main

        with Session(self.engine) as session:
            before_permissions = session.scalar(select(func.count()).select_from(Permission))
            before_audits = session.scalar(select(func.count()).select_from(Auditoria))

        output = io.StringIO()
        with patch("app.cli.remediate_role_admin_permissions.SessionLocal", return_value=Session(self.engine)), \
             patch.object(sys, "argv", ["remediate_role_admin_permissions"]), \
             patch("sys.stdout", output):
            main()

        self.assertIn("ROLE_ADMIN filas ausentes: RIESGOS_TRABAJO, AUSENTISMO, ACCIDENTES, OFICINA", output.getvalue())
        self.assertIn("No se realizaron cambios", output.getvalue())
        with Session(self.engine) as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(Permission)), before_permissions)
            self.assertEqual(session.scalar(select(func.count()).select_from(Auditoria)), before_audits)

    def test_cli_apply_uses_one_real_transaction_and_is_idempotent(self):
        """El --apply no puede hacer un SELECT que active autobegin antes de begin()."""
        from app.cli.remediate_role_admin_permissions import main

        # La fila falsa existe sólo para el caso de inspección; esta regresión parte de los cinco objetivos ausentes.
        with Session(self.engine) as session, session.begin():
            session.delete(session.get(Permission, "ROLE_ADMIN:PRODUCCION"))

        first_output = io.StringIO()
        with patch("app.cli.remediate_role_admin_permissions.SessionLocal", return_value=Session(self.engine)), \
             patch.object(sys, "argv", ["remediate_role_admin_permissions", "--apply"]), \
             patch("sys.stdout", first_output):
            self.assertIsNone(main())

        expected = "RIESGOS_TRABAJO, AUSENTISMO, ACCIDENTES, PRODUCCION, OFICINA"
        self.assertIn(f"ROLE_ADMIN filas insertadas: {expected}", first_output.getvalue())
        with Session(self.engine) as session:
            admin = {row.modulo: row for row in session.scalars(select(Permission).where(Permission.rol_id == ROLE_ADMIN))}
            self.assertEqual(set(admin), set(TARGET_MODULES))
            for module in TARGET_MODULES:
                self.assertEqual({field: getattr(admin[module], field) for field in ALL_RIGHTS}, ALL_RIGHTS)
            audits = session.scalars(select(Auditoria).where(
                Auditoria.correlation_id == "maintenance:role-admin-missing-permissions",
            )).all()
            self.assertEqual(len(audits), len(TARGET_MODULES) * (len(ALL_RIGHTS) + 2))
            self.assertTrue(all(row.usuario == "SYSTEM_MAINTENANCE" for row in audits))
            self.assertEqual({row.id_registro for row in audits}, {
                f"{ROLE_ADMIN}:{module}" for module in TARGET_MODULES
            })

        second_output = io.StringIO()
        with patch("app.cli.remediate_role_admin_permissions.SessionLocal", return_value=Session(self.engine)), \
             patch.object(sys, "argv", ["remediate_role_admin_permissions", "--apply"]), \
             patch("sys.stdout", second_output):
            self.assertIsNone(main())
        self.assertIn("ROLE_ADMIN filas insertadas: ninguna", second_output.getvalue())
        with Session(self.engine) as session:
            audits = session.scalars(select(Auditoria).where(
                Auditoria.correlation_id == "maintenance:role-admin-missing-permissions",
            )).all()
            self.assertEqual(len(audits), len(TARGET_MODULES) * (len(ALL_RIGHTS) + 2))


if __name__ == "__main__":
    unittest.main()
