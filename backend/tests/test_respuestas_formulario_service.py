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
from app.models import EnvioFormulario, RespuestaFormulario, User
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


if __name__ == "__main__":
    unittest.main()
