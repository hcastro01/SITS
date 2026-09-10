import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.cli.backup_sqlite import create_backup
from app.cli.production_check import expected_head, run_checks
from app.core.config import Settings
from app.db.session import build_engine
from app.models import Base, Role, User
from sqlalchemy import text
from sqlalchemy.orm import Session


class SQLiteBackupTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.database = self.root / "sits.db"
        with sqlite3.connect(self.database) as connection:
            connection.execute("CREATE TABLE casos (id INTEGER PRIMARY KEY, codigo TEXT NOT NULL)")
            connection.execute("INSERT INTO casos (codigo) VALUES ('CASO-001')")

    def test_backup_is_consistent_and_contains_committed_data(self):
        backup = create_backup(
            f"sqlite:///{self.database.as_posix()}",
            self.root / "backups",
        )

        self.assertTrue(backup.is_file())
        with sqlite3.connect(backup) as connection:
            self.assertEqual(connection.execute("PRAGMA quick_check").fetchone(), ("ok",))
            self.assertEqual(connection.execute("SELECT codigo FROM casos").fetchone(), ("CASO-001",))
        self.assertEqual(list((self.root / "backups").glob("*.partial")), [])

    def test_backup_rejects_a_missing_database(self):
        with self.assertRaises(FileNotFoundError):
            create_backup(
                f"sqlite:///{(self.root / 'missing.db').as_posix()}",
                self.root / "backups",
            )


class ProductionCheckTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.database = Path(self.directory.name) / "production.db"
        self.engine = build_engine(f"sqlite:///{self.database.as_posix()}")
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)
        with self.engine.begin() as connection:
            connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
            connection.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
                {"revision": expected_head()},
            )
        with Session(self.engine) as session:
            session.add(Role(id_rol="ROLE_ADMIN", nombre="Administrador"))
            session.add(
                User(
                    id_usuario="admin",
                    correo="admin@example.com",
                    nombre="Admin",
                    rol_id="ROLE_ADMIN",
                    estado="ACTIVO",
                    password_hash="hash-de-prueba",
                )
            )
            session.commit()

    def settings(self):
        return Settings(
            _env_file=None,
            environment="production",
            auth_mode="password",
            cookie_secure=True,
            cookie_samesite="none",
            database_url=f"sqlite:///{self.database.as_posix()}",
            cors_origins=["https://sits.example.com"],
            trusted_hosts=["api.sits.example.com"],
        )

    def test_ready_database_passes_all_mandatory_checks(self):
        results = run_checks(self.settings(), self.engine)

        self.assertFalse([result for result in results if result.status == "error"])
        self.assertIn("administración", {result.name for result in results})
        self.assertIn("migraciones", {result.name for result in results})

    def test_missing_admin_password_is_reported_as_an_error(self):
        with Session(self.engine) as session:
            admin = session.get(User, "admin")
            admin.password_hash = None
            session.commit()

        results = run_checks(self.settings(), self.engine)

        admin_check = next(result for result in results if result.name == "administración")
        self.assertEqual(admin_check.status, "error")


if __name__ == "__main__":
    unittest.main()
