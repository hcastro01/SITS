import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.api.formularios import responder
from app.core.errors import AppError
from app.core.permissions import resolve_current_user
from app.db.session import build_engine
from app.models import Atencion, Auditoria, Caso, EnvioFormulario, SecuenciaRespuestaFormulario, User
from app.services.formularios import change_status, create_formulario
from app.services.preguntas import preguntas
from app.services.records import apply_soft_delete
from app.services.response_codes import format_response_code
from app.services.respuestas_formulario import save_response
from app.services.security_seed import seed_security


class ResponseCodeTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.engine = build_engine(f"sqlite:///{self.directory.name}/codes.db")
        self.original_engine = db_session.engine
        db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")
        with Session(self.engine) as session, session.begin():
            seed_security(session)
            session.add_all([
                User(id_usuario="admin", correo="admin@example.com", nombre="Admin", rol_id="ROLE_ADMIN", estado="ACTIVO"),
                User(id_usuario="ts1", correo="ts1@example.com", nombre="TS 1", rol_id="ROLE_TRABAJADOR_SOCIAL", estado="ACTIVO"),
                User(id_usuario="ts2", correo="ts2@example.com", nombre="TS 2", rol_id="ROLE_TRABAJADOR_SOCIAL", estado="ACTIVO"),
            ])
            session.flush()
            admin = resolve_current_user(session, "admin@example.com")
            form = create_formulario(session, admin, motivo_auditoria="Alta", correlation_id="setup", nombre="Ficha")
            question = preguntas.create(session, admin, motivo_auditoria="Alta", correlation_id="setup-q",
                                        id_formulario=form.id_formulario, etiqueta="Resultado")
            change_status(session, admin, form.id_formulario, "PUBLICADO",
                          expected_version=form.version, correlation_id="setup-publish")
            self.form_id = form.id_formulario
            self.question_id = question.id_pregunta

    def tearDown(self):
        db_session.engine = self.original_engine
        self.engine.dispose()
        self.directory.cleanup()

    def _answer(self, value="OK"):
        return [{"id_pregunta": self.question_id, "valor_texto": value}]

    def test_format_has_fixed_prefix_and_eleven_digits(self):
        self.assertEqual(format_response_code(1), "TTHH_RRLL_00000000001")
        self.assertEqual(format_response_code(35), "TTHH_RRLL_00000000035")
        self.assertEqual(format_response_code(125), "TTHH_RRLL_00000000125")
        self.assertEqual(format_response_code(1000), "TTHH_RRLL_00000001000")

    def test_first_and_second_final_responses_are_unique_and_correlative(self):
        with Session(self.engine) as session, session.begin():
            first = save_response(session, resolve_current_user(session, "ts1@example.com"), self.form_id,
                                  draft=False, respuestas=self._answer("uno"), correlation_id="one")
            second = save_response(session, resolve_current_user(session, "ts2@example.com"), self.form_id,
                                   draft=False, respuestas=self._answer("dos"), correlation_id="two")
            self.assertEqual((first.numero_secuencial, first.codigo_respuesta), (1, "TTHH_RRLL_00000000001"))
            self.assertEqual((second.numero_secuencial, second.codigo_respuesta), (2, "TTHH_RRLL_00000000002"))
            self.assertNotEqual(first.codigo_respuesta, second.codigo_respuesta)
            audit_rows = list(session.scalars(select(Auditoria).where(
                Auditoria.tabla == "envios_formulario", Auditoria.id_registro == first.id_respuesta,
                Auditoria.campo == "codigo_respuesta",
            )))
            self.assertEqual(len(audit_rows), 1)
            self.assertEqual(audit_rows[0].valor_nuevo, first.codigo_respuesta)

    def test_draft_resaves_consume_nothing_and_finalization_consumes_once(self):
        with Session(self.engine) as session, session.begin():
            user = resolve_current_user(session, "ts1@example.com")
            draft = save_response(session, user, self.form_id, draft=True, respuestas=self._answer("parcial"),
                                  id_envio_cliente="draft-key", correlation_id="draft-1")
            self.assertIsNone(draft.codigo_respuesta)
            draft = save_response(session, user, self.form_id, draft=True, respuestas=self._answer("parcial 2"),
                                  id_envio_cliente="draft-key", correlation_id="draft-2")
            self.assertIsNone(draft.numero_secuencial)
            response_id, version = draft.id_respuesta, draft.version
            counter = session.get(SecuenciaRespuestaFormulario, "GLOBAL")
            self.assertEqual(counter.ultimo_numero, 0)
        with Session(self.engine) as session, session.begin():
            user = resolve_current_user(session, "ts1@example.com")
            final = save_response(session, user, self.form_id, draft=False, respuestas=self._answer("final"),
                                  id_envio_cliente="draft-key", id_respuesta=response_id,
                                  expected_version=version, correlation_id="final")
            code = final.codigo_respuesta
            self.assertEqual(code, "TTHH_RRLL_00000000001")
        with Session(self.engine) as session, session.begin():
            user = resolve_current_user(session, "ts1@example.com")
            retry = save_response(session, user, self.form_id, draft=False, respuestas=self._answer("ignored"),
                                  id_envio_cliente="draft-key", correlation_id="retry")
            self.assertEqual(retry.codigo_respuesta, code)
            self.assertEqual(session.get(SecuenciaRespuestaFormulario, "GLOBAL").ultimo_numero, 1)

    def test_registered_response_cannot_be_edited_and_keeps_its_code(self):
        with Session(self.engine) as session, session.begin():
            user = resolve_current_user(session, "ts1@example.com")
            response = save_response(session, user, self.form_id, draft=False, respuestas=self._answer(),
                                     id_envio_cliente="immutable", correlation_id="create")
            response_id, code = response.id_respuesta, response.codigo_respuesta
        with Session(self.engine) as session, session.begin():
            user = resolve_current_user(session, "ts1@example.com")
            with self.assertRaises(AppError):
                save_response(session, user, self.form_id, draft=True, respuestas=self._answer("changed"),
                              id_respuesta=response_id, expected_version=1, correlation_id="edit")
        with Session(self.engine) as session:
            self.assertEqual(session.get(EnvioFormulario, response_id).codigo_respuesta, code)

    def test_soft_deleted_number_is_not_reused(self):
        with Session(self.engine) as session, session.begin():
            first = save_response(session, resolve_current_user(session, "ts1@example.com"), self.form_id,
                                  draft=False, respuestas=self._answer(), correlation_id="first")
            apply_soft_delete(first, "admin@example.com", "Anulación de prueba")
        with Session(self.engine) as session, session.begin():
            second = save_response(session, resolve_current_user(session, "ts2@example.com"), self.form_id,
                                   draft=False, respuestas=self._answer(), correlation_id="second")
            self.assertEqual(second.codigo_respuesta, "TTHH_RRLL_00000000002")

    def test_sequence_is_global_across_forms_and_context_modules(self):
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin@example.com")
            session.add_all([Caso(id_caso="case-1", codigo_caso="CAS-1"),
                             Atencion(id_atencion="attention-1", motivo="Seguimiento")])
            form = create_formulario(session, admin, motivo_auditoria="Alta", correlation_id="context",
                                     nombre="Contextual", destinos=["CASOS", "ATENCIONES"])
            question = preguntas.create(session, admin, motivo_auditoria="Alta", correlation_id="context-q",
                                        id_formulario=form.id_formulario, etiqueta="Dato")
            change_status(session, admin, form.id_formulario, "PUBLICADO",
                          expected_version=form.version, correlation_id="context-publish")
            contextual_form_id, contextual_question_id = form.id_formulario, question.id_pregunta
        with Session(self.engine) as session, session.begin():
            user = resolve_current_user(session, "ts1@example.com")
            case_response = save_response(session, user, contextual_form_id, draft=False,
                respuestas=[{"id_pregunta": contextual_question_id, "valor_texto": "caso"}],
                contexto_tipo="CASOS", contexto_id="case-1", correlation_id="case")
            attention_response = save_response(session, user, contextual_form_id, draft=False,
                respuestas=[{"id_pregunta": contextual_question_id, "valor_texto": "atención"}],
                contexto_tipo="ATENCIONES", contexto_id="attention-1", correlation_id="attention")
            other_form_response = save_response(session, resolve_current_user(session, "ts2@example.com"),
                self.form_id, draft=False, respuestas=self._answer(), correlation_id="general")
            self.assertEqual([case_response.numero_secuencial, attention_response.numero_secuencial,
                              other_form_response.numero_secuencial], [1, 2, 3])

    def test_api_ignores_client_code_and_returns_backend_code(self):
        with Session(self.engine) as session, session.begin():
            result = responder(self.form_id, {
                "borrador": False, "respuestas": self._answer(), "id_envio_cliente": "api",
                "codigo_respuesta": "TTHH_RRLL_99999999999", "numero_secuencial": 99_999_999_999,
            }, db=session, user=resolve_current_user(session, "ts1@example.com"))
            self.assertEqual(result["codigo_respuesta"], "TTHH_RRLL_00000000001")
            self.assertEqual(result["numero_secuencial"], 1)

    def test_concurrent_submissions_receive_distinct_atomic_numbers(self):
        barrier = threading.Barrier(2)

        def submit(email: str, key: str) -> tuple[int, str]:
            with Session(self.engine) as session, session.begin():
                user = resolve_current_user(session, email)
                barrier.wait(timeout=5)
                response = save_response(session, user, self.form_id, draft=False,
                                         respuestas=self._answer(email), id_envio_cliente=key,
                                         correlation_id=key)
                return response.numero_secuencial, response.codigo_respuesta

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda args: submit(*args), [
                ("ts1@example.com", "concurrent-1"), ("ts2@example.com", "concurrent-2")]))
        self.assertEqual({number for number, _ in results}, {1, 2})
        self.assertEqual(len({code for _, code in results}), 2)
        with Session(self.engine) as session:
            self.assertEqual(session.scalar(select(func.count(EnvioFormulario.codigo_respuesta.distinct()))), 2)


if __name__ == "__main__":
    unittest.main()
