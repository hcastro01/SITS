import unittest
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.core.errors import AppError
from app.core.permissions import resolve_current_user
from app.db.session import build_engine
from app.models import User
from app.services.admin import list_administration, save_permission, save_user_role
from app.services.security_seed import seed_security


class AdminServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.engine = build_engine(f"sqlite:///{self.directory.name}/test.db")
        self._original_engine = db_session.engine
        db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")
        with Session(self.engine) as session, session.begin():
            seed_security(session)
            session.add(User(id_usuario="admin1", correo="admin1@example.com", nombre="Admin Uno",
                              rol_id="ROLE_ADMIN", estado="ACTIVO"))
            session.add(User(id_usuario="ts", correo="ts@example.com", nombre="Trabajador",
                              rol_id="ROLE_TRABAJADOR_SOCIAL", estado="ACTIVO"))
            session.add(User(id_usuario="consulta", correo="consulta@example.com", nombre="Consulta",
                              rol_id="ROLE_CONSULTA", estado="ACTIVO"))

    def tearDown(self):
        db_session.engine = self._original_engine
        self.engine.dispose()
        self.directory.cleanup()

    def test_non_admin_cannot_list_administration(self):
        with Session(self.engine) as session:
            ts = resolve_current_user(session, "ts@example.com")
            with self.assertRaises(AppError) as ctx:
                list_administration(session, ts)
            self.assertEqual(ctx.exception.code, "FORBIDDEN")

    def test_admin_can_list_administration(self):
        with Session(self.engine) as session:
            admin = resolve_current_user(session, "admin1@example.com")
            datos = list_administration(session, admin)
            self.assertEqual(len(datos["roles"]), 5)
            self.assertEqual(len(datos["permisos"]), 90)
            self.assertEqual(len(datos["usuarios"]), 3)

    def test_cannot_demote_the_last_active_admin(self):
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin1@example.com")
            with self.assertRaises(AppError) as ctx:
                save_user_role(session, admin, "admin1", rol_id="ROLE_CONSULTA", estado="ACTIVO",
                                expected_version=1, correlation_id="c1")
            self.assertEqual(ctx.exception.code, "LAST_ADMIN")

    def test_cannot_deactivate_the_last_active_admin(self):
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin1@example.com")
            with self.assertRaises(AppError) as ctx:
                save_user_role(session, admin, "admin1", rol_id="ROLE_ADMIN", estado="INACTIVO",
                                expected_version=1, correlation_id="c1")
            self.assertEqual(ctx.exception.code, "LAST_ADMIN")

    def test_can_demote_admin_when_another_active_admin_exists(self):
        with Session(self.engine) as session, session.begin():
            session.add(User(id_usuario="admin2", correo="admin2@example.com", nombre="Admin Dos",
                              rol_id="ROLE_ADMIN", estado="ACTIVO"))
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin2@example.com")
            resultado = save_user_role(session, admin, "admin1", rol_id="ROLE_CONSULTA", estado="ACTIVO",
                                        expected_version=1, correlation_id="c1")
            self.assertEqual(resultado["rol_id"], "ROLE_CONSULTA")

    def test_non_admin_cannot_reassign_roles(self):
        with Session(self.engine) as session, session.begin():
            consulta = resolve_current_user(session, "consulta@example.com")
            with self.assertRaises(AppError) as ctx:
                save_user_role(session, consulta, "ts", rol_id="ROLE_ADMIN", estado="ACTIVO",
                                expected_version=1, correlation_id="c1")
            self.assertEqual(ctx.exception.code, "FORBIDDEN")

    def test_cannot_strip_core_admin_permission(self):
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin1@example.com")
            with self.assertRaises(AppError) as ctx:
                save_permission(session, admin, "ROLE_ADMIN", "ADMINISTRACION",
                                 derechos={"edit": False}, expected_version=1, correlation_id="c1")
            self.assertEqual(ctx.exception.code, "CORE_ADMIN_PERMISSION")

    def test_can_grant_a_permission_to_a_non_admin_role(self):
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin1@example.com")
            resultado = save_permission(session, admin, "ROLE_CONSULTA", "CASOS",
                                         derechos={"export": True}, expected_version=1, correlation_id="c1")
            self.assertTrue(resultado["export"])

    def test_permission_update_requires_expected_version(self):
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin1@example.com")
            with self.assertRaises(AppError) as ctx:
                save_permission(session, admin, "ROLE_CONSULTA", "CASOS",
                                 derechos={"export": True}, expected_version=None, correlation_id="c1")
            self.assertEqual(ctx.exception.code, "EXPECTED_VERSION_REQUIRED")


if __name__ == "__main__":
    unittest.main()
