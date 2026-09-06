import unittest
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.cli.bootstrap_admin import AdminAlreadyBootstrapped, bootstrap_admin
from app.db.session import build_engine
from app.models import User
from app.services.security_seed import ROLES, seed_security


class BootstrapAdminTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.engine = build_engine(f"sqlite:///{self.directory.name}/test.db")
        self._original_engine = db_session.engine
        db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")

    def tearDown(self):
        db_session.engine = self._original_engine
        self.engine.dispose()
        self.directory.cleanup()

    def test_creates_first_admin_when_no_users_exist(self):
        with Session(self.engine) as session, session.begin():
            seed_security(session)
        with Session(self.engine) as session, session.begin():
            created = bootstrap_admin(session, correo="  Admin@Example.COM ", nombre="Persona Responsable")
            created_id = created.id_usuario
        with Session(self.engine) as session:
            user = session.get(User, created_id)
            self.assertEqual(user.correo, "admin@example.com")
            self.assertEqual(user.nombre, "Persona Responsable")
            self.assertEqual(user.rol_id, "ROLE_ADMIN")
            self.assertEqual(user.estado, "ACTIVO")
            self.assertTrue(user.activo)
            self.assertFalse(user.eliminado)

    def test_refuses_when_any_user_exists(self):
        with Session(self.engine) as session, session.begin():
            seed_security(session)
        with Session(self.engine) as session, session.begin():
            session.add(User(id_usuario="u1", correo="existente@example.com", nombre="Existente",
                              rol_id="ROLE_CONSULTA", estado="ACTIVO"))
        with self.assertRaises(AdminAlreadyBootstrapped):
            with Session(self.engine) as session, session.begin():
                bootstrap_admin(session, correo="otro@example.com", nombre="Otro")
        with Session(self.engine) as session:
            self.assertIsNone(session.scalar(select(User).where(User.correo == "otro@example.com")))
            self.assertEqual(session.scalar(select(func.count()).select_from(User)), 1)

    def test_requires_admin_role_to_already_exist(self):
        # Motor recién migrado, sin seed_security: ROLE_ADMIN todavía no existe.
        with self.assertRaises(LookupError):
            with Session(self.engine) as session, session.begin():
                bootstrap_admin(session, correo="admin@example.com", nombre="Persona Responsable")

    def test_role_admin_constant_matches_seed(self):
        self.assertIn("ROLE_ADMIN", ROLES)


if __name__ == "__main__":
    unittest.main()
