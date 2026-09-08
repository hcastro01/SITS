from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.core.config import SQLiteJournalMode, get_settings


_SQLITE_PRAGMAS = {
    "wal": ("PRAGMA journal_mode=WAL", "PRAGMA synchronous=NORMAL"),
    "delete": ("PRAGMA journal_mode=DELETE", "PRAGMA synchronous=FULL"),
}


def build_engine(database_url: str, journal_mode: SQLiteJournalMode = "wal"):
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite":
        raise ValueError("Esta fase de la migración requiere SQLite.")
    try:
        journal_statement, synchronous_statement = _SQLITE_PRAGMAS[journal_mode]
    except KeyError as exc:
        raise ValueError("journal_mode debe ser 'wal' o 'delete'.") from exc
    if url.database and url.database != ":memory:":
        Path(url.database).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(database_url, connect_args={"check_same_thread": False, "timeout": 10})

    @event.listens_for(engine, "connect")
    def configure_sqlite(connection, _):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=10000")
        if url.database != ":memory:":
            cursor.execute(journal_statement)
            cursor.execute(synchronous_statement)
        cursor.close()

    return engine


settings = get_settings()
engine = build_engine(settings.database_url, settings.sqlite_journal_mode)
SessionLocal = sessionmaker(bind=engine)
