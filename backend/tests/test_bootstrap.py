import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import build_engine
from app.models import Base, Permission, Role, User
from app.services.security_seed import seed_security


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.engine = build_engine(f"sqlite:///{self.directory.name}/test.db")
        Base.metadata.create_all(self.engine)

    def tearDown(self):
        self.engine.dispose()
        self.directory.cleanup()

    def test_restart_preserves_permissions_and_never_creates_users(self):
        with Session(self.engine) as session, session.begin():
            seed_security(session)
        with Session(self.engine) as session, session.begin():
            permission = session.get(Permission, "ROLE_ADMIN:CASOS")
            permission.can_delete = False
        with Session(self.engine) as session, session.begin():
            seed_security(session)
        with Session(self.engine) as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(Role)), 5)
            self.assertEqual(session.scalar(select(func.count()).select_from(Permission)), 90)
            self.assertEqual(session.scalar(select(func.count()).select_from(User)), 0)
            self.assertFalse(session.get(Permission, "ROLE_ADMIN:CASOS").can_delete)
            sensitive = session.scalars(select(Permission).where(Permission.can_sensitive)).all()
            self.assertTrue(all(row.role_id == "ROLE_ADMIN" for row in sensitive))

    def test_unknown_role_cannot_be_assigned(self):
        with self.assertRaises(IntegrityError), Session(self.engine) as session, session.begin():
            session.add(User(id="test", email="test@example.invalid", name="Test", role_id="missing"))

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
                        self.assertEqual(getattr(permission, f"can_{action}"), allowed)


if __name__ == "__main__":
    unittest.main()
