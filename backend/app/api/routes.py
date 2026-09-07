from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import engine


router = APIRouter(prefix="/api/v1")

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def _expected_head() -> str:
    """Revisión Alembic más reciente conocida por el código."""
    config = Config(str(ALEMBIC_INI))
    return ScriptDirectory.from_config(config).get_current_head()


@router.get("/health/live", tags=["Estado"])
def live():
    return {"status": "ok"}


@router.get("/health/ready", tags=["Estado"])
def ready():
    try:
        with engine.connect() as connection:
            version = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()

        if version != _expected_head():
            raise HTTPException(
                status_code=503,
                detail="Esquema pendiente de actualización",
            )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Servicio temporalmente no disponible",
        ) from None

    return {"status": "ok", "database": "ok"}