import unittest
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.core.errors import AppError
from app.core.permissions import resolve_current_user
from app.db.session import build_engine
from app.models import Persona, User
from app.services.actividades import create_actividad, is_overdue, list_actividades, soft_delete_actividad, update_actividad
from app.services.security_seed import seed_security


class ActividadesServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.engine = build_engine(f"sqlite:///{self.directory.name}/test.db")
        self.original_engine = db_session.engine
        db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")
        with Session(self.engine) as session, session.begin():
            seed_security(session)
            session.add_all([
                User(id_usuario="admin", correo="admin@example.com", nombre="Admin", rol_id="ROLE_ADMIN", estado="ACTIVO"),
                User(id_usuario="responsable", correo="responsable@example.com", nombre="Responsable", rol_id="ROLE_ADMIN", estado="ACTIVO"),
                User(id_usuario="inactivo", correo="inactivo@example.com", nombre="Inactivo", rol_id="ROLE_ADMIN", estado="INACTIVO"),
                User(id_usuario="consulta", correo="consulta@example.com", nombre="Consulta", rol_id="ROLE_CONSULTA", estado="ACTIVO"),
                Persona(id_persona="persona", nombre="Persona de prueba", cedula="0102030405", area="Operaciones"),
            ])

    def tearDown(self):
        db_session.engine = self.original_engine
        self.engine.dispose()
        self.directory.cleanup()

    def user(self, session, correo="admin@example.com"):
        return resolve_current_user(session, correo)

    def create(self, session, user=None, **fields):
        values = {
            "nombre": "Actividad base", "descripcion": "Descripción base", "responsable_id": "responsable",
            "tipo_fecha": "LIMITE", "fecha_objetivo": "2026-10-15", "estado": "PENDIENTE",
        }
        values.update(fields)
        return create_actividad(session, user or self.user(session), motivo_auditoria="Alta", correlation_id="test", **values)

    def test_creates_valid_activity_with_session_author_and_optional_person(self):
        with Session(self.engine) as session, session.begin():
            activity = self.create(session, persona_id="persona")
            without_person = self.create(session, nombre="Sin persona")
            self.assertEqual(activity.creado_por_id, "admin")
            self.assertEqual(activity.responsable_id, "responsable")
            self.assertEqual(activity.persona_id, "persona")
            self.assertEqual(activity.version, 1)
            self.assertIsNone(without_person.persona_id)

    def test_required_fields_and_author_spoofing_are_rejected(self):
        with Session(self.engine) as session, session.begin():
            for field in ("nombre", "descripcion"):
                with self.subTest(field=field), self.assertRaises(AppError) as ctx:
                    self.create(session, **{field: " "})
                self.assertEqual(ctx.exception.code, "INVALID_INPUT")
            with self.assertRaises(AppError) as ctx:
                create_actividad(session, self.user(session), motivo_auditoria="Alta", correlation_id="test", nombre="Solo nombre")
            self.assertEqual(ctx.exception.code, "INVALID_INPUT")
            with self.assertRaises(AppError) as ctx:
                self.create(session, creado_por_id="responsable")
            self.assertEqual(ctx.exception.code, "INVALID_FIELD")

    def test_responsible_must_exist_and_be_active(self):
        with Session(self.engine) as session, session.begin():
            for responsible_id in ("nadie", "inactivo"):
                with self.subTest(responsible_id=responsible_id), self.assertRaises(AppError) as ctx:
                    self.create(session, responsable_id=responsible_id)
                self.assertEqual(ctx.exception.code, "RESPONSABLE_INVALIDO")

    def test_listing_pagination_search_and_all_filters(self):
        with Session(self.engine) as session, session.begin():
            first = self.create(session, nombre="Llamar a Ana", descripcion="Seguimiento", responsable_id="admin",
                                tipo_fecha="LIMITE", fecha_objetivo="2026-09-10", estado="PENDIENTE")
            second = self.create(session, nombre="Visita", descripcion="Caso prioritario", responsable_id="responsable",
                                 tipo_fecha="PROGRAMADA", fecha_objetivo="2026-09-20", estado="EN_PROCESO")
            third = self.create(session, nombre="Cerrar informe", descripcion="Informe final", responsable_id="responsable",
                                tipo_fecha="LIMITE", fecha_objetivo="2026-10-20", estado="COMPLETADA")
            user = self.user(session)
            rows, total = list_actividades(session, user, search=None, responsable_id=None, estado=None,
                                           tipo_fecha=None, desde=None, hasta=None, mis_actividades=False, limit=2, offset=0)
            self.assertEqual((len(rows), total), (2, 3))
            rows, total = list_actividades(session, user, search="prioritario", responsable_id=None, estado=None,
                                           tipo_fecha=None, desde=None, hasta=None, mis_actividades=False, limit=25, offset=0)
            self.assertEqual(([row.id_actividad for row in rows], total), ([second.id_actividad], 1))
            for filters, expected in (
                ({"responsable_id": "responsable"}, {second.id_actividad, third.id_actividad}),
                ({"estado": "EN_PROCESO"}, {second.id_actividad}),
                ({"tipo_fecha": "PROGRAMADA"}, {second.id_actividad}),
                ({"desde": "2026-10-01"}, {third.id_actividad}),
                ({"hasta": "2026-09-15"}, {first.id_actividad}),
            ):
                query = {"search": None, "responsable_id": None, "estado": None, "tipo_fecha": None,
                         "desde": None, "hasta": None, "mis_actividades": False, "limit": 25, "offset": 0}
                query.update(filters)
                rows, total = list_actividades(session, user, **query)
                self.assertEqual(({row.id_actividad for row in rows}, total), (expected, len(expected)))
            rows, total = list_actividades(session, user, search=None, responsable_id="responsable", estado="EN_PROCESO",
                                           tipo_fecha="PROGRAMADA", desde="2026-09-15", hasta="2026-09-30",
                                           mis_actividades=False, limit=25, offset=0)
            self.assertEqual(([row.id_actividad for row in rows], total), ([second.id_actividad], 1))
            rows, total = list_actividades(session, user, search=None, responsable_id=None, estado=None,
                                           tipo_fecha=None, desde=None, hasta=None, mis_actividades=True, limit=25, offset=0)
            self.assertEqual(([row.id_actividad for row in rows], total), ([first.id_actividad], 1))
            self.assertIsNotNone(third.id_actividad)

    def test_edit_completion_sets_finalization_and_reopening_clears_it(self):
        with Session(self.engine) as session, session.begin():
            activity = self.create(session)
            completed = update_actividad(session, self.user(session), activity.id_actividad, expected_version=1,
                                         motivo_auditoria="Completar", correlation_id="test", estado="COMPLETADA",
                                         nombre="Actividad editada")
            self.assertEqual(completed.nombre, "Actividad editada")
            self.assertEqual(completed.estado, "COMPLETADA")
            self.assertIsNotNone(completed.fecha_finalizacion)
            reopened = update_actividad(session, self.user(session), activity.id_actividad, expected_version=2,
                                        motivo_auditoria="Reabrir", correlation_id="test", estado="EN_PROCESO")
            self.assertIsNone(reopened.fecha_finalizacion)

    def test_archiving_is_logical_and_excluded_from_active_listing(self):
        with Session(self.engine) as session, session.begin():
            activity = self.create(session)
            archived = soft_delete_actividad(session, self.user(session), activity.id_actividad, expected_version=1,
                                             motivo="Duplicada", correlation_id="test")
            self.assertTrue(archived.eliminado)
            self.assertFalse(archived.activo)
            rows, total = list_actividades(session, self.user(session), search=None, responsable_id=None, estado=None,
                                           tipo_fecha=None, desde=None, hasta=None, mis_actividades=False, limit=25, offset=0)
            self.assertEqual((rows, total), ([], 0))

    def test_permissions_are_enforced(self):
        with Session(self.engine) as session, session.begin():
            consulta = self.user(session, "consulta@example.com")
            with self.assertRaises(AppError) as ctx:
                self.create(session, user=consulta)
            self.assertEqual(ctx.exception.code, "FORBIDDEN")
            with self.assertRaises(AppError) as ctx:
                list_actividades(session, consulta, search=None, responsable_id=None, estado=None,
                                 tipo_fecha=None, desde=None, hasta=None, mis_actividades=False, limit=25, offset=0)
            self.assertEqual(ctx.exception.code, "FORBIDDEN")

    def test_the_four_overdue_rules(self):
        today = datetime.now(ZoneInfo("America/Guayaquil")).date()
        def activity(kind, target, state):
            return type("Activity", (), {"tipo_fecha": kind, "fecha_objetivo": target.isoformat(), "estado": state})()
        self.assertTrue(is_overdue(activity("LIMITE", today - timedelta(days=1), "PENDIENTE")))
        self.assertFalse(is_overdue(activity("LIMITE", today, "PENDIENTE")))
        self.assertFalse(is_overdue(activity("PROGRAMADA", today - timedelta(days=1), "PENDIENTE")))
        self.assertFalse(is_overdue(activity("LIMITE", today - timedelta(days=1), "COMPLETADA")))
