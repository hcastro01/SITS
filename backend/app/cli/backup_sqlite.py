"""Crea un respaldo consistente de SQLite mediante su API de backup en línea."""

import argparse
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.engine import make_url

from app.core.config import get_settings


def sqlite_path(database_url: str) -> Path:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        raise ValueError("DATABASE_URL debe apuntar a un archivo SQLite.")
    path = Path(url.database).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"No existe la base SQLite configurada: {path}")
    return path


def create_backup(database_url: str, output_dir: Path) -> Path:
    source_path = sqlite_path(database_url)
    target_dir = output_dir.expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-UTC")
    target = target_dir / f"{source_path.stem}-{timestamp}.db"
    if target.exists():
        raise FileExistsError(f"El respaldo ya existe: {target}")

    temporary_file = tempfile.NamedTemporaryFile(
        prefix=f".{source_path.stem}-",
        suffix=".partial",
        dir=target_dir,
        delete=False,
    )
    temporary_path = Path(temporary_file.name)
    temporary_file.close()

    try:
        source_uri = f"{source_path.as_uri()}?mode=ro"
        with sqlite3.connect(source_uri, uri=True) as source, sqlite3.connect(temporary_path) as destination:
            source.backup(destination)
            result = destination.execute("PRAGMA quick_check").fetchone()
            if result != ("ok",):
                raise RuntimeError("El respaldo creado no superó PRAGMA quick_check.")
        temporary_path.replace(target)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    return target


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Crea y verifica un respaldo consistente de la base SQLite configurada."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("backups"),
        help="Directorio de salida (por defecto: ./backups).",
    )
    args = parser.parse_args()
    backup = create_backup(get_settings().database_url, args.output_dir)
    print(f"Respaldo SQLite verificado: {backup}")


if __name__ == "__main__":
    main()
