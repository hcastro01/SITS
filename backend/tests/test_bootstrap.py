import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.db.session import build_engine
from app.models import Base, Permission, Role, User
from app.services.security_seed import ACTION_TO_FIELD, seed_security


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.engine = build_engine(f"sqlite:///{self.directory.name}/test.db")
        # env.py resuelve `engine` desde app.db.session en tiempo de ejecución de cada
        # comando Alembic; se sustituye temporalmente para migrar la base de prueba.
        self._original_engine = db_session.engine
        db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")

    def tearDown(self):
        db_session.engine = self._original_engine
        self.engine.dispose()
        self.directory.cleanup()

    def test_migrations_match_orm_metadata(self):
        with self.engine.connect() as connection:
            context = MigrationContext.configure(connection)
            diff = compare_metadata(context, Base.metadata)
        self.assertEqual(diff, [], f"Divergencia entre modelos y migraciones: {diff}")

    def test_restart_preserves_permissions_and_never_creates_users(self):
        with Session(self.engine) as session, session.begin():
            seed_security(session)
        with Session(self.engine) as session, session.begin():
            permission = session.get(Permission, "ROLE_ADMIN:CASOS")
            permission.puede_eliminar = False
        with Session(self.engine) as session, session.begin():
            seed_security(session)
        with Session(self.engine) as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(Role)), 5)
            self.assertEqual(session.scalar(select(func.count()).select_from(Permission)), 90)
            self.assertEqual(session.scalar(select(func.count()).select_from(User)), 0)
            self.assertFalse(session.get(Permission, "ROLE_ADMIN:CASOS").puede_eliminar)
            sensitive = session.scalars(select(Permission).where(Permission.puede_sensible)).all()
            self.assertTrue(all(row.rol_id == "ROLE_ADMIN" for row in sensitive))

    def test_unknown_role_cannot_be_assigned(self):
        with self.assertRaises(IntegrityError), Session(self.engine) as session, session.begin():
            session.add(User(id_usuario="test", correo="test@example.invalid", nombre="Test", rol_id="missing"))

    def test_seed_matches_original_apps_script_matrix(self):
        # Fixture extraída ejecutando setupRights_ de Setup.gs con Config.gs.
        expected = json.loads(Path(__file__).with_name("legacy_permissions.json").read_text())
        with Session(self.engine) as session, session.begin():
            seed_security(session)
        with Session(self.engine) as session:
            for row in expected:
                permission = session.get(Permission, f"{row['role']}:{row['module']}")
                for action, allowed in row["rights"].items():
                    with self.subTest(role=row["role"], module=row["module"], action=action):
                        self.assertEqual(getattr(permission, ACTION_TO_FIELD[action]), allowed)


if __name__ == "__main__":
    unittest.main()
