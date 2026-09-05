from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import engine

router = APIRouter(prefix="/api/v1")


@router.get("/health/live", tags=["Estado"])
def live():
    return {"status": "ok"}


@router.get("/health/ready", tags=["Estado"])
def ready():
    try:
        with engine.connect() as connection:
            version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        if version != "0001_security":
            raise HTTPException(status_code=503, detail="Esquema pendiente de actualización")
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Servicio temporalmente no disponible") from None
    return {"status": "ok", "database": "ok"}

