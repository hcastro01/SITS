import unittest
from dataclasses import replace
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
from app.services.admin import (
    create_user, list_administration, reset_user_password, restore_user, save_permission, save_user, save_user_role,
    soft_delete_user,
)
from app.services.passwords import hash_password, verify_password
from app.services.security_seed import MODULES, ROLES, seed_security
from app.services.sessions import create_session, resolve_session_user_id


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
            self.assertEqual(len(datos["permisos"]), len(MODULES) * len(ROLES))
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

    def test_admin_can_update_user_data_with_normalized_email_and_safe_audit(self):
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin1@example.com")
            resultado = save_user(
                session, admin, "ts", nombre="  Trabajador Actualizado  ", correo="  TS.NUEVO@EXAMPLE.COM ",
                rol_id="ROLE_CONSULTA", estado="INACTIVO", expected_version=1, correlation_id="update-1",
            )
            self.assertEqual(resultado["nombre"], "Trabajador Actualizado")
            self.assertEqual(resultado["correo"], "ts.nuevo@example.com")
            self.assertEqual(resultado["rol_id"], "ROLE_CONSULTA")
            self.assertEqual(resultado["estado"], "INACTIVO")
            self.assertFalse(resultado["activo"])
            self.assertEqual(resultado["version"], 2)
            self.assertNotIn("password_hash", resultado)
            auditorias = session.scalars(select(Auditoria).where(
                Auditoria.tabla == "usuarios", Auditoria.id_registro == "ts", Auditoria.accion == "UPDATE",
            )).all()
            self.assertTrue(auditorias)
            self.assertTrue(all(row.campo not in {"password", "password_hash"} for row in auditorias))
            self.assertTrue(all(row.motivo == "Actualización de usuario" for row in auditorias))
            self.assertTrue(all(row.correlation_id == "update-1" for row in auditorias))

    def test_user_update_rejects_invalid_or_duplicate_email(self):
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin1@example.com")
            for correo, code in (("no-es-correo", "INVALID_EMAIL"), ("ADMIN1@EXAMPLE.COM", "USER_ALREADY_EXISTS")):
                with self.subTest(correo=correo), self.assertRaises(AppError) as ctx:
                    save_user(
                        session, admin, "ts", nombre="Trabajador", correo=correo,
                        rol_id="ROLE_TRABAJADOR_SOCIAL", estado="ACTIVO", expected_version=1, correlation_id="update-1",
                    )
                self.assertEqual(ctx.exception.code, code)

    def test_admin_can_reset_password_without_auditing_secret_or_hash(self):
        old_password = "ClaveAnterior123"
        new_password = "ClaveNueva456"
        with Session(self.engine) as session, session.begin():
            session.get(User, "ts").password_hash = hash_password(old_password)
            token_one = create_session(session, "ts")
            token_two = create_session(session, "ts")
            admin = resolve_current_user(session, "admin1@example.com")
            resultado = reset_user_password(
                session, admin, "ts", password=new_password, expected_version=1, correlation_id="password-1",
            )
            usuario = session.get(User, "ts")
            self.assertEqual(resultado["version"], 2)
            self.assertNotIn("password", resultado)
            self.assertNotIn("password_hash", resultado)
            self.assertTrue(verify_password(new_password, usuario.password_hash))
            self.assertFalse(verify_password(old_password, usuario.password_hash))
            auditorias = session.scalars(select(Auditoria).where(
                Auditoria.tabla == "usuarios", Auditoria.id_registro == "ts", Auditoria.accion == "UPDATE",
            )).all()
            self.assertTrue(auditorias)
            self.assertTrue(all(row.campo not in {"password", "password_hash"} for row in auditorias))
            audit_values = " ".join((row.valor_anterior or "") + (row.valor_nuevo or "") for row in auditorias)
            self.assertNotIn(new_password, audit_values)
            self.assertNotIn(usuario.password_hash, audit_values)
            self.assertTrue(all(row.motivo == "Restablecimiento de contraseña por administrador" for row in auditorias))
            self.assertTrue(all(row.correlation_id == "password-1" for row in auditorias))
            self.assertIsNone(resolve_session_user_id(session, token_one))
            self.assertIsNone(resolve_session_user_id(session, token_two))

    def test_password_reset_requires_edit_permission_and_current_version(self):
        with Session(self.engine) as session, session.begin():
            consulta = resolve_current_user(session, "consulta@example.com")
            with self.assertRaises(AppError) as forbidden:
                reset_user_password(session, consulta, "ts", password="ClaveNueva456", expected_version=1, correlation_id="x")
            self.assertEqual(forbidden.exception.code, "FORBIDDEN")

            admin = resolve_current_user(session, "admin1@example.com")
            with self.assertRaises(AppError) as stale:
                reset_user_password(session, admin, "ts", password="ClaveNueva456", expected_version=99, correlation_id="x")
            self.assertEqual(stale.exception.code, "VERSION_CONFLICT")

    def test_password_reset_rejects_weak_password(self):
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin1@example.com")
            with self.assertRaises(AppError) as ctx:
                reset_user_password(session, admin, "ts", password="débil", expected_version=1, correlation_id="x")
            self.assertEqual(ctx.exception.code, "WEAK_PASSWORD")

    def test_soft_delete_lifecycle_preserves_row_password_audit_and_revokes_all_sessions(self):
        password = "ClaveTemporalEliminacion123"
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin1@example.com")
            usuario = session.get(User, "ts")
            usuario.password_hash = hash_password(password)
            token_one = create_session(session, "ts")
            token_two = create_session(session, "ts")
            deleted = soft_delete_user(
                session, admin, "ts", expected_version=1, motivo="Salida de la compañía", correlation_id="delete-1",
            )
            self.assertTrue(deleted["eliminado"])
            self.assertFalse(deleted["activo"])
            self.assertEqual(deleted["version"], 2)
            self.assertNotIn("password", deleted)
            self.assertNotIn("password_hash", deleted)

        with Session(self.engine) as session:
            usuario = session.get(User, "ts")
            self.assertIsNotNone(usuario)
            self.assertTrue(usuario.eliminado)
            self.assertEqual(usuario.motivo_eliminacion, "Salida de la compañía")
            self.assertTrue(verify_password(password, usuario.password_hash))
            self.assertIsNone(resolve_session_user_id(session, token_one))
            self.assertIsNone(resolve_session_user_id(session, token_two))
            admin = resolve_current_user(session, "admin1@example.com")
            self.assertNotIn("ts", {item["id_usuario"] for item in list_administration(session, admin)["usuarios"]})
            self.assertIn("ts", {item["id_usuario"] for item in list_administration(session, admin, include_deleted=True)["usuarios"]})
            audit_values = " ".join(
                (row.valor_anterior or "") + (row.valor_nuevo or "")
                for row in session.scalars(select(Auditoria).where(Auditoria.id_registro == "ts")).all()
            )
            self.assertNotIn(password, audit_values)
            self.assertNotIn(usuario.password_hash, audit_values)
            self.assertNotIn(token_one, audit_values)
            self.assertNotIn(token_two, audit_values)

        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin1@example.com")
            restored = restore_user(session, admin, "ts", expected_version=2, correlation_id="restore-1")
            self.assertFalse(restored["eliminado"])
            self.assertTrue(restored["activo"])
            self.assertEqual(restored["version"], 3)
            self.assertTrue(verify_password(password, session.get(User, "ts").password_hash))
            self.assertIsNone(resolve_session_user_id(session, token_one))
            self.assertIsNone(resolve_session_user_id(session, token_two))

    def test_restore_keeps_an_inactive_user_inactive(self):
        with Session(self.engine) as session, session.begin():
            session.add(User(id_usuario="inactive", correo="inactive@example.com", nombre="Inactivo",
                             rol_id="ROLE_CONSULTA", estado="INACTIVO", activo=False))
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin1@example.com")
            deleted = soft_delete_user(session, admin, "inactive", expected_version=1, motivo="Archivo", correlation_id="d")
            self.assertTrue(deleted["eliminado"])
            restored = restore_user(session, admin, "inactive", expected_version=2, correlation_id="r")
            self.assertEqual(restored["estado"], "INACTIVO")
            self.assertFalse(restored["activo"])
            self.assertFalse(restored["eliminado"])

    def test_user_lifecycle_requires_delete_permission_reason_current_version_and_admin_safeguards(self):
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin1@example.com")
            consulta = resolve_current_user(session, "consulta@example.com")
            with self.assertRaises(AppError) as forbidden_delete:
                soft_delete_user(session, consulta, "ts", expected_version=1, motivo="x", correlation_id="x")
            self.assertEqual(forbidden_delete.exception.code, "FORBIDDEN")
            with self.assertRaises(AppError) as missing_reason:
                soft_delete_user(session, admin, "ts", expected_version=1, motivo="  ", correlation_id="x")
            self.assertEqual(missing_reason.exception.code, "DELETE_REASON_REQUIRED")
            with self.assertRaises(AppError) as stale:
                soft_delete_user(session, admin, "ts", expected_version=99, motivo="x", correlation_id="x")
            self.assertEqual(stale.exception.code, "VERSION_CONFLICT")
            with self.assertRaises(AppError) as self_delete:
                soft_delete_user(session, admin, "admin1", expected_version=1, motivo="x", correlation_id="x")
            self.assertEqual(self_delete.exception.code, "SELF_DELETE_FORBIDDEN")
            with self.assertRaises(AppError) as last_admin:
                soft_delete_user(session, replace(admin, id_usuario="otro-admin"), "admin1",
                                 expected_version=1, motivo="x", correlation_id="x")
            self.assertEqual(last_admin.exception.code, "LAST_ADMIN")

    def test_deleted_listing_and_restore_require_delete_permission_and_current_version(self):
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin1@example.com")
            soft_delete_user(session, admin, "ts", expected_version=1, motivo="x", correlation_id="x")
            consulta = resolve_current_user(session, "consulta@example.com")
            with self.assertRaises(AppError) as hidden:
                list_administration(session, consulta, include_deleted=True)
            self.assertEqual(hidden.exception.code, "FORBIDDEN")
            with self.assertRaises(AppError) as forbidden_restore:
                restore_user(session, consulta, "ts", expected_version=2, correlation_id="x")
            self.assertEqual(forbidden_restore.exception.code, "FORBIDDEN")
            with self.assertRaises(AppError) as stale_restore:
                restore_user(session, admin, "ts", expected_version=99, correlation_id="x")
            self.assertEqual(stale_restore.exception.code, "VERSION_CONFLICT")

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
