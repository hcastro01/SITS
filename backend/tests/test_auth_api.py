"""Prueba las funciones de los endpoints de auth por invocación directa: el proyecto no
tiene httpx en requirements.txt (lo necesita fastapi.testclient.TestClient), así que se
llama a las funciones de ruta como funciones Python normales en vez de por HTTP real.
"""

import unittest
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from fastapi import Response
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.api.auth import LoginRequest, login, login_throttle, me
from app.core.errors import AppError
from app.core.permissions import resolve_current_user
from app.db.session import build_engine
from app.models import User
from app.services.security_seed import seed_security
from app.services.sessions import COOKIE_NAME
from app.services.passwords import hash_password


class AuthApiTests(unittest.TestCase):
    def setUp(self):
        login_throttle.clear()
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
        login_throttle.clear()
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

    def test_password_mode_accepts_only_the_configured_password(self):
        settings = SimpleNamespace(auth_mode="password", cookie_secure=True, cookie_samesite="none", session_ttl_hours=12)
        with Session(self.engine) as session, session.begin():
            session.get(User, "u1").password_hash = hash_password("ClaveSegura123")
        with patch("app.api.auth.get_settings", return_value=settings):
            with Session(self.engine) as session, session.begin():
                with self.assertRaises(AppError) as ctx:
                    login(LoginRequest(correo="ana@example.com", password="ClaveIncorrecta123"), Response(), session)
                self.assertEqual(ctx.exception.code, "INVALID_CREDENTIALS")
            with Session(self.engine) as session, session.begin():
                profile = login(LoginRequest(correo="ana@example.com", password="ClaveSegura123"), Response(), session)
                self.assertEqual(profile.id_usuario, "u1")

    def test_password_mode_runs_a_dummy_verification_for_unknown_users(self):
        settings = SimpleNamespace(auth_mode="password", cookie_secure=True, cookie_samesite="none", session_ttl_hours=12)
        with patch("app.api.auth.get_settings", return_value=settings), \
             patch("app.api.auth.verify_password", return_value=False) as verifier:
            with Session(self.engine) as session, session.begin():
                with self.assertRaises(AppError) as ctx:
                    login(LoginRequest(correo="unknown@example.com", password="ClaveSegura123"), Response(), session)
            self.assertEqual(ctx.exception.code, "INVALID_CREDENTIALS")
            verifier.assert_called_once()

    def test_password_mode_blocks_repeated_failures_for_the_same_account(self):
        settings = SimpleNamespace(
            auth_mode="password", cookie_secure=True, cookie_samesite="none", session_ttl_hours=12,
            login_max_attempts=3, login_window_seconds=300,
        )
        with patch("app.api.auth.get_settings", return_value=settings), \
             patch("app.api.auth.verify_password", return_value=False) as verifier:
            with Session(self.engine) as session, session.begin():
                for _ in range(3):
                    with self.assertRaises(AppError) as ctx:
                        login(LoginRequest(correo="unknown@example.com", password="Incorrecta123"), Response(), session)
                    self.assertEqual(ctx.exception.code, "INVALID_CREDENTIALS")
                with self.assertRaises(AppError) as ctx:
                    login(LoginRequest(correo="unknown@example.com", password="Incorrecta123"), Response(), session)
            self.assertEqual(ctx.exception.code, "TOO_MANY_LOGIN_ATTEMPTS")
            self.assertEqual(ctx.exception.status_code, 429)
            self.assertEqual(verifier.call_count, 3)

    def test_successful_login_clears_previous_failures(self):
        settings = SimpleNamespace(
            auth_mode="password", cookie_secure=True, cookie_samesite="none", session_ttl_hours=12,
            login_max_attempts=3, login_window_seconds=300,
        )
        with Session(self.engine) as session, session.begin():
            session.get(User, "u1").password_hash = hash_password("ClaveSegura123")
        with patch("app.api.auth.get_settings", return_value=settings):
            with Session(self.engine) as session, session.begin():
                for _ in range(2):
                    with self.assertRaises(AppError):
                        login(LoginRequest(correo="ana@example.com", password="Incorrecta123"), Response(), session)
                profile = login(LoginRequest(correo="ana@example.com", password="ClaveSegura123"), Response(), session)
                self.assertEqual(profile.id_usuario, "u1")
                for _ in range(2):
                    with self.assertRaises(AppError) as ctx:
                        login(LoginRequest(correo="ana@example.com", password="Incorrecta123"), Response(), session)
                    self.assertEqual(ctx.exception.code, "INVALID_CREDENTIALS")


if __name__ == "__main__":
    unittest.main()
