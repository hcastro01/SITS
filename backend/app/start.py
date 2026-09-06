import uvicorn
from alembic import command
from alembic.config import Config

from app.db.session import SessionLocal
from app.services.matrix_seed import seed_institutional_matrix
from app.services.security_seed import seed_security


def initialize():
    command.upgrade(Config("alembic.ini"), "head")
    with SessionLocal.begin() as session:
        seed_security(session)
        seed_institutional_matrix(session)


if __name__ == "__main__":
    initialize()
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, workers=1, proxy_headers=False)

