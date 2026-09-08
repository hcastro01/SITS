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
from app.models import Atencion, Caso, EnvioFormulario, Formulario, FormularioVersion, RespuestaFormulario, User
from app.services.dynamic_responses import context_forms, get_user_response
from app.services.form_builder import get_definition, save_definition
from app.services.formularios import change_status, create_formulario
from app.services.preguntas import preguntas
from app.services.respuestas_formulario import save_response
from app.services.security_seed import seed_security


class RespuestasFormularioServiceTests(unittest.TestCase):
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
            session.add(User(id_usuario="ts", correo="ts@example.com", nombre="Trabajador",
                              rol_id="ROLE_TRABAJADOR_SOCIAL", estado="ACTIVO"))
            session.add(User(id_usuario="ts2", correo="ts2@example.com", nombre="Trabajador 2",
                              rol_id="ROLE_TRABAJADOR_SOCIAL", estado="ACTIVO"))
            admin = resolve_current_user(session, "admin@example.com")
            formulario = create_formulario(session, admin, motivo_auditoria="Alta",
                                            correlation_id="c0", nombre="Ficha")
            self.id_formulario = formulario.id_formulario
            pregunta = preguntas.create(session, admin, motivo_auditoria="Alta", correlation_id="c0b",
                                         id_formulario=self.id_formulario, etiqueta="Resultado")
            self.id_pregunta = pregunta.id_pregunta
            change_status(session, admin, self.id_formulario, "PUBLICADO",
                           expected_version=formulario.version, correlation_id="c0c")

    def tearDown(self):
        db_session.engine = self._original_engine
        self.engine.dispose()
        self.directory.cleanup()

    def test_registered_response_requires_published_form(self):
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin@example.com")
            ts = resolve_current_user(session, "ts@example.com")
            otro_formulario = create_formulario(session, admin, motivo_auditoria="Alta",
                                                 correlation_id="c1", nombre="Sin publicar")
            with self.assertRaises(AppError) as ctx:
                save_response(session, ts, otro_formulario.id_formulario, draft=False,
                               respuestas=[{"id_pregunta": self.id_pregunta, "valor_texto": "x"}],
                               correlation_id="c2")
            self.assertEqual(ctx.exception.code, "FORM_NOT_PUBLISHED")

    def test_new_draft_also_requires_published_form(self):
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin@example.com")
            ts = resolve_current_user(session, "ts@example.com")
            formulario = create_formulario(session, admin, motivo_auditoria="Alta",
                                            correlation_id="c1", nombre="Sin publicar")
            with self.assertRaises(AppError) as ctx:
                save_response(session, ts, formulario.id_formulario, draft=True,
                              respuestas=[], correlation_id="c2")
            self.assertEqual(ctx.exception.code, "FORM_NOT_PUBLISHED")

    def test_empty_response_is_rejected(self):
        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            with self.assertRaises(AppError) as ctx:
                save_response(session, ts, self.id_formulario, draft=False, respuestas=[], correlation_id="c1")
            self.assertEqual(ctx.exception.code, "EMPTY_RESPONSE")

    def test_same_client_key_from_different_users_does_not_collide(self):
        # Hallazgo de Fase 1 §6: la clave del legacy era global. Aquí dos usuarios pueden
        # compartir el mismo id_envio_cliente sin pisarse ni ver la respuesta ajena.
        with Session(self.engine) as session, session.begin():
            ts1 = resolve_current_user(session, "ts@example.com")
            ts2 = resolve_current_user(session, "ts2@example.com")
            envio1 = save_response(session, ts1, self.id_formulario, draft=False,
                                    respuestas=[{"id_pregunta": self.id_pregunta, "valor_texto": "de ts1"}],
                                    id_envio_cliente="misma-clave", correlation_id="c1")
            envio2 = save_response(session, ts2, self.id_formulario, draft=False,
                                    respuestas=[{"id_pregunta": self.id_pregunta, "valor_texto": "de ts2"}],
                                    id_envio_cliente="misma-clave", correlation_id="c2")
            self.assertNotEqual(envio1.id_respuesta, envio2.id_respuesta)
        with Session(self.engine) as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(EnvioFormulario)), 2)

    def test_resubmitting_registered_response_with_same_key_is_idempotent(self):
        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            primero = save_response(session, ts, self.id_formulario, draft=False,
                                     respuestas=[{"id_pregunta": self.id_pregunta, "valor_texto": "v1"}],
                                     id_envio_cliente="clave-x", correlation_id="c1")
            id_respuesta = primero.id_respuesta
        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            segundo = save_response(session, ts, self.id_formulario, draft=False,
                                     respuestas=[{"id_pregunta": self.id_pregunta, "valor_texto": "v2-ignorado"}],
                                     id_envio_cliente="clave-x", correlation_id="c2")
            self.assertEqual(segundo.id_respuesta, id_respuesta)
        with Session(self.engine) as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(EnvioFormulario)), 1)
            detalle = session.scalar(
                select(RespuestaFormulario).where(RespuestaFormulario.id_respuesta == id_respuesta)
            )
            self.assertEqual(detalle.valor_texto, "v1")  # no se sobrescribió por el reenvío duplicado.

    def test_draft_can_be_resaved_and_retires_previous_answers(self):
        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            borrador1 = save_response(session, ts, self.id_formulario, draft=True,
                                       respuestas=[{"id_pregunta": self.id_pregunta, "valor_texto": "primer intento"}],
                                       id_envio_cliente="borrador-1", correlation_id="c1")
            id_respuesta = borrador1.id_respuesta
        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            save_response(session, ts, self.id_formulario, draft=True,
                          respuestas=[{"id_pregunta": self.id_pregunta, "valor_texto": "segundo intento"}],
                          id_envio_cliente="borrador-1", correlation_id="c2")
        with Session(self.engine) as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(EnvioFormulario)), 1)
            activas = session.scalars(
                select(RespuestaFormulario).where(
                    RespuestaFormulario.id_respuesta == id_respuesta,
                    RespuestaFormulario.eliminado.is_(False),
                )
            ).all()
            self.assertEqual(len(activas), 1)
            self.assertEqual(activas[0].valor_texto, "segundo intento")

    def test_hidden_required_question_does_not_block_final_submission(self):
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin@example.com")
            ts = resolve_current_user(session, "ts@example.com")
            formulario = create_formulario(session, admin, motivo_auditoria="Alta",
                                            correlation_id="c1", nombre="Condicional")
            origen = preguntas.create(session, admin, motivo_auditoria="Alta", correlation_id="c2",
                                      id_formulario=formulario.id_formulario, etiqueta="¿Requiere derivación?", tipo="SI_NO")
            destino = preguntas.create(session, admin, motivo_auditoria="Alta", correlation_id="c3",
                                       id_formulario=formulario.id_formulario, etiqueta="Estado de derivación",
                                       obligatoria=True)
            from app.services.reglas_formulario import reglas_formulario
            reglas_formulario.create(session, admin, motivo_auditoria="Alta", correlation_id="c4",
                                      id_formulario=formulario.id_formulario,
                                      id_pregunta_origen=origen.id_pregunta,
                                      id_pregunta_destino=destino.id_pregunta,
                                      operador="EQ", valor_comparacion="Sí", accion="MOSTRAR", grupo="TODAS")
            change_status(session, admin, formulario.id_formulario, "PUBLICADO",
                          expected_version=formulario.version, correlation_id="c5")
            envio = save_response(session, ts, formulario.id_formulario, draft=False,
                                  respuestas=[{"id_pregunta": origen.id_pregunta, "valor_texto": "No"}],
                                  correlation_id="c6")
            self.assertEqual(envio.estado, "REGISTRADO")

    def test_registered_response_uses_immutable_published_definition(self):
        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            response = save_response(session, ts, self.id_formulario, draft=False,
                                     respuestas=[{"id_pregunta": self.id_pregunta, "valor_texto": "Original"}],
                                     correlation_id="c1")
            response_id = response.id_respuesta
            first_version_id = response.id_version_formulario
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin@example.com")
            form = session.get(Formulario, self.id_formulario)
            definition = get_definition(session, self.id_formulario)
            definition["preguntas"][0]["etiqueta"] = "Resultado actualizado"
            updated = save_definition(session, admin, self.id_formulario, {
                "expected_version": form.version, "nombre": definition["nombre"],
                "descripcion": definition["descripcion"], "destinos": definition["destinos"],
                "secciones": definition["secciones"], "preguntas": definition["preguntas"],
                "reglas": definition["reglas"],
            }, correlation_id="c2")
            change_status(session, admin, self.id_formulario, "PUBLICADO",
                          expected_version=updated["version"], correlation_id="c3")
        with Session(self.engine) as session:
            ts = resolve_current_user(session, "ts@example.com")
            historic = get_user_response(session, ts, response_id)
            self.assertEqual(historic["id_version_formulario"], first_version_id)
            self.assertEqual(historic["definicion"]["preguntas"][0]["etiqueta"], "Resultado")
            self.assertEqual(session.query(FormularioVersion).count(), 2)

    def test_context_flow_pending_draft_registered_and_second_destination(self):
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin@example.com")
            session.add(Caso(id_caso="caso-1", codigo_caso="CAS-001", colaborador="Ana"))
            session.add(Atencion(id_atencion="atencion-1", colaborador="Ana", motivo="Seguimiento"))
            form = create_formulario(session, admin, motivo_auditoria="Alta", correlation_id="c1",
                                     nombre="Seguimiento Social", destinos=["CASOS", "ATENCIONES"])
            field = preguntas.create(session, admin, motivo_auditoria="Alta", correlation_id="c2",
                                     id_formulario=form.id_formulario, etiqueta="Observación")
            change_status(session, admin, form.id_formulario, "PUBLICADO",
                          expected_version=form.version, correlation_id="c3")
            form_id, question_id = form.id_formulario, field.id_pregunta
        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            self.assertEqual(context_forms(session, ts, "CASOS", "caso-1")[0]["estado_respuesta"], "PENDIENTE")
            draft = save_response(session, ts, form_id, draft=True,
                                  respuestas=[{"id_pregunta": question_id, "valor_texto": "Parcial"}],
                                  contexto_tipo="CASOS", contexto_id="caso-1",
                                  id_envio_cliente="flujo-contexto", correlation_id="c4")
            draft_id = draft.id_respuesta
        with Session(self.engine) as session, session.begin():
            ts = resolve_current_user(session, "ts@example.com")
            case_item = context_forms(session, ts, "CASOS", "caso-1")[0]
            self.assertEqual(case_item["estado_respuesta"], "BORRADOR")
            final = save_response(session, ts, form_id, draft=False,
                                  respuestas=[{"id_pregunta": question_id, "valor_texto": "Final"}],
                                  contexto_tipo="CASOS", contexto_id="caso-1", id_respuesta=draft_id,
                                  expected_version=case_item["version"], correlation_id="c5")
            self.assertEqual(final.estado, "REGISTRADO")
        with Session(self.engine) as session:
            ts = resolve_current_user(session, "ts@example.com")
            self.assertEqual(context_forms(session, ts, "CASOS", "caso-1")[0]["estado_respuesta"], "REGISTRADO")
            self.assertEqual(context_forms(session, ts, "ATENCIONES", "atencion-1")[0]["estado_respuesta"], "PENDIENTE")


if __name__ == "__main__":
    unittest.main()
