import unittest
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.db.session import build_engine
from app.models import Auditoria, User
from app.services.audit import log_change
from app.services.security_seed import seed_security


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.engine = build_engine(f"sqlite:///{self.directory.name}/test.db")
        self._original_engine = db_session.engine
        db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")
        with Session(self.engine) as session, session.begin():
            seed_security(session)
            session.add(User(id_usuario="u1", correo="u1@example.com", nombre="Original",
                              rol_id="ROLE_CONSULTA", estado="ACTIVO"))

    def tearDown(self):
        db_session.engine = self._original_engine
        self.engine.dispose()
        self.directory.cleanup()

    def test_writes_one_row_per_changed_field_and_redacts_sensitive_ones(self):
        with Session(self.engine) as session, session.begin():
            log_change(session, "usuarios", "u1", "CREATE", {}, {"nombre": "Ana", "cedula": "0102030405"}, "op@example.com")
        with Session(self.engine) as session:
            rows = {row.campo: row for row in session.scalars(select(Auditoria)).all()}
            self.assertEqual(set(rows), {"nombre", "cedula"})
            self.assertEqual(rows["nombre"].valor_nuevo, "Ana")
            self.assertEqual(rows["cedula"].valor_nuevo, "[VALOR SENSIBLE MODIFICADO]")

    def test_update_skips_unchanged_fields(self):
        with Session(self.engine) as session, session.begin():
            log_change(session, "usuarios", "u1", "UPDATE",
                       {"nombre": "A", "estado": "ACTIVO"}, {"nombre": "B", "estado": "ACTIVO"}, "op@example.com")
        with Session(self.engine) as session:
            rows = session.scalars(select(Auditoria)).all()
            self.assertEqual([r.campo for r in rows], ["nombre"])

    def test_update_with_no_changes_writes_a_single_wildcard_row(self):
        with Session(self.engine) as session, session.begin():
            log_change(session, "usuarios", "u1", "UPDATE", {"nombre": "A"}, {"nombre": "A"}, "op@example.com")
        with Session(self.engine) as session:
            rows = session.scalars(select(Auditoria)).all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].campo, "*")

    def test_sensitive_record_redacts_fields_outside_the_always_visible_allowlist(self):
        with Session(self.engine) as session, session.begin():
            log_change(session, "casos", "c1", "VIEW_SENSITIVE", {}, {"id_caso": "c1", "descripcion": "detalle"},
                       "op@example.com", sensitive_record=True)
        with Session(self.engine) as session:
            rows = {row.campo: row for row in session.scalars(select(Auditoria)).all()}
            self.assertEqual(rows["id_caso"].valor_nuevo, "c1")
            self.assertEqual(rows["descripcion"].valor_nuevo, "[VALOR SENSIBLE MODIFICADO]")

    def test_invalid_action_is_rejected(self):
        with Session(self.engine) as session, session.begin():
            with self.assertRaises(ValueError):
                log_change(session, "usuarios", "u1", "CAMINAR", {}, {"nombre": "Ana"}, "op@example.com")

    def test_failed_audit_rolls_back_the_whole_transaction(self):
        # Demuestra la propiedad que el legacy no podía dar (MIGRACION_FASE_1.md discrepancia D9):
        # si la auditoría falla, la mutación de dominio hecha en la misma transacción también cae.
        try:
            with Session(self.engine) as session, session.begin():
                user = session.get(User, "u1")
                user.nombre = "Nombre que no debe persistir"
                log_change(session, "usuarios", "u1", "ACCION_INVALIDA", {}, {"nombre": user.nombre}, "op@example.com")
        except ValueError:
            pass
        with Session(self.engine) as session:
            self.assertEqual(session.get(User, "u1").nombre, "Original")
            self.assertEqual(session.scalar(select(func.count()).select_from(Auditoria)), 0)


if __name__ == "__main__":
    unittest.main()
