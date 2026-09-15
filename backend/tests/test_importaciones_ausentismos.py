import unittest
from io import BytesIO
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from openpyxl import Workbook
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.core.errors import AppError
from app.core.permissions import resolve_current_user
from app.db.session import build_engine
from app.models import Ausentismo, ErrorImportacionAusentismo, LoteImportacionAusentismo, Persona, User
from app.services.importaciones_ausentismos import (
    analizar_archivo_ausentismos, confirmar_lote_ausentismos, leer_xlsx,
    listar_errores_lote_ausentismos, listar_lotes_ausentismos, obtener_lote_ausentismos,
)
from app.services.security_seed import seed_security


HEADERS = ["cedula", "fecha_inicio", "fecha_fin", "tipo_ausentismo", "motivo", "observacion"]


def xlsx(rows, headers=HEADERS):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    stream = BytesIO()
    workbook.save(stream)
    workbook.close()
    return stream.getvalue()


class ImportacionesAusentismosTests(unittest.TestCase):
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

    def content(self, rows=None, headers=HEADERS):
        return xlsx(rows or [["0012345678", "2026-09-01", "2026-09-02", "MEDICO", "Consulta", "Certificado"]], headers)

    def analyze(self, session, rows=None, headers=HEADERS, correo="admin@example.com"):
        return analizar_archivo_ausentismos(
            session, self.user(session, correo), nombre_archivo="ausentismos.xlsx", contenido=self.content(rows, headers), correlation_id="test",
        )

    def test_valid_xlsx_creates_preview_without_inserting_absences(self):
        with Session(self.engine) as session, session.begin():
            lote, preview = self.analyze(session)
            self.assertEqual((lote.estado, lote.total_filas, lote.filas_validas), ("ANALIZADO", 1, 1))
            self.assertTrue(preview.puede_confirmarse)
            self.assertEqual(session.scalars(select(Ausentismo)).all(), [])

    def test_missing_header_rejects_file(self):
        with Session(self.engine) as session, session.begin(), self.assertRaises(AppError) as ctx:
            self.analyze(session, headers=["cedula", "fecha_inicio", "fecha_fin", "tipo_ausentismo", "observacion"])
        self.assertEqual(ctx.exception.code, "INVALID_IMPORT_HEADERS")

    def test_empty_xlsx_is_rejected(self):
        with self.assertRaises(AppError) as ctx:
            leer_xlsx(xlsx([]))
        self.assertEqual(ctx.exception.code, "EMPTY_IMPORT_FILE")

    def test_unknown_person_is_persisted_as_row_error(self):
        with Session(self.engine) as session, session.begin():
            lote, _ = self.analyze(session, rows=[["no-existe", "2026-09-01", "2026-09-02", "MEDICO", "Consulta", None]])
            errors = session.scalars(select(ErrorImportacionAusentismo).where(ErrorImportacionAusentismo.lote_id == lote.id_lote)).all()
            self.assertEqual((lote.filas_con_error, len(errors), errors[0].codigo), (1, 1, "VALIDACION"))
            self.assertNotIn("no-existe", errors[0].datos_fila)

    def test_ambiguous_person_is_an_error(self):
        with Session(self.engine) as session, session.begin():
            session.add(Persona(id_persona="persona-duplicada", nombre="Duplicada", cedula="0012345678"))
            lote, preview = self.analyze(session)
            self.assertEqual((lote.filas_con_error, preview.filas[0].estado), (1, "ERROR"))

    def test_invalid_date_is_an_error(self):
        with Session(self.engine) as session, session.begin():
            lote, _ = self.analyze(session, rows=[["0012345678", "invalida", "2026-09-02", "MEDICO", "Consulta", None]])
            self.assertEqual(lote.filas_con_error, 1)

    def test_end_date_before_start_is_an_error(self):
        with Session(self.engine) as session, session.begin():
            lote, _ = self.analyze(session, rows=[["0012345678", "2026-09-03", "2026-09-02", "MEDICO", "Consulta", None]])
            self.assertEqual(lote.filas_con_error, 1)

    def test_database_duplicate_is_persisted_as_duplicate_incidence(self):
        with Session(self.engine) as session, session.begin():
            session.add(Ausentismo(id_ausentismo="existente", persona_id="persona-uno", fecha_inicio="2026-09-01", fecha_fin="2026-09-02", tipo_ausentismo="MEDICO", motivo="Previo"))
            lote, _ = self.analyze(session)
            error = session.scalar(select(ErrorImportacionAusentismo).where(ErrorImportacionAusentismo.lote_id == lote.id_lote))
            self.assertEqual((lote.filas_duplicadas, error.codigo), (1, "DUPLICADO"))

    def test_duplicate_inside_xlsx_is_persisted_as_duplicate_incidence(self):
        with Session(self.engine) as session, session.begin():
            lote, _ = self.analyze(session, rows=[
                ["0012345678", "2026-09-01", "2026-09-02", "MEDICO", "Primero", None],
                ["0012345678", "2026-09-01", "2026-09-02", "MEDICO", "Segundo", None],
            ])
            self.assertEqual((lote.filas_validas, lote.filas_duplicadas), (1, 1))

    def test_error_lote_cannot_be_confirmed(self):
        with Session(self.engine) as session, session.begin():
            lote, _ = self.analyze(session, rows=[["invalida", "2026-09-01", "2026-09-02", "MEDICO", "Consulta", None]])
            with self.assertRaises(AppError) as ctx:
                confirmar_lote_ausentismos(session, self.user(session), lote.id_lote, correlation_id="test")
            self.assertEqual(ctx.exception.code, "IMPORT_NOT_CONFIRMABLE")
            self.assertEqual(session.scalars(select(Ausentismo)).all(), [])

    def test_valid_lote_confirms_all_rows_transactionally(self):
        with Session(self.engine) as session, session.begin():
            lote, _ = self.analyze(session, rows=[
                ["0012345678", "2026-09-01", "2026-09-02", "MEDICO", "Consulta", None],
                ["0098765432", "2026-09-03", "2026-09-03", "PERSONAL", "Permiso", "Breve"],
            ])
            confirmed = confirmar_lote_ausentismos(session, self.user(session), lote.id_lote, correlation_id="test")
            self.assertEqual((confirmed.estado, confirmed.filas_importadas, len(session.scalars(select(Ausentismo)).all())), ("CONFIRMADO", 2, 2))

    def test_persistence_failure_rolls_back_every_absence(self):
        with Session(self.engine) as session, session.begin():
            lote, _ = self.analyze(session)
            user = self.user(session)
            def fail_insert(*_):
                raise IntegrityError("insert", {}, Exception("forced"))
            event.listen(Ausentismo, "before_insert", fail_insert)
            try:
                with self.assertRaises(AppError) as ctx:
                    confirmar_lote_ausentismos(session, user, lote.id_lote, correlation_id="test")
            finally:
                event.remove(Ausentismo, "before_insert", fail_insert)
            self.assertEqual(ctx.exception.code, "IMPORT_PERSISTENCE_FAILED")
        with Session(self.engine) as session:
            self.assertEqual(session.scalars(select(Ausentismo)).all(), [])

    def test_lote_cannot_be_confirmed_twice(self):
        with Session(self.engine) as session, session.begin():
            lote, _ = self.analyze(session)
            confirmar_lote_ausentismos(session, self.user(session), lote.id_lote, correlation_id="test")
            with self.assertRaises(AppError) as ctx:
                confirmar_lote_ausentismos(session, self.user(session), lote.id_lote, correlation_id="test")
            self.assertEqual(ctx.exception.code, "IMPORT_ALREADY_CONFIRMED")

    def test_history_is_paginated(self):
        with Session(self.engine) as session, session.begin():
            first, _ = self.analyze(session, rows=[["0012345678", "2026-09-01", "2026-09-01", "MEDICO", "Uno", None]])
            second, _ = self.analyze(session, rows=[["0098765432", "2026-09-02", "2026-09-02", "MEDICO", "Dos", None]])
            lots, total = listar_lotes_ausentismos(session, self.user(session), limit=1, offset=1)
            self.assertEqual((total, len(lots)), (2, 1))
            self.assertIn(lots[0].id_lote, {first.id_lote, second.id_lote})

    def test_detail_returns_lote(self):
        with Session(self.engine) as session, session.begin():
            lote, _ = self.analyze(session)
            self.assertEqual(obtener_lote_ausentismos(session, self.user(session), lote.id_lote).id_lote, lote.id_lote)

    def test_error_pagination(self):
        with Session(self.engine) as session, session.begin():
            lote, _ = self.analyze(session, rows=[
                ["invalida", "2026-09-01", "2026-09-02", "MEDICO", "Uno", None],
                ["invalida-dos", "2026-09-03", "2026-09-04", "MEDICO", "Dos", None],
            ])
            errors, total = listar_errores_lote_ausentismos(session, self.user(session), lote.id_lote, limit=1, offset=1)
            self.assertEqual((total, len(errors)), (2, 1))

    def test_permissions_apply_to_analysis_confirmation_and_history(self):
        with Session(self.engine) as session, session.begin():
            with self.assertRaises(AppError) as ctx:
                self.analyze(session, correo="consulta@example.com")
            self.assertEqual(ctx.exception.code, "FORBIDDEN")
            lote, _ = self.analyze(session)
            with self.assertRaises(AppError) as ctx:
                listar_lotes_ausentismos(session, self.user(session, "consulta@example.com"), limit=25, offset=0)
            self.assertEqual(ctx.exception.code, "FORBIDDEN")
            self.assertIsNotNone(lote.id_lote)

    def test_counts_keep_valid_error_and_duplicate_categories(self):
        with Session(self.engine) as session, session.begin():
            lote, preview = self.analyze(session, rows=[
                ["0012345678", "2026-09-01", "2026-09-01", "MEDICO", "Valida", None],
                ["0012345678", "2026-09-01", "2026-09-01", "MEDICO", "Duplicada", None],
                ["inexistente", "2026-09-01", "2026-09-01", "MEDICO", "Error", None],
            ])
            self.assertEqual((lote.total_filas, lote.filas_validas, lote.filas_duplicadas, lote.filas_con_error), (3, 1, 1, 1))
            self.assertFalse(preview.puede_confirmarse)
