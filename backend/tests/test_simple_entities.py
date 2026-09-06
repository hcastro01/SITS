import unittest
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.core.errors import AppError
from app.core.permissions import resolve_current_user
from app.db.session import build_engine
from app.models import Auditoria, Persona, User
from app.services.hallazgos_recorrido import hallazgos_recorrido
from app.services.novedades import novedades
from app.services.personas import personas
from app.services.recorridos import recorridos
from app.services.security_seed import MODULES, seed_security

ENTIDADES = [novedades, recorridos, hallazgos_recorrido, personas]


class SimpleEntitiesWiringTests(unittest.TestCase):
    """Cada declaración usa una tabla/módulo/columnas reales — no solo la fábrica genérica."""

    def test_modulo_is_a_known_module(self):
        for entidad in ENTIDADES:
            with self.subTest(entidad=entidad.tabla):
                self.assertIn(entidad.modulo, MODULES)

    def test_campos_are_real_model_columns(self):
        for entidad in ENTIDADES:
            columnas = {c.name for c in entidad.model.__table__.columns}
            for campo in entidad.campos:
                with self.subTest(entidad=entidad.tabla, campo=campo):
                    self.assertIn(campo, columnas)

    def test_id_field_matches_the_actual_primary_key(self):
        for entidad in ENTIDADES:
            pk_columns = {c.name for c in entidad.model.__table__.primary_key.columns}
            with self.subTest(entidad=entidad.tabla):
                self.assertEqual(pk_columns, {entidad.id_field})


class EntityServiceFactoryTests(unittest.TestCase):
    """Prueba la mecánica de la fábrica una sola vez, a fondo, usando `personas` (sin FK)."""

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
            session.add(User(id_usuario="admin", correo="admin@example.com", nombre="Admin",
                              rol_id="ROLE_ADMIN", estado="ACTIVO"))
            session.add(User(id_usuario="consulta", correo="consulta@example.com", nombre="Consulta",
                              rol_id="ROLE_CONSULTA", estado="ACTIVO"))

    def tearDown(self):
        db_session.engine = self._original_engine
        self.engine.dispose()
        self.directory.cleanup()

    def test_create_rejects_unknown_field_and_requires_permission(self):
        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            with self.assertRaises(AppError) as ctx:
                personas.create(session, ts, motivo_auditoria="Alta", correlation_id="c1", campo_x="y")
            self.assertEqual(ctx.exception.code, "INVALID_FIELD")

            consulta = resolve_current_user(session, "consulta@example.com")
            with self.assertRaises(AppError) as ctx:
                personas.create(session, consulta, motivo_auditoria="Alta", correlation_id="c1", nombre="Ana")
            self.assertEqual(ctx.exception.code, "FORBIDDEN")

    def test_full_lifecycle_create_update_conflict_delete_restore(self):
        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            creada = personas.create(session, ts, motivo_auditoria="Alta", correlation_id="c1",
                                      nombre="Ana", cedula="0102030405")
            id_persona, version = creada.id_persona, creada.version

        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            with self.assertRaises(AppError) as ctx:
                personas.update(session, ts, id_persona, expected_version=version + 1,
                                 motivo_auditoria="Edicion", correlation_id="c2", cargo="Analista")
            self.assertEqual(ctx.exception.code, "VERSION_CONFLICT")

        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            actualizada = personas.update(session, ts, id_persona, expected_version=version,
                                           motivo_auditoria="Edicion", correlation_id="c3", cargo="Analista")
            self.assertEqual(actualizada.version, version + 1)
        with Session(self.engine) as session:
            self.assertEqual(session.get(Persona, id_persona).cargo, "Analista")

        # ROLE_TRABAJADOR_SOCIAL no tiene PERSONAS:delete en el seed.
        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            with self.assertRaises(AppError) as ctx:
                personas.soft_delete(session, ts, id_persona, expected_version=version + 1,
                                      motivo="Duplicado", correlation_id="c4")
            self.assertEqual(ctx.exception.code, "FORBIDDEN")

        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin@example.com")
            with self.assertRaises(AppError) as ctx:
                personas.soft_delete(session, admin, id_persona, expected_version=version + 1,
                                      motivo="", correlation_id="c5")
            self.assertEqual(ctx.exception.code, "DELETE_REASON_REQUIRED")
        with Session(self.engine) as session:
            # La validación de motivo debe fallar sin dejar la versión a medio incrementar.
            self.assertEqual(session.get(Persona, id_persona).version, version + 1)

        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin@example.com")
            personas.soft_delete(session, admin, id_persona, expected_version=version + 1,
                                  motivo="Duplicado", correlation_id="c6")
        with Session(self.engine) as session:
            record = session.get(Persona, id_persona)
            self.assertTrue(record.eliminado)
            self.assertEqual(record.motivo_eliminacion, "Duplicado")

        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin@example.com")
            personas.restore(session, admin, id_persona, correlation_id="c7")
        with Session(self.engine) as session:
            record = session.get(Persona, id_persona)
            self.assertFalse(record.eliminado)
            self.assertIsNone(record.motivo_eliminacion)

        with Session(self.engine) as session:
            audits = session.query(Auditoria).filter_by(tabla="personas", id_registro=id_persona).all()
            acciones = {a.accion for a in audits}
            self.assertEqual(acciones, {"CREATE", "UPDATE", "DELETE", "RESTORE"})


if __name__ == "__main__":
    unittest.main()
