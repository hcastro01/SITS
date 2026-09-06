import unittest
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.core.errors import AppError
from app.core.permissions import resolve_current_user
from app.db.session import build_engine
from app.models import Atencion, Auditoria, User
from app.services.atenciones import create_atencion, restore_atencion, soft_delete_atencion, update_atencion
from app.services.records import get_history
from app.services.security_seed import seed_security


class AtencionesServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.engine = build_engine(f"sqlite:///{self.directory.name}/test.db")
        self._original_engine = db_session.engine
        db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")
        with Session(self.engine) as session, session.begin():
            seed_security(session)
            session.add(User(id_usuario="ts", correo="ts@example.com", nombre="Trabajador",
                              rol_id="ROLE_TRABAJADOR_SOCIAL", estado="ACTIVO"))
            session.add(User(id_usuario="consulta", correo="consulta@example.com", nombre="Consulta",
                              rol_id="ROLE_CONSULTA", estado="ACTIVO"))

    def tearDown(self):
        db_session.engine = self._original_engine
        self.engine.dispose()
        self.directory.cleanup()

    def test_create_requires_create_permission(self):
        with Session(self.engine) as session, session.begin():
            consulta = resolve_current_user(session, "consulta@example.com")
            with self.assertRaises(AppError) as ctx:
                create_atencion(session, consulta, motivo_auditoria="Alta", correlation_id="c1", motivo="Prueba")
            self.assertEqual(ctx.exception.code, "FORBIDDEN")

    def test_create_rejects_unknown_field(self):
        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            with self.assertRaises(AppError) as ctx:
                create_atencion(session, ts, motivo_auditoria="Alta", correlation_id="c1", campo_inventado="x")
            self.assertEqual(ctx.exception.code, "INVALID_FIELD")

    def test_create_writes_one_audit_row_and_update_requires_expected_version(self):
        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            record = create_atencion(session, ts, motivo_auditoria="Alta", correlation_id="c1", motivo="Prueba")
            id_atencion, version = record.id_atencion, record.version
        with Session(self.engine) as session:
            audits = session.query(Auditoria).filter_by(tabla="atenciones", id_registro=id_atencion).all()
            self.assertTrue(any(a.campo == "motivo" and a.valor_nuevo == "Prueba" for a in audits))

        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            with self.assertRaises(AppError) as ctx:
                update_atencion(session, ts, id_atencion, expected_version=None,
                                 motivo_auditoria="Edicion", correlation_id="c2", motivo="Otro")
            self.assertEqual(ctx.exception.code, "EXPECTED_VERSION_REQUIRED")

        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            with self.assertRaises(AppError) as ctx:
                update_atencion(session, ts, id_atencion, expected_version=version + 1,
                                 motivo_auditoria="Edicion", correlation_id="c2", motivo="Otro")
            self.assertEqual(ctx.exception.code, "VERSION_CONFLICT")

        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            update_atencion(session, ts, id_atencion, expected_version=version,
                             motivo_auditoria="Edicion", correlation_id="c3", motivo="Correcto")
        with Session(self.engine) as session:
            self.assertEqual(session.get(Atencion, id_atencion).motivo, "Correcto")

    def test_trabajador_social_cannot_soft_delete(self):
        # ROLE_TRABAJADOR_SOCIAL no tiene ATENCIONES:delete en el seed (security_seed.py).
        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            record = create_atencion(session, ts, motivo_auditoria="Alta", correlation_id="c1")
            id_atencion, version = record.id_atencion, record.version
        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            with self.assertRaises(AppError) as ctx:
                soft_delete_atencion(session, ts, id_atencion, expected_version=version, motivo="Duplicado",
                                      correlation_id="c2")
            self.assertEqual(ctx.exception.code, "FORBIDDEN")

    def test_soft_delete_requires_reason_for_a_role_that_can_delete(self):
        with Session(self.engine) as session, session.begin():
            session.add(User(id_usuario="admin", correo="admin@example.com", nombre="Admin",
                              rol_id="ROLE_ADMIN", estado="ACTIVO"))
            admin = resolve_current_user(session, "admin@example.com")
            record = create_atencion(session, admin, motivo_auditoria="Alta", correlation_id="c1")
            id_atencion, version = record.id_atencion, record.version
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin@example.com")
            with self.assertRaises(AppError) as ctx:
                soft_delete_atencion(session, admin, id_atencion, expected_version=version, motivo="",
                                      correlation_id="c2")
            self.assertEqual(ctx.exception.code, "DELETE_REASON_REQUIRED")
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin@example.com")
            soft_delete_atencion(session, admin, id_atencion, expected_version=version, motivo="Duplicado",
                                  correlation_id="c3")
        with Session(self.engine) as session:
            record = session.get(Atencion, id_atencion)
            self.assertTrue(record.eliminado)
            self.assertEqual(record.motivo_eliminacion, "Duplicado")

    def test_restore_clears_deletion_metadata(self):
        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            record = create_atencion(session, ts, motivo_auditoria="Alta", correlation_id="c1")
            id_atencion = record.id_atencion
            session.add(User(id_usuario="admin", correo="admin@example.com", nombre="Admin",
                              rol_id="ROLE_ADMIN", estado="ACTIVO"))
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin@example.com")
            record = session.get(Atencion, id_atencion)
            soft_delete_atencion(session, admin, id_atencion, expected_version=record.version,
                                  motivo="Ya no aplica", correlation_id="c2")
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin@example.com")
            restore_atencion(session, admin, id_atencion, correlation_id="c3")
        with Session(self.engine) as session:
            record = session.get(Atencion, id_atencion)
            self.assertFalse(record.eliminado)
            self.assertTrue(record.activo)
            self.assertIsNone(record.motivo_eliminacion)

    def test_history_requires_auditoria_permission(self):
        # Hallazgo H3: Base Sistema/ProcessService.gs:157 solo exigía el permiso del módulo.
        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            record = create_atencion(session, ts, motivo_auditoria="Alta", correlation_id="c1")
            id_atencion = record.id_atencion
        with Session(self.engine) as session:
            ts = resolve_current_user(session, "ts@example.com")
            # ROLE_TRABAJADOR_SOCIAL tiene ATENCIONES:read pero no AUDITORIA:read (seed).
            with self.assertRaises(AppError) as ctx:
                get_history(session, ts, "ATENCIONES", "atenciones", id_atencion)
            self.assertEqual(ctx.exception.code, "FORBIDDEN")


if __name__ == "__main__":
    unittest.main()
