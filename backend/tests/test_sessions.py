import unittest
from datetime import UTC, datetime, timedelta
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.db.session import build_engine
from app.models import Sesion, User
from app.services.security_seed import seed_security
from app.services.sessions import create_session, resolve_session_user_id, revoke_session


class SessionsServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.engine = build_engine(f"sqlite:///{self.directory.name}/test.db")
        self._original_engine = db_session.engine
        db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")
        with Session(self.engine) as session, session.begin():
            seed_security(session)
            session.add(User(id_usuario="u1", correo="u1@example.com", nombre="Uno",
                              rol_id="ROLE_CONSULTA", estado="ACTIVO"))

    def tearDown(self):
        db_session.engine = self._original_engine
        self.engine.dispose()
        self.directory.cleanup()

    def test_token_is_never_stored_in_plain_text(self):
        with Session(self.engine) as session, session.begin():
            token = create_session(session, "u1")
        with Session(self.engine) as session:
            fila = session.scalar(select(Sesion))
            self.assertNotEqual(fila.token_hash, token)
            self.assertNotIn(token, fila.token_hash)

    def test_valid_token_resolves_to_the_right_user(self):
        with Session(self.engine) as session, session.begin():
            token = create_session(session, "u1")
        with Session(self.engine) as session:
            self.assertEqual(resolve_session_user_id(session, token), "u1")

    def test_unknown_token_resolves_to_none(self):
        with Session(self.engine) as session:
            self.assertIsNone(resolve_session_user_id(session, "token-inventado"))

    def test_empty_token_resolves_to_none(self):
        with Session(self.engine) as session:
            self.assertIsNone(resolve_session_user_id(session, ""))

    def test_expired_session_resolves_to_none(self):
        with Session(self.engine) as session, session.begin():
            token = create_session(session, "u1")
        with Session(self.engine) as session, session.begin():
            fila = session.scalar(select(Sesion))
            fila.expira_en = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        with Session(self.engine) as session:
            self.assertIsNone(resolve_session_user_id(session, token))

    def test_revoked_session_resolves_to_none(self):
        with Session(self.engine) as session, session.begin():
            token = create_session(session, "u1")
        with Session(self.engine) as session, session.begin():
            revoke_session(session, token)
        with Session(self.engine) as session:
            self.assertIsNone(resolve_session_user_id(session, token))

    def test_revoke_is_idempotent(self):
        with Session(self.engine) as session, session.begin():
            token = create_session(session, "u1")
        with Session(self.engine) as session, session.begin():
            revoke_session(session, token)
        with Session(self.engine) as session, session.begin():
            revoke_session(session, token)  # no debe fallar ni sobrescribir la primera revocación
        with Session(self.engine) as session:
            fila = session.scalar(select(Sesion))
            self.assertIsNotNone(fila.revocada_en)


if __name__ == "__main__":
    unittest.main()
