import unittest
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.core.errors import AppError
from app.core.permissions import resolve_current_user
from app.db.session import build_engine
from app.models import User
from app.services.casos import add_seguimiento, create_caso
from app.services.export import csv_escape, export_search_results
from app.services.search import search
from app.services.security_seed import seed_security


class SearchServiceTests(unittest.TestCase):
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
            ts = resolve_current_user(session, "ts@example.com")
            caso = create_caso(session, ts, motivo_auditoria="Alta", correlation_id="c0",
                                responsable="Ana", estado_caso="ABIERTO")
            self.id_caso = caso.id_caso
            add_seguimiento(session, ts, self.id_caso, correlation_id="c0b",
                             fecha="2026-09-01", descripcion="Contacto inicial con la persona")

    def tearDown(self):
        db_session.engine = self._original_engine
        self.engine.dispose()
        self.directory.cleanup()

    def test_search_finds_case_by_text_query(self):
        with Session(self.engine) as session:
            ts = resolve_current_user(session, "ts@example.com")
            resultado = search(session, ts, tablas=["casos"], q="ana")
            self.assertEqual(resultado["total"], 1)
            self.assertEqual(resultado["items"][0]["id"], self.id_caso)

    def test_search_is_accent_insensitive_and_treats_wildcards_as_text(self):
        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            special = create_caso(
                session, ts, motivo_auditoria="Alta", correlation_id="special",
                responsable="Ángela_100%", estado_caso="ABIERTO",
            )
            special_id = special.id_caso
        with Session(self.engine) as session:
            ts = resolve_current_user(session, "ts@example.com")
            by_name = search(session, ts, tablas=["casos"], q="angela_100%")
            self.assertEqual([item["id"] for item in by_name["items"]], [special_id])
            by_percent = search(session, ts, tablas=["casos"], q="%")
            self.assertEqual([item["id"] for item in by_percent["items"]], [special_id])

    def test_search_keeps_an_exact_total_while_paginating_candidates(self):
        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            for index in range(5):
                create_caso(
                    session, ts, motivo_auditoria="Alta", correlation_id=f"page-{index}",
                    responsable=f"Persona {index}", estado_caso="ABIERTO",
                )
        with Session(self.engine) as session:
            ts = resolve_current_user(session, "ts@example.com")
            result = search(session, ts, tablas=["casos"], pagina=2, tamano_pagina=2)
            self.assertEqual(result["total"], 6)
            self.assertEqual(result["total_paginas"], 3)
            self.assertEqual(len(result["items"]), 2)

    def test_search_skips_tables_without_read_permission(self):
        with Session(self.engine) as session:
            consulta = resolve_current_user(session, "consulta@example.com")
            # ROLE_CONSULTA no tiene RESPUESTAS ni REPORTES, pero sí CASOS/ATENCIONES/etc.
            resultado = search(session, consulta, tablas=["casos"], q="ana")
            self.assertEqual(resultado["total"], 1)

    def test_search_rejects_unknown_table(self):
        with Session(self.engine) as session:
            ts = resolve_current_user(session, "ts@example.com")
            with self.assertRaises(AppError) as ctx:
                search(session, ts, tablas=["documentos"], q="")
            self.assertEqual(ctx.exception.code, "INVALID_ENTITY")

    def test_non_sensitive_case_is_fully_visible_to_a_role_without_sensitive_rights(self):
        # NIVEL_SENSIBILIDAD no está sembrado (hallazgo H2): ningún caso es sensible todavía,
        # así que incluso ROLE_CONSULTA (sin CASOS:sensitive) ve el registro completo.
        with Session(self.engine) as session:
            consulta = resolve_current_user(session, "consulta@example.com")
            resultado = search(session, consulta, tablas=["casos"], q="")
            item = resultado["items"][0]
            self.assertFalse(item["sensible"])
            self.assertFalse(item["restringido"])
            self.assertIn("colaborador", item["registro"])

    def test_export_requires_reportes_export_permission(self):
        with Session(self.engine) as session:
            consulta = resolve_current_user(session, "consulta@example.com")
            with self.assertRaises(AppError) as ctx:
                export_search_results(session, consulta, tablas=["casos"])
            self.assertEqual(ctx.exception.code, "FORBIDDEN")

    def test_export_produces_csv_with_header(self):
        with Session(self.engine) as session:
            ts = resolve_current_user(session, "ts@example.com")
            csv_text, truncado = export_search_results(session, ts, tablas=["casos"])
            self.assertFalse(truncado)
            self.assertTrue(csv_text.startswith("tabla,id,fecha,sensible,restringido\r\n"))
            self.assertIn(self.id_caso, csv_text)


class CsvEscapeTests(unittest.TestCase):
    def test_neutralizes_formula_prefix_at_position_zero(self):
        self.assertEqual(csv_escape("=cmd()"), "'=cmd()")

    def test_neutralizes_formula_prefix_after_leading_whitespace(self):
        # Corrige el hallazgo de la auditoría: Base Sistema/Utils.gs:107-111 solo
        # comprobaba la posición 0, no un valor con espacio inicial.
        self.assertEqual(csv_escape("  =WEBSERVICE(x)"), "'  =WEBSERVICE(x)")

    def test_leaves_normal_text_untouched(self):
        self.assertEqual(csv_escape("Ana"), "Ana")

    def test_handles_none(self):
        self.assertEqual(csv_escape(None), "")


if __name__ == "__main__":
    unittest.main()
