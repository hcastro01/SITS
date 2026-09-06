import unittest
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.core.errors import AppError
from app.core.permissions import resolve_current_user
from app.db.session import build_engine
from app.models import Caso, Cierre, Compromiso, Derivacion, Seguimiento, User
from app.services.casos import add_compromiso, add_derivacion, add_seguimiento, close_caso, create_caso
from app.services.security_seed import seed_security


class CasosServiceTests(unittest.TestCase):
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

    def _crear_caso(self, session, user, **campos):
        return create_caso(session, user, motivo_auditoria="Apertura", correlation_id="c1", **campos)

    def test_create_generates_codigo_caso(self):
        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            caso = self._crear_caso(session, ts, responsable="Ana")
            self.assertRegex(caso.codigo_caso, r"^CAS-\d{4}-[0-9A-F]{10}$")

    def test_consulta_role_cannot_create_case(self):
        with Session(self.engine) as session, session.begin():
            consulta = resolve_current_user(session, "consulta@example.com")
            with self.assertRaises(AppError) as ctx:
                self._crear_caso(session, consulta)
            self.assertEqual(ctx.exception.code, "FORBIDDEN")

    def test_add_seguimiento_updates_case_ultimo_seguimiento_transactionally(self):
        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            caso = self._crear_caso(session, ts)
            id_caso = caso.id_caso
        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            add_seguimiento(session, ts, id_caso, correlation_id="c2", fecha="2026-09-05", descripcion="Contacto")
        with Session(self.engine) as session:
            self.assertEqual(session.get(Caso, id_caso).ultimo_seguimiento, "2026-09-05")
            self.assertEqual(session.scalar(select(func.count()).select_from(Seguimiento)), 1)

    def test_add_derivacion_sets_case_flag(self):
        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            caso = self._crear_caso(session, ts)
            id_caso = caso.id_caso
        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            add_derivacion(session, ts, id_caso, correlation_id="c2", area_destino="RRHH", motivo="Seguimiento externo")
        with Session(self.engine) as session:
            self.assertTrue(session.get(Caso, id_caso).derivacion)
            self.assertEqual(session.scalar(select(func.count()).select_from(Derivacion)), 1)

    def test_add_compromiso_defaults_creation_date(self):
        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            caso = self._crear_caso(session, ts)
            id_caso = caso.id_caso
        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            compromiso = add_compromiso(session, ts, id_caso, correlation_id="c2", responsable="Ana", descripcion="X")
            self.assertIsNotNone(compromiso.fecha_creacion_compromiso)
        with Session(self.engine) as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(Compromiso)), 1)

    def test_close_caso_updates_estado_and_rejects_double_close(self):
        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            caso = self._crear_caso(session, ts)
            id_caso, version = caso.id_caso, caso.version
        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            close_caso(session, ts, id_caso, expected_version=version, correlation_id="c2",
                       fecha_cierre_caso="2026-09-05", responsable="Ana", motivo_cierre="Resuelto")
        with Session(self.engine) as session:
            caso_cerrado = session.get(Caso, id_caso)
            self.assertEqual(caso_cerrado.estado_caso, "CERRADO")
            self.assertEqual(caso_cerrado.motivo_cierre, "Resuelto")
            nueva_version = caso_cerrado.version
        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            with self.assertRaises(AppError) as ctx:
                close_caso(session, ts, id_caso, expected_version=nueva_version, correlation_id="c3",
                           fecha_cierre_caso="2026-09-06", responsable="Ana", motivo_cierre="Otra vez")
            self.assertEqual(ctx.exception.code, "CASE_ALREADY_CLOSED")

    def test_close_caso_version_conflict_rolls_back_the_closure_too(self):
        # Demuestra la transaccionalidad: si el caso ya no coincide con expected_version,
        # ni el Cierre ni la actualizacion del caso quedan persistidos.
        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            caso = self._crear_caso(session, ts)
            id_caso, version = caso.id_caso, caso.version
        try:
            with Session(self.engine) as session, session.begin():
                ts = resolve_current_user(session, "ts@example.com")
                close_caso(session, ts, id_caso, expected_version=version + 99, correlation_id="c2",
                           fecha_cierre_caso="2026-09-05", responsable="Ana", motivo_cierre="Resuelto")
        except AppError as error:
            self.assertEqual(error.code, "VERSION_CONFLICT")
        with Session(self.engine) as session:
            self.assertEqual(session.get(Caso, id_caso).estado_caso, None)
            self.assertEqual(session.scalar(select(func.count()).select_from(Cierre)), 0)


if __name__ == "__main__":
    unittest.main()
