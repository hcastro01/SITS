import unittest
from datetime import UTC, datetime, timedelta
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.core.errors import AppError
from app.core.permissions import resolve_current_user
from app.db.session import build_engine
from app.models import Caso, Compromiso, Novedad, Permission, Recorrido, Role, Seguimiento, User
from app.services.dashboard import get_dashboard
from app.services.security_seed import ACTION_TO_FIELD, MODULES, seed_security

HOY = datetime.now(UTC).date().isoformat()
AYER = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()
MANANA = (datetime.now(UTC).date() + timedelta(days=1)).isoformat()


class DashboardServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.engine = build_engine(f"sqlite:///{self.directory.name}/test.db")
        self._original_engine = db_session.engine
        db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")
        with Session(self.engine) as session, session.begin():
            seed_security(session)
            session.add(User(id_usuario="admin", correo="admin@example.com", nombre="Admin",
                              rol_id="ROLE_ADMIN", estado="ACTIVO"))

    def tearDown(self):
        db_session.engine = self._original_engine
        self.engine.dispose()
        self.directory.cleanup()

    def _admin(self, session):
        return resolve_current_user(session, "admin@example.com")

    def test_requires_dashboard_permission(self):
        with Session(self.engine) as session, session.begin():
            session.add(Role(id_rol="ROLE_SIN_NADA", nombre="Sin permisos"))
            session.flush()
            for modulo in MODULES:
                session.add(Permission(id_permiso=f"ROLE_SIN_NADA:{modulo}", rol_id="ROLE_SIN_NADA", modulo=modulo,
                                        **dict.fromkeys(ACTION_TO_FIELD.values(), False)))
            session.add(User(id_usuario="nadie", correo="nadie@example.com", nombre="Nadie",
                              rol_id="ROLE_SIN_NADA", estado="ACTIVO"))
        with Session(self.engine) as session, session.begin():
            nadie = resolve_current_user(session, "nadie@example.com")
            with self.assertRaises(AppError) as ctx:
                get_dashboard(session, nadie)
            self.assertEqual(ctx.exception.code, "FORBIDDEN")

    def test_computes_case_counts_by_status_and_excludes_deleted(self):
        with Session(self.engine) as session, session.begin():
            session.add(Caso(id_caso="c1", codigo_caso="CAS-1", estado_caso="Abierto"))
            session.add(Caso(id_caso="c2", codigo_caso="CAS-2", estado_caso="CERRADO"))
            session.add(Caso(id_caso="c3", codigo_caso="CAS-3", estado_caso="borrador"))
            session.add(Caso(id_caso="c4", codigo_caso="CAS-4", estado_caso="Abierto",
                              eliminado=True, motivo_eliminacion="prueba"))
        with Session(self.engine) as session, session.begin():
            admin = self._admin(session)
            datos = get_dashboard(session, admin)
            self.assertEqual(datos["casesOpen"], 2)  # c1 (Abierto) + c3 (borrador, no está en CERRADO/INACTIVO)
            self.assertEqual(datos["casesClosed"], 1)
            self.assertEqual(datos["casesPending"], 1)  # c3 (BORRADOR)

    def test_upcoming_followups_excludes_past_dates_and_closed_status(self):
        with Session(self.engine) as session, session.begin():
            session.add(Caso(id_caso="c1", codigo_caso="CAS-1"))
            session.flush()
            session.add(Seguimiento(id_seguimiento="s1", id_caso="c1", fecha_proxima_accion=MANANA, estado="ABIERTO"))
            session.add(Seguimiento(id_seguimiento="s2", id_caso="c1", fecha_proxima_accion=AYER, estado="ABIERTO"))
            session.add(Seguimiento(id_seguimiento="s3", id_caso="c1", fecha_proxima_accion=MANANA, estado="CERRADO"))
            session.add(Seguimiento(id_seguimiento="s4", id_caso="c1", fecha_proxima_accion=HOY, estado="ABIERTO"))
        with Session(self.engine) as session, session.begin():
            admin = self._admin(session)
            datos = get_dashboard(session, admin)
            self.assertEqual(datos["upcomingFollowUps"], 2)  # s1 y s4

    def test_overdue_commitments_excludes_completed_states(self):
        with Session(self.engine) as session, session.begin():
            session.add(Caso(id_caso="c1", codigo_caso="CAS-1"))
            session.flush()
            session.add(Compromiso(id_compromiso="cp1", id_caso="c1", fecha_limite=AYER, estado="PENDIENTE"))
            session.add(Compromiso(id_compromiso="cp2", id_caso="c1", fecha_limite=AYER, estado="CUMPLIDO"))
            session.add(Compromiso(id_compromiso="cp3", id_caso="c1", fecha_limite=MANANA, estado="PENDIENTE"))
        with Session(self.engine) as session, session.begin():
            admin = self._admin(session)
            datos = get_dashboard(session, admin)
            self.assertEqual(datos["overdueCommitments"], 1)  # cp1

    def test_pending_news_excludes_closed_and_resolved(self):
        with Session(self.engine) as session, session.begin():
            session.add(Novedad(id_novedad="n1", estado="ABIERTA"))
            session.add(Novedad(id_novedad="n2", estado="CERRADO"))
            session.add(Novedad(id_novedad="n3", estado="RESUELTO"))
        with Session(self.engine) as session, session.begin():
            admin = self._admin(session)
            datos = get_dashboard(session, admin)
            self.assertEqual(datos["pendingNews"], 1)  # n1

    def test_tours_completed_counts_only_active_recorridos(self):
        with Session(self.engine) as session, session.begin():
            session.add(Recorrido(id_recorrido="r1"))
            session.add(Recorrido(id_recorrido="r2"))
            session.add(Recorrido(id_recorrido="r3", eliminado=True, motivo_eliminacion="prueba"))
        with Session(self.engine) as session, session.begin():
            admin = self._admin(session)
            datos = get_dashboard(session, admin)
            self.assertEqual(datos["toursCompleted"], 2)

    def test_only_includes_metrics_for_permitted_modules(self):
        with Session(self.engine) as session, session.begin():
            session.add(Role(id_rol="ROLE_SOLO_CASOS", nombre="Solo casos"))
            session.flush()
            for modulo in MODULES:
                permitido = modulo in {"DASHBOARD", "CASOS"}
                session.add(Permission(
                    id_permiso=f"ROLE_SOLO_CASOS:{modulo}", rol_id="ROLE_SOLO_CASOS", modulo=modulo,
                    **{ACTION_TO_FIELD["read"]: permitido, **{v: False for k, v in ACTION_TO_FIELD.items() if k != "read"}},
                ))
            session.add(User(id_usuario="limitado", correo="limitado@example.com", nombre="Limitado",
                              rol_id="ROLE_SOLO_CASOS", estado="ACTIVO"))
            session.add(Caso(id_caso="c1", codigo_caso="CAS-1", estado_caso="Abierto"))
        with Session(self.engine) as session, session.begin():
            limitado = resolve_current_user(session, "limitado@example.com")
            datos = get_dashboard(session, limitado)
            self.assertIn("casesOpen", datos)
            self.assertNotIn("upcomingFollowUps", datos)
            self.assertNotIn("overdueCommitments", datos)
            self.assertNotIn("pendingNews", datos)
            self.assertNotIn("toursCompleted", datos)
            self.assertIn("generatedAt", datos)


if __name__ == "__main__":
    unittest.main()
