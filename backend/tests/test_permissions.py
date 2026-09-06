import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.core.errors import AppError
from app.core.permissions import authorize, authorize_sensitive_child, resolve_current_user
from app.db.session import build_engine
from app.models import User
from app.services.security_seed import ROLES, seed_security


class PermissionMatrixTests(unittest.TestCase):
    """Deriva la matriz de denegación de tests/legacy_permissions.json (90 combinaciones,
    5 roles x 18 módulos), la misma fuente que valida el seed contra Setup.gs."""

    def setUp(self):
        self.directory = TemporaryDirectory()
        self.engine = build_engine(f"sqlite:///{self.directory.name}/test.db")
        self._original_engine = db_session.engine
        db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")
        self.correo_by_role = {rol_id: f"{rol_id.lower()}@example.com" for rol_id in ROLES}
        with Session(self.engine) as session, session.begin():
            seed_security(session)
            for rol_id, correo in self.correo_by_role.items():
                session.add(User(id_usuario=rol_id, correo=correo, nombre=rol_id, rol_id=rol_id, estado="ACTIVO"))
        self.legacy = json.loads(Path(__file__).with_name("legacy_permissions.json").read_text())

    def tearDown(self):
        db_session.engine = self._original_engine
        self.engine.dispose()
        self.directory.cleanup()

    def test_authorize_matches_legacy_matrix_for_every_role_and_module(self):
        with Session(self.engine) as session:
            for row in self.legacy:
                user = resolve_current_user(session, self.correo_by_role[row["role"]])
                for action, allowed in row["rights"].items():
                    with self.subTest(role=row["role"], module=row["module"], action=action):
                        if allowed:
                            authorize(user, row["module"], action)
                        else:
                            with self.assertRaises(AppError) as ctx:
                                authorize(user, row["module"], action)
                            self.assertEqual(ctx.exception.code, "FORBIDDEN")
                            self.assertEqual(ctx.exception.status_code, 403)

    def test_sensitive_is_additive_not_alternative(self):
        # ROLE_TRABAJADOR_SOCIAL tiene CASOS:read pero no CASOS:sensitive (legacy_permissions.json).
        with Session(self.engine) as session:
            user = resolve_current_user(session, self.correo_by_role["ROLE_TRABAJADOR_SOCIAL"])
            authorize(user, "CASOS", "read")  # no debe lanzar
            with self.assertRaises(AppError) as ctx:
                authorize(user, "CASOS", "read", sensitive=True)
            self.assertEqual(ctx.exception.code, "SENSITIVE_FORBIDDEN")

    def test_authorize_sensitive_child_requires_and_not_or(self):
        # Reproduce el escenario del hallazgo de Fase 1 §6: alguien con permiso sensible en
        # CASOS pero no en SEGUIMIENTOS no debe poder ver seguimientos sensibles (ni al
        # revés). Ningún rol del seed cumple ambos lados a la vez salvo ROLE_ADMIN.
        with Session(self.engine) as session:
            trabajador = resolve_current_user(session, self.correo_by_role["ROLE_TRABAJADOR_SOCIAL"])
            with self.assertRaises(AppError):
                authorize_sensitive_child(trabajador, "SEGUIMIENTOS", "read")
            admin = resolve_current_user(session, self.correo_by_role["ROLE_ADMIN"])
            authorize_sensitive_child(admin, "SEGUIMIENTOS", "read")  # no debe lanzar

    def test_invalid_action_is_rejected(self):
        with Session(self.engine) as session:
            user = resolve_current_user(session, self.correo_by_role["ROLE_ADMIN"])
            with self.assertRaises(AppError) as ctx:
                authorize(user, "CASOS", "vuela")
            self.assertEqual(ctx.exception.code, "INVALID_ACTION")

    def test_unregistered_user_is_rejected(self):
        with Session(self.engine) as session:
            with self.assertRaises(AppError) as ctx:
                resolve_current_user(session, "nadie@example.com")
            self.assertEqual(ctx.exception.code, "USER_NOT_REGISTERED")

    def test_disabled_user_is_rejected(self):
        with Session(self.engine) as session, session.begin():
            session.add(User(id_usuario="inactivo", correo="inactivo@example.com", nombre="Inactivo",
                              rol_id="ROLE_CONSULTA", estado="INACTIVO"))
        with Session(self.engine) as session:
            with self.assertRaises(AppError) as ctx:
                resolve_current_user(session, "inactivo@example.com")
            self.assertEqual(ctx.exception.code, "USER_DISABLED")

    def test_correo_is_normalized(self):
        with Session(self.engine) as session:
            user = resolve_current_user(session, "  ROLE_ADMIN@EXAMPLE.COM ")
            self.assertEqual(user.correo, "role_admin@example.com")


if __name__ == "__main__":
    unittest.main()
