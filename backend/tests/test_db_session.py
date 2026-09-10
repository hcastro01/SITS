import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from app.core.config import Settings
from app.db.session import build_engine


class SQLiteJournalModeTests(unittest.TestCase):
    def build_temporary_engine(self, journal_mode: str):
        directory = tempfile.TemporaryDirectory()
        database_path = Path(directory.name) / "journal-mode.db"
        engine = build_engine(f"sqlite:///{database_path.as_posix()}", journal_mode)
        self.addCleanup(directory.cleanup)
        self.addCleanup(engine.dispose)
        return engine

    @staticmethod
    def read_pragmas(engine):
        with engine.connect() as connection:
            return {
                "journal_mode": connection.exec_driver_sql("PRAGMA journal_mode").scalar_one(),
                "foreign_keys": connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one(),
                "busy_timeout": connection.exec_driver_sql("PRAGMA busy_timeout").scalar_one(),
                "synchronous": connection.exec_driver_sql("PRAGMA synchronous").scalar_one(),
            }

    def test_wal_is_the_default_and_is_applied_to_the_engine(self):
        with patch.dict(os.environ):
            os.environ.pop("SQLITE_JOURNAL_MODE", None)
            settings = Settings(_env_file=None)
        self.assertEqual(settings.sqlite_journal_mode, "wal")

        pragmas = self.read_pragmas(self.build_temporary_engine(settings.sqlite_journal_mode))

        self.assertEqual(pragmas["journal_mode"], "wal")
        self.assertEqual(pragmas["foreign_keys"], 1)
        self.assertEqual(pragmas["busy_timeout"], 10000)
        self.assertEqual(pragmas["synchronous"], 1)  # NORMAL

    def test_delete_from_environment_is_applied_to_the_engine(self):
        with patch.dict(os.environ, {"SQLITE_JOURNAL_MODE": "delete"}):
            settings = Settings(_env_file=None)

        self.assertEqual(settings.sqlite_journal_mode, "delete")
        pragmas = self.read_pragmas(self.build_temporary_engine(settings.sqlite_journal_mode))

        self.assertEqual(pragmas["journal_mode"], "delete")
        self.assertEqual(pragmas["foreign_keys"], 1)
        self.assertEqual(pragmas["busy_timeout"], 10000)
        self.assertEqual(pragmas["synchronous"], 2)  # FULL

    def test_invalid_setting_is_rejected(self):
        with patch.dict(os.environ, {"SQLITE_JOURNAL_MODE": "truncate"}):
            with self.assertRaises(ValidationError):
                Settings(_env_file=None)

    def test_build_engine_rejects_an_unvalidated_journal_mode(self):
        with self.assertRaisesRegex(ValueError, "debe ser 'wal' o 'delete'"):
            build_engine("sqlite:///:memory:", "truncate")

    def production_settings(self, **overrides):
        values = {
            "environment": "production",
            "auth_mode": "password",
            "cookie_secure": True,
            "cookie_samesite": "none",
            "database_url": "sqlite:////var/lib/sits/trabajo_social.db",
            "cors_origins": ["https://sits.example.com"],
            "trusted_hosts": ["api.sits.example.com"],
        }
        values.update(overrides)
        return Settings(_env_file=None, **values)

    def test_production_accepts_an_absolute_persistent_sqlite_path(self):
        settings = self.production_settings()

        self.assertEqual(settings.environment, "production")
        self.assertEqual(settings.database_url, "sqlite:////var/lib/sits/trabajo_social.db")

    def test_production_rejects_relative_or_in_memory_sqlite(self):
        for database_url in ("sqlite:///./data/sits.db", "sqlite:///:memory:"):
            with self.subTest(database_url=database_url), self.assertRaisesRegex(
                ValidationError, "SQLite absoluto y persistente"
            ):
                self.production_settings(database_url=database_url)

    def test_production_rejects_insecure_origins_and_hosts(self):
        with self.assertRaisesRegex(ValidationError, "orígenes HTTPS exactos"):
            self.production_settings(cors_origins=["http://sits.example.com"])
        with self.assertRaisesRegex(ValidationError, "orígenes HTTPS exactos"):
            self.production_settings(cors_origins=["https://sits.example.com/login"])
        with self.assertRaisesRegex(ValidationError, "hosts públicos exactos"):
            self.production_settings(trusted_hosts=["*"])
        with self.assertRaisesRegex(ValidationError, "hosts públicos exactos"):
            self.production_settings(trusted_hosts=["https://api.sits.example.com"])

    def test_session_ttl_is_bounded(self):
        for hours in (0, 169):
            with self.subTest(hours=hours), self.assertRaises(ValidationError):
                Settings(_env_file=None, session_ttl_hours=hours)


if __name__ == "__main__":
    unittest.main()
