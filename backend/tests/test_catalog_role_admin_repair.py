import io
import sys
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.core.permissions import can, resolve_current_user
from app.db.session import build_engine
from app.models import Auditoria, ModuloSistema, Permission, Role, User
from app.services.catalog_role_admin_repair import (
    ALL_RIGHTS, CATALOG_TARGETS, PERMISSION_TARGETS, ROLE_ADMIN, RepairAbort,
    apply_repair, inspect_repair, revert_repair,
)


def module_from(definition):
    return ModuloSistema(**definition, activo=True, eliminado=False, version=1)


def admin_permission(module):
    return Permission(
        id_permiso=f"{ROLE_ADMIN}:{module}", rol_id=ROLE_ADMIN, modulo=module,
        **ALL_RIGHTS, activo=True, eliminado=False, version=1,
    )


class CatalogRoleAdminRepairTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.engine = build_engine(f"sqlite:///{self.directory.name}/repair.db")
        self.original_engine = db_session.engine
        db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")
        with Session(self.engine) as session, session.begin():
            session.add_all([
                Role(id_rol=ROLE_ADMIN, nombre="Administrador", activo=True, eliminado=False, version=1),
                Role(id_rol="ROLE_OTHER", nombre="Otro", activo=True, eliminado=False, version=1),
                ModuloSistema(id_modulo="sits-trabajo-social", nombre="Trabajo Social", activo=True, eliminado=False, version=1),
            ])
            session.flush()
            session.add_all([
                ModuloSistema(id_modulo="sits-actividades", nombre="Actividades", permiso="ACTIVIDADES", icono="✓", padre_id_modulo="sits-trabajo-social", orden=20, activo=True, eliminado=False, version=1),
                ModuloSistema(id_modulo="sits-oficina", nombre="Oficina", icono="▣", padre_id_modulo="sits-trabajo-social", orden=50, activo=True, eliminado=False, version=1),
                ModuloSistema(id_modulo="ajeno", nombre="Ajeno", permiso="AJENO", ruta="/ajeno", activo=True, eliminado=False, version=1),
            ])
            session.flush()
            session.add_all([
                admin_permission("OFICINA"),
                Permission(id_permiso="ROLE_OTHER:AJENO", rol_id="ROLE_OTHER", modulo="AJENO", puede_leer=True, activo=True, eliminado=False, version=1),
                User(id_usuario="admin", correo="admin@example.com", nombre="Admin", rol_id=ROLE_ADMIN, estado="ACTIVO", activo=True, eliminado=False, version=1),
                User(id_usuario="other", correo="other@example.com", nombre="Other", rol_id="ROLE_OTHER", estado="ACTIVO", activo=True, eliminado=False, version=1),
            ])

    def tearDown(self):
        db_session.engine = self.original_engine
        self.engine.dispose()
        self.directory.cleanup()

    def counts(self):
        with Session(self.engine) as session:
            return (
                session.scalar(select(func.count()).select_from(ModuloSistema)),
                session.scalar(select(func.count()).select_from(Permission)),
                session.scalar(select(func.count()).select_from(Auditoria)),
            )

    def test_creates_exactly_five_modules_four_permissions_and_audits(self):
        before = self.counts()
        with Session(self.engine) as session:
            result = apply_repair(session)
        self.assertTrue(result.correlation_id)
        self.assertEqual(len(result.created_modules), 5)
        self.assertEqual(result.created_permissions, PERMISSION_TARGETS)
        self.assertEqual(self.counts(), (before[0] + 5, before[1] + 4, before[2] + 98))
        with Session(self.engine) as session:
            for definition in CATALOG_TARGETS:
                row = session.get(ModuloSistema, definition["id_modulo"])
                self.assertEqual(row.nombre, definition["nombre"])
                self.assertEqual(row.permiso, definition["permiso"])
                self.assertEqual(row.ruta, definition["ruta"])
                self.assertEqual(row.icono, definition["icono"])
                self.assertEqual(row.padre_id_modulo, definition["padre_id_modulo"])
                self.assertEqual((row.orden, row.activo, row.eliminado, row.version), (definition["orden"], True, False, 1))
            for module in PERMISSION_TARGETS:
                row = session.get(Permission, f"{ROLE_ADMIN}:{module}")
                self.assertEqual({field: getattr(row, field) for field in ALL_RIGHTS}, ALL_RIGHTS)
                self.assertEqual((row.activo, row.eliminado, row.version), (True, False, 1))
            audits = session.scalars(select(Auditoria).where(Auditoria.correlation_id == result.correlation_id)).all()
            self.assertEqual(len(audits), 98)
            self.assertEqual({row.accion for row in audits}, {"CREATE"})

    def test_second_execution_is_idempotent_and_preserves_unrelated_rows(self):
        with Session(self.engine) as session:
            apply_repair(session)
        before = self.counts()
        with Session(self.engine) as session:
            result = apply_repair(session)
        self.assertEqual(result.correlation_id, None)
        self.assertEqual(self.counts(), before)
        with Session(self.engine) as session:
            self.assertEqual(session.get(ModuloSistema, "ajeno").ruta, "/ajeno")
            self.assertTrue(session.get(Permission, "ROLE_OTHER:AJENO").puede_leer)
            self.assertTrue(session.get(Permission, f"{ROLE_ADMIN}:OFICINA").puede_exportar)

    def test_partial_state_only_inserts_remaining_rows(self):
        with Session(self.engine) as session, session.begin():
            session.add(module_from(CATALOG_TARGETS[0]))
            session.add(admin_permission("ACTIVIDADES"))
        with Session(self.engine) as session:
            result = apply_repair(session)
        self.assertEqual(result.created_modules, tuple(row["id_modulo"] for row in CATALOG_TARGETS[1:]))
        self.assertEqual(result.created_permissions, PERMISSION_TARGETS[1:])
        self.assertEqual(self.counts()[2], 76)

    def test_conflicts_abort_without_changes(self):
        with Session(self.engine) as session, session.begin():
            bad = module_from(CATALOG_TARGETS[0])
            bad.icono = "X"
            session.add(bad)
        before = self.counts()
        with Session(self.engine) as session:
            with self.assertRaisesRegex(RepairAbort, "incompatible"):
                apply_repair(session)
        self.assertEqual(self.counts(), before)

    def test_missing_or_inactive_prerequisites_abort_without_changes(self):
        cases = ("role", "office", "parent")
        for case in cases:
            with self.subTest(case=case):
                with Session(self.engine) as session, session.begin():
                    if case == "role":
                        session.get(Role, ROLE_ADMIN).activo = False
                    elif case == "office":
                        session.get(Permission, f"{ROLE_ADMIN}:OFICINA").activo = False
                    else:
                        session.get(ModuloSistema, "sits-oficina").activo = False
                before = self.counts()
                with Session(self.engine) as session:
                    with self.assertRaises(RepairAbort):
                        inspect_repair(session)
                self.assertEqual(self.counts(), before)
                with Session(self.engine) as session, session.begin():
                    if case == "role":
                        session.get(Role, ROLE_ADMIN).activo = True
                    elif case == "office":
                        session.get(Permission, f"{ROLE_ADMIN}:OFICINA").activo = True
                    else:
                        session.get(ModuloSistema, "sits-oficina").activo = True

    def test_audit_or_commit_failure_rolls_back_and_never_announces_success(self):
        import app.services.catalog_role_admin_repair as repair

        original_log = repair.log_change
        calls = 0
        def broken_audit(*args, **kwargs):
            nonlocal calls
            calls += 1
            original_log(*args, **kwargs)
            if calls == 2:
                raise RuntimeError("audit failure")

        with Session(self.engine) as session, patch.object(repair, "log_change", side_effect=broken_audit):
            with self.assertRaisesRegex(RuntimeError, "audit failure"):
                apply_repair(session)
        self.assertEqual(self.counts()[2], 0)
        self.assertEqual(self.counts()[:2], (4, 2))

        session = Session(self.engine)
        def broken_commit(_session):
            raise RuntimeError("commit failure")
        event.listen(session, "before_commit", broken_commit)
        try:
            with self.assertRaisesRegex(RuntimeError, "commit failure"):
                apply_repair(session)
        finally:
            event.remove(session, "before_commit", broken_commit)
            session.close()
        self.assertEqual(self.counts()[2], 0)
        self.assertEqual(self.counts()[:2], (4, 2))

    def test_dry_run_cli_is_read_only_and_apply_prints_only_post_commit_summary(self):
        from app.cli.repair_catalog_role_admin import main

        before = self.counts()
        output = io.StringIO()
        with patch("app.cli.repair_catalog_role_admin.SessionLocal", return_value=Session(self.engine)), \
             patch.object(sys, "argv", ["repair_catalog_role_admin"]), patch("sys.stdout", output):
            self.assertEqual(main(), 0)
        self.assertIn("CAMBIOS PROPUESTOS", output.getvalue())
        self.assertEqual(self.counts(), before)

        output = io.StringIO()
        with patch("app.cli.repair_catalog_role_admin.SessionLocal", return_value=Session(self.engine)), \
             patch.object(sys, "argv", ["repair_catalog_role_admin", "--apply"]), patch("sys.stdout", output):
            self.assertEqual(main(), 0)
        self.assertIn("CAMBIOS CONFIRMADOS DESPUÉS DEL COMMIT", output.getvalue())

    def test_reversal_is_precise_and_blocks_modified_or_new_dependencies(self):
        with Session(self.engine) as session:
            result = apply_repair(session)
        with Session(self.engine) as session:
            reverted = revert_repair(session, result.correlation_id)
        self.assertEqual(len(reverted.created_modules), 5)
        self.assertEqual(self.counts()[:2], (4, 2))
        with Session(self.engine) as session:
            actions = set(session.scalars(select(Auditoria.accion).where(Auditoria.correlation_id == result.correlation_id)))
            self.assertEqual(actions, {"CREATE", "DELETE"})

        with Session(self.engine) as session:
            result = apply_repair(session)
        with Session(self.engine) as session, session.begin():
            session.get(ModuloSistema, "sits-beneficios").nombre = "Modificado"
        with Session(self.engine) as session:
            with self.assertRaisesRegex(RepairAbort, "incompatible"):
                revert_repair(session, result.correlation_id)
        with Session(self.engine) as session, session.begin():
            session.get(ModuloSistema, "sits-beneficios").nombre = "Beneficios"
            session.add(ModuloSistema(id_modulo="hijo-posterior", nombre="Hijo posterior", padre_id_modulo="sits-beneficios", activo=True, eliminado=False, version=1))
        with Session(self.engine) as session:
            with self.assertRaisesRegex(RepairAbort, "módulo hijo posterior"):
                revert_repair(session, result.correlation_id)
        with Session(self.engine) as session, session.begin():
            session.delete(session.get(ModuloSistema, "hijo-posterior"))
            session.add(Permission(id_permiso="ROLE_OTHER:BENEFICIOS", rol_id="ROLE_OTHER", modulo="BENEFICIOS", puede_leer=True, activo=True, eliminado=False, version=1))
        with Session(self.engine) as session:
            with self.assertRaisesRegex(RepairAbort, "dependiente"):
                revert_repair(session, result.correlation_id)

    def test_repair_grants_menu_permissions_without_changing_oficina_api_permission_or_other_role(self):
        with Session(self.engine) as session:
            apply_repair(session)
        with Session(self.engine) as session:
            admin = resolve_current_user(session, "admin@example.com")
            other = resolve_current_user(session, "other@example.com")
        for module in PERMISSION_TARGETS:
            self.assertTrue(can(admin, module, "read"))
            self.assertTrue(can(admin, module, "create"))
            self.assertFalse(can(other, module, "read"))
        self.assertTrue(can(admin, "OFICINA", "read"))
        self.assertFalse(can(other, "OFICINA", "read"))


if __name__ == "__main__":
    unittest.main()
