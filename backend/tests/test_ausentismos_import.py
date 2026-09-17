import unittest
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.core.errors import AppError
from app.core.permissions import resolve_current_user
from app.db.session import build_engine
from app.models import Ausentismo, Persona, User
from app.services.ausentismos import analizar_importacion_ausentismos
from app.services.security_seed import seed_security


HEADERS = ["cedula", "fecha_inicio", "fecha_fin", "tipo_ausentismo", "motivo", "observacion"]


class AusentismosImportTests(unittest.TestCase):
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
                User(id_usuario="consulta", correo="consulta@example.com", nombre="Consulta", rol_id="ROLE_CONSULTA", estado="ACTIVO"),
                Persona(id_persona="persona-uno", nombre="Una", cedula="0012345678"),
                Persona(id_persona="persona-dos", nombre="Dos", cedula="0098765432"),
            ])

    def tearDown(self):
        db_session.engine = self.original_engine
        self.engine.dispose()
        self.directory.cleanup()

    def user(self, session, correo="admin@example.com"):
        return resolve_current_user(session, correo)

    def analyze(self, session, headers=HEADERS, rows=None, correo="admin@example.com"):
        rows = rows if rows is not None else [["0012345678", "2026-09-01", "2026-09-02", "MEDICO", "Consulta", "Con certificado"]]
        return analizar_importacion_ausentismos(session, self.user(session, correo), encabezados=headers, filas=rows)

    def test_canonical_headers_allow_only_external_whitespace(self):
        with Session(self.engine) as session:
            result = self.analyze(session, headers=[f"  {header}  " for header in HEADERS])
            self.assertEqual(result.encabezados, tuple(HEADERS))
            for headers in (
                ["cedula", "fecha_inicio", "fecha_fin", "tipo", "motivo"],
                ["cedula", "fecha_inicio", "fecha_fin", "tipo_ausentismo", "motivo", "extra"],
                ["cedula", "fecha_inicio", "fecha_fin", "tipo_ausentismo", "motivo", "motivo"],
            ):
                with self.subTest(headers=headers), self.assertRaises(AppError) as ctx:
                    self.analyze(session, headers=headers)
                self.assertEqual(ctx.exception.code, "INVALID_IMPORT_HEADERS")

    def test_valid_row_resolves_person_by_text_cedula_and_preserves_zeroes(self):
        with Session(self.engine) as session:
            result = self.analyze(session)
            row = result.filas[0]
            self.assertEqual((result.total_filas, result.filas_validas, result.filas_con_error), (1, 1, 0))
            self.assertTrue(result.puede_confirmarse)
            self.assertEqual((row.estado, row.cedula, row.persona_id), ("VALIDA", "0012345678", "persona-uno"))

    def test_missing_or_ambiguous_person_is_an_error(self):
        with Session(self.engine) as session, session.begin():
            session.add(Persona(id_persona="persona-duplicada", nombre="Duplicada", cedula="0012345678"))
            result = self.analyze(session, rows=[
                ["no-existe", "2026-09-01", "2026-09-02", "MEDICO", "Consulta", None],
                ["0012345678", "2026-09-01", "2026-09-02", "MEDICO", "Consulta", None],
            ])
            self.assertEqual([row.estado for row in result.filas], ["ERROR", "ERROR"])
            self.assertIn("No existe una Persona activa", result.filas[0].errores[0])
            self.assertIn("más de una Persona", result.filas[1].errores[0])
            self.assertFalse(result.puede_confirmarse)

    def test_required_fields_dates_and_date_range_are_validated(self):
        with Session(self.engine) as session:
            result = self.analyze(session, rows=[
                ["0012345678", "invalida", "2026-09-02", "", "", None],
                ["0012345678", "2026-09-03", "2026-09-02", "MEDICO", "Consulta", None],
            ])
            self.assertEqual([row.estado for row in result.filas], ["ERROR", "ERROR"])
            self.assertTrue(any("fecha_inicio" in error for error in result.filas[0].errores))
            self.assertTrue(any("tipo_ausentismo" in error for error in result.filas[0].errores))
            self.assertTrue(any("motivo" in error for error in result.filas[0].errores))
            self.assertTrue(any("fecha_fin no puede ser anterior" in error for error in result.filas[1].errores))

    def test_persisted_duplicate_uses_only_approved_functional_key(self):
        with Session(self.engine) as session, session.begin():
            session.add(Ausentismo(
                id_ausentismo="existente", persona_id="persona-uno", fecha_inicio="2026-09-01", fecha_fin="2026-09-02",
                tipo_ausentismo="MEDICO", motivo="Motivo anterior", observacion="Otra observación",
            ))
            result = self.analyze(session, rows=[["0012345678", "2026-09-01", "2026-09-02", "MEDICO", "Motivo nuevo", "Nueva observación"]])
            self.assertEqual((result.filas[0].estado, result.filas_duplicadas), ("DUPLICADA", 1))
            self.assertFalse(result.puede_confirmarse)

    def test_duplicate_inside_same_file_is_reported_before_confirmation(self):
        with Session(self.engine) as session:
            result = self.analyze(session, rows=[
                ["0012345678", "2026-09-01", "2026-09-02", "MEDICO", "Consulta", None],
                ["0012345678", "2026-09-01", "2026-09-02", "MEDICO", "Otro motivo", "Otra observación"],
            ])
            self.assertEqual([row.estado for row in result.filas], ["VALIDA", "DUPLICADA"])
            self.assertEqual((result.filas_validas, result.filas_duplicadas), (1, 1))
            self.assertFalse(result.puede_confirmarse)

    def test_optional_observation_is_not_required(self):
        with Session(self.engine) as session:
            result = self.analyze(session, headers=HEADERS[:-1], rows=[["0098765432", "2026-09-01", "2026-09-01", "PERSONAL", "Permiso"]])
            self.assertEqual((result.filas[0].estado, result.filas[0].observacion), ("VALIDA", None))

    def test_analysis_requires_both_existing_create_permissions(self):
        with Session(self.engine) as session:
            with self.assertRaises(AppError) as ctx:
                self.analyze(session, correo="consulta@example.com")
            self.assertEqual(ctx.exception.code, "FORBIDDEN")
