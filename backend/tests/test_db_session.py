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
        self.addCleanup(engine.dispose)
        self.addCleanup(directory.cleanup)
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


if __name__ == "__main__":
    unittest.main()
