import unittest
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.core.errors import AppError
from app.core.permissions import resolve_current_user
from app.db.session import build_engine
from app.models import Pregunta, User
from app.services.formularios import change_status, create_formulario, update_formulario
from app.services.opciones_pregunta import opciones_pregunta
from app.services.preguntas import preguntas
from app.services.reglas_formulario import reglas_formulario
from app.services.security_seed import seed_security


class FormulariosServiceTests(unittest.TestCase):
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
            session.add(User(id_usuario="consulta", correo="consulta@example.com", nombre="Consulta",
                              rol_id="ROLE_CONSULTA", estado="ACTIVO"))

    def tearDown(self):
        db_session.engine = self._original_engine
        self.engine.dispose()
        self.directory.cleanup()

    def test_create_forces_borrador_and_rejects_estado_field(self):
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin@example.com")
            with self.assertRaises(AppError) as ctx:
                create_formulario(session, admin, motivo_auditoria="Alta", correlation_id="c1",
                                   nombre="Ficha", estado="PUBLICADO")
            self.assertEqual(ctx.exception.code, "INVALID_FIELD")
            formulario = create_formulario(session, admin, motivo_auditoria="Alta",
                                            correlation_id="c1", nombre="Ficha")
            self.assertEqual(formulario.estado, "BORRADOR")

    def test_update_cannot_change_estado(self):
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin@example.com")
            formulario = create_formulario(session, admin, motivo_auditoria="Alta",
                                            correlation_id="c1", nombre="Ficha")
            id_formulario, version = formulario.id_formulario, formulario.version
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin@example.com")
            with self.assertRaises(AppError) as ctx:
                update_formulario(session, admin, id_formulario, expected_version=version,
                                   motivo_auditoria="Edicion", correlation_id="c2", estado="PUBLICADO")
            self.assertEqual(ctx.exception.code, "INVALID_FIELD")

    def test_publish_requires_at_least_one_active_question(self):
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin@example.com")
            formulario = create_formulario(session, admin, motivo_auditoria="Alta",
                                            correlation_id="c1", nombre="Ficha")
            id_formulario, version = formulario.id_formulario, formulario.version

        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin@example.com")
            with self.assertRaises(AppError) as ctx:
                change_status(session, admin, id_formulario, "PUBLICADO",
                               expected_version=version, correlation_id="c2")
            self.assertEqual(ctx.exception.code, "FORM_WITHOUT_QUESTIONS")

        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin@example.com")
            preguntas.create(session, admin, motivo_auditoria="Alta", correlation_id="c3",
                              id_formulario=id_formulario, etiqueta="Responsable")

        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin@example.com")
            publicado = change_status(session, admin, id_formulario, "publicado",
                                       expected_version=version, correlation_id="c4")
            self.assertEqual(publicado.estado, "PUBLICADO")
            self.assertIsNotNone(publicado.fecha_publicacion)

    def test_invalid_status_is_rejected(self):
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin@example.com")
            formulario = create_formulario(session, admin, motivo_auditoria="Alta",
                                            correlation_id="c1", nombre="Ficha")
            id_formulario, version = formulario.id_formulario, formulario.version
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin@example.com")
            with self.assertRaises(AppError) as ctx:
                change_status(session, admin, id_formulario, "ARCHIVADO",
                               expected_version=version, correlation_id="c2")
            self.assertEqual(ctx.exception.code, "INVALID_FORM_STATUS")

    def test_consulta_role_cannot_create_formulario(self):
        with Session(self.engine) as session, session.begin():
            consulta = resolve_current_user(session, "consulta@example.com")
            with self.assertRaises(AppError) as ctx:
                create_formulario(session, consulta, motivo_auditoria="Alta", correlation_id="c1", nombre="X")
            self.assertEqual(ctx.exception.code, "FORBIDDEN")

    def test_pregunta_and_opcion_and_regla_factories_work_end_to_end(self):
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin@example.com")
            formulario = create_formulario(session, admin, motivo_auditoria="Alta",
                                            correlation_id="c1", nombre="Ficha")
            id_formulario = formulario.id_formulario
            p1 = preguntas.create(session, admin, motivo_auditoria="Alta", correlation_id="c2",
                                   id_formulario=id_formulario, etiqueta="Area", tipo="LISTA_DESPLEGABLE")
            p2 = preguntas.create(session, admin, motivo_auditoria="Alta", correlation_id="c3",
                                   id_formulario=id_formulario, etiqueta="Turno")
            opciones_pregunta.create(session, admin, motivo_auditoria="Alta", correlation_id="c4",
                                      id_pregunta=p1.id_pregunta, valor="A", etiqueta="Area A")
            reglas_formulario.create(session, admin, motivo_auditoria="Alta", correlation_id="c5",
                                      id_formulario=id_formulario, id_pregunta_origen=p1.id_pregunta,
                                      id_pregunta_destino=p2.id_pregunta, operador="EQ",
                                      valor_comparacion="A", accion="MOSTRAR")
        with Session(self.engine) as session:
            self.assertEqual(session.query(Pregunta).count(), 2)


if __name__ == "__main__":
    unittest.main()
