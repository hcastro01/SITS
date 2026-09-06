"""Prueba las funciones de los endpoints de auth por invocación directa: el proyecto no
tiene httpx en requirements.txt (lo necesita fastapi.testclient.TestClient), así que se
llama a las funciones de ruta como funciones Python normales en vez de por HTTP real.
"""

import unittest
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from fastapi import Response
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.api.auth import LoginRequest, login, me
from app.core.errors import AppError
from app.core.permissions import resolve_current_user
from app.db.session import build_engine
from app.models import User
from app.services.security_seed import seed_security
from app.services.sessions import COOKIE_NAME


class AuthApiTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.engine = build_engine(f"sqlite:///{self.directory.name}/test.db")
        self._original_engine = db_session.engine
        db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")
        with Session(self.engine) as session, session.begin():
            seed_security(session)
        with Session(self.engine) as session, session.begin():
            session.add(User(id_usuario="u1", correo="ana@example.com", nombre="Ana",
                              rol_id="ROLE_CONSULTA", estado="ACTIVO"))
            session.add(User(id_usuario="u2", correo="inactivo@example.com", nombre="Inactivo",
                              rol_id="ROLE_CONSULTA", estado="INACTIVO"))

    def tearDown(self):
        db_session.engine = self._original_engine
        self.engine.dispose()
        self.directory.cleanup()

    def test_login_sets_session_cookie_and_returns_profile(self):
        with Session(self.engine) as session, session.begin():
            response = Response()
            perfil = login(LoginRequest(correo="  Ana@Example.COM "), response, session)
            self.assertEqual(perfil.correo, "ana@example.com")
            self.assertEqual(perfil.rol_id, "ROLE_CONSULTA")
            set_cookie_headers = response.raw_headers
            cookie_header = next(v for k, v in set_cookie_headers if k == b"set-cookie")
            self.assertIn(COOKIE_NAME.encode(), cookie_header)
            self.assertIn(b"HttpOnly", cookie_header)

    def test_login_rejects_unregistered_email(self):
        with Session(self.engine) as session, session.begin():
            with self.assertRaises(AppError) as ctx:
                login(LoginRequest(correo="nadie@example.com"), Response(), session)
            self.assertEqual(ctx.exception.code, "USER_NOT_REGISTERED")

    def test_login_rejects_inactive_user(self):
        with Session(self.engine) as session, session.begin():
            with self.assertRaises(AppError) as ctx:
                login(LoginRequest(correo="inactivo@example.com"), Response(), session)
            self.assertEqual(ctx.exception.code, "USER_DISABLED")

    def test_me_returns_the_resolved_user_profile(self):
        with Session(self.engine) as session:
            user = resolve_current_user(session, "ana@example.com")
            perfil = me(user)
            self.assertEqual(perfil.id_usuario, user.id_usuario)
            self.assertEqual(perfil.rol_nombre, user.rol_nombre)


if __name__ == "__main__":
    unittest.main()
