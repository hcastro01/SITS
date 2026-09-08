import unittest
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.core.errors import AppError
from app.core.permissions import resolve_current_user
from app.db.session import build_engine
from app.models import Auditoria, User
from app.services.admin import create_user, list_administration, save_permission, save_user_role
from app.services.passwords import verify_password
from app.services.security_seed import seed_security


class AdminServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.engine = build_engine(f"sqlite:///{self.directory.name}/test.db")
        self._original_engine = db_session.engine
        db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")
        with Session(self.engine) as session, session.begin():
            seed_security(session)
            session.add(User(id_usuario="admin1", correo="admin1@example.com", nombre="Admin Uno",
                              rol_id="ROLE_ADMIN", estado="ACTIVO"))
            session.add(User(id_usuario="ts", correo="ts@example.com", nombre="Trabajador",
                              rol_id="ROLE_TRABAJADOR_SOCIAL", estado="ACTIVO"))
            session.add(User(id_usuario="consulta", correo="consulta@example.com", nombre="Consulta",
                              rol_id="ROLE_CONSULTA", estado="ACTIVO"))

    def tearDown(self):
        db_session.engine = self._original_engine
        self.engine.dispose()
        self.directory.cleanup()

    def test_non_admin_cannot_list_administration(self):
        with Session(self.engine) as session:
            ts = resolve_current_user(session, "ts@example.com")
            with self.assertRaises(AppError) as ctx:
                list_administration(session, ts)
            self.assertEqual(ctx.exception.code, "FORBIDDEN")

    def test_admin_can_list_administration(self):
        with Session(self.engine) as session:
            admin = resolve_current_user(session, "admin1@example.com")
            datos = list_administration(session, admin)
            self.assertEqual(len(datos["roles"]), 5)
            self.assertEqual(len(datos["permisos"]), 90)
            self.assertEqual(len(datos["usuarios"]), 3)

    def test_admin_can_create_an_active_user_with_a_hashed_password_and_audit(self):
        password = "TemporalSegura123"
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin1@example.com")
            resultado = create_user(
                session, admin, correo="  NUEVA@Example.COM ", nombre="  Nueva Persona  ",
                rol_id="ROLE_TRABAJADOR_SOCIAL", password=password, correlation_id="create-1",
            )
            usuario = session.get(User, resultado["id_usuario"])
            self.assertEqual(resultado["correo"], "nueva@example.com")
            self.assertEqual(resultado["nombre"], "Nueva Persona")
            self.assertEqual(resultado["estado"], "ACTIVO")
            self.assertTrue(resultado["activo"])
            self.assertFalse(resultado["eliminado"])
            self.assertNotIn("password", resultado)
            self.assertNotIn("password_hash", resultado)
            self.assertIsNotNone(usuario)
            self.assertNotEqual(usuario.password_hash, password)
            self.assertTrue(verify_password(password, usuario.password_hash))
            self.assertEqual(usuario.creado_por, admin.correo)
            self.assertIsNotNone(usuario.fecha_creacion)

            auditorias = session.scalars(select(Auditoria).where(
                Auditoria.tabla == "usuarios", Auditoria.id_registro == usuario.id_usuario,
                Auditoria.accion == "CREATE",
            )).all()
            self.assertTrue(auditorias)
            self.assertTrue(all(row.usuario == admin.correo for row in auditorias))
            self.assertTrue(all(row.motivo == "Alta de usuario" for row in auditorias))
            self.assertTrue(all(row.campo not in {"password", "password_hash"} for row in auditorias))
            self.assertNotIn(password, " ".join((row.valor_nuevo or "") for row in auditorias))

    def test_user_without_create_permission_cannot_create_user(self):
        with Session(self.engine) as session, session.begin():
            consulta = resolve_current_user(session, "consulta@example.com")
            with self.assertRaises(AppError) as ctx:
                create_user(
                    session, consulta, correo="otra@example.com", nombre="Otra Persona",
                    rol_id="ROLE_CONSULTA", password="TemporalSegura123",
                )
            self.assertEqual(ctx.exception.code, "FORBIDDEN")
            self.assertEqual(ctx.exception.status_code, 403)

    def test_create_user_rejects_a_duplicate_email_case_insensitively(self):
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin1@example.com")
            with self.assertRaises(AppError) as ctx:
                create_user(
                    session, admin, correo=" ADMIN1@EXAMPLE.COM ", nombre="Duplicado",
                    rol_id="ROLE_CONSULTA", password="TemporalSegura123",
                )
            self.assertEqual(ctx.exception.code, "USER_ALREADY_EXISTS")
            self.assertEqual(ctx.exception.status_code, 409)

    def test_create_user_rejects_an_unknown_role(self):
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin1@example.com")
            with self.assertRaises(AppError) as ctx:
                create_user(
                    session, admin, correo="otra@example.com", nombre="Otra Persona",
                    rol_id="ROLE_INEXISTENTE", password="TemporalSegura123",
                )
            self.assertEqual(ctx.exception.code, "ROLE_NOT_FOUND")
            self.assertEqual(ctx.exception.status_code, 422)

    def test_create_user_rejects_a_weak_password(self):
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin1@example.com")
            with self.assertRaises(AppError) as ctx:
                create_user(
                    session, admin, correo="otra@example.com", nombre="Otra Persona",
                    rol_id="ROLE_CONSULTA", password="debil",
                )
            self.assertEqual(ctx.exception.code, "WEAK_PASSWORD")
            self.assertEqual(ctx.exception.status_code, 422)

    def test_cannot_demote_the_last_active_admin(self):
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin1@example.com")
            with self.assertRaises(AppError) as ctx:
                save_user_role(session, admin, "admin1", rol_id="ROLE_CONSULTA", estado="ACTIVO",
                                expected_version=1, correlation_id="c1")
            self.assertEqual(ctx.exception.code, "LAST_ADMIN")

    def test_cannot_deactivate_the_last_active_admin(self):
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin1@example.com")
            with self.assertRaises(AppError) as ctx:
                save_user_role(session, admin, "admin1", rol_id="ROLE_ADMIN", estado="INACTIVO",
                                expected_version=1, correlation_id="c1")
            self.assertEqual(ctx.exception.code, "LAST_ADMIN")

    def test_can_demote_admin_when_another_active_admin_exists(self):
        with Session(self.engine) as session, session.begin():
            session.add(User(id_usuario="admin2", correo="admin2@example.com", nombre="Admin Dos",
                              rol_id="ROLE_ADMIN", estado="ACTIVO"))
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin2@example.com")
            resultado = save_user_role(session, admin, "admin1", rol_id="ROLE_CONSULTA", estado="ACTIVO",
                                        expected_version=1, correlation_id="c1")
            self.assertEqual(resultado["rol_id"], "ROLE_CONSULTA")

    def test_non_admin_cannot_reassign_roles(self):
        with Session(self.engine) as session, session.begin():
            consulta = resolve_current_user(session, "consulta@example.com")
            with self.assertRaises(AppError) as ctx:
                save_user_role(session, consulta, "ts", rol_id="ROLE_ADMIN", estado="ACTIVO",
                                expected_version=1, correlation_id="c1")
            self.assertEqual(ctx.exception.code, "FORBIDDEN")

    def test_cannot_strip_core_admin_permission(self):
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin1@example.com")
            with self.assertRaises(AppError) as ctx:
                save_permission(session, admin, "ROLE_ADMIN", "ADMINISTRACION",
                                 derechos={"edit": False}, expected_version=1, correlation_id="c1")
            self.assertEqual(ctx.exception.code, "CORE_ADMIN_PERMISSION")

    def test_can_grant_a_permission_to_a_non_admin_role(self):
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin1@example.com")
            resultado = save_permission(session, admin, "ROLE_CONSULTA", "CASOS",
                                         derechos={"export": True}, expected_version=1, correlation_id="c1")
            self.assertTrue(resultado["export"])

    def test_permission_update_requires_expected_version(self):
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin1@example.com")
            with self.assertRaises(AppError) as ctx:
                save_permission(session, admin, "ROLE_CONSULTA", "CASOS",
                                 derechos={"export": True}, expected_version=None, correlation_id="c1")
            self.assertEqual(ctx.exception.code, "EXPECTED_VERSION_REQUIRED")


if __name__ == "__main__":
    unittest.main()
