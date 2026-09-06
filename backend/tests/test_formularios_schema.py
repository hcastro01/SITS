import unittest
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.db.session import build_engine
from app.models import EnvioFormulario, Formulario, OpcionPregunta, Pregunta, RespuestaFormulario


class FormulariosSchemaTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.engine = build_engine(f"sqlite:///{self.directory.name}/test.db")
        self._original_engine = db_session.engine
        db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")
        with Session(self.engine) as session, session.begin():
            session.add(Formulario(id_formulario="f1", nombre="Ficha de caso"))

    def tearDown(self):
        db_session.engine = self._original_engine
        self.engine.dispose()
        self.directory.cleanup()

    def test_pregunta_allows_self_referencing_dependent_field(self):
        with Session(self.engine) as session, session.begin():
            session.add(Pregunta(id_pregunta="p1", id_formulario="f1", etiqueta="Derivacion"))
            session.flush()
            session.add(Pregunta(id_pregunta="p2", id_formulario="f1", etiqueta="Estado derivacion",
                                  campo_dependiente="p1", valor_dependiente="true"))
        with Session(self.engine) as session:
            self.assertEqual(session.get(Pregunta, "p2").campo_dependiente, "p1")

    def test_opcion_pregunta_allows_hierarchical_parent(self):
        with Session(self.engine) as session, session.begin():
            session.add(Pregunta(id_pregunta="p1", id_formulario="f1", etiqueta="Area"))
            session.flush()
            session.add(OpcionPregunta(id_opcion="o1", id_pregunta="p1", valor="A", etiqueta="Area A"))
            session.flush()
            session.add(OpcionPregunta(id_opcion="o2", id_pregunta="p1", valor="A1", etiqueta="Sub A1",
                                        id_opcion_padre="o1"))
        with Session(self.engine) as session:
            self.assertEqual(session.get(OpcionPregunta, "o2").id_opcion_padre, "o1")

    def test_envio_uniqueness_is_scoped_per_user_not_global(self):
        # Fase 1 §6 / hallazgo de idempotencia: la clave global del legacy permitía que un
        # id_envio_cliente ajeno colisionara. Aquí dos usuarios pueden compartir la misma
        # clave de cliente sin chocar.
        with Session(self.engine) as session, session.begin():
            session.add(EnvioFormulario(id_respuesta="e1", id_formulario="f1",
                                         usuario_respuesta="ana@example.com", id_envio_cliente="clave-1"))
            session.add(EnvioFormulario(id_respuesta="e2", id_formulario="f1",
                                         usuario_respuesta="beto@example.com", id_envio_cliente="clave-1"))
        with Session(self.engine) as session:
            self.assertEqual(session.get(EnvioFormulario, "e1").usuario_respuesta, "ana@example.com")
            self.assertEqual(session.get(EnvioFormulario, "e2").usuario_respuesta, "beto@example.com")

    def test_same_user_cannot_reuse_client_key(self):
        with Session(self.engine) as session, session.begin():
            session.add(EnvioFormulario(id_respuesta="e1", id_formulario="f1",
                                         usuario_respuesta="ana@example.com", id_envio_cliente="clave-1"))
        with self.assertRaises(IntegrityError):
            with Session(self.engine) as session, session.begin():
                session.add(EnvioFormulario(id_respuesta="e2", id_formulario="f1",
                                             usuario_respuesta="ana@example.com", id_envio_cliente="clave-1"))

    def test_respuestas_allow_multiple_rows_per_pregunta(self):
        # Fase 1 §4 línea 107: selección múltiple genera varias filas por pregunta.
        with Session(self.engine) as session, session.begin():
            session.add(Pregunta(id_pregunta="p1", id_formulario="f1", etiqueta="Opciones"))
            session.add(EnvioFormulario(id_respuesta="e1", id_formulario="f1", usuario_respuesta="ana@example.com"))
            session.flush()
            session.add(RespuestaFormulario(id_detalle_respuesta="d1", id_respuesta="e1", id_pregunta="p1",
                                             valor_opcion="rojo"))
            session.add(RespuestaFormulario(id_detalle_respuesta="d2", id_respuesta="e1", id_pregunta="p1",
                                             valor_opcion="azul"))
        with Session(self.engine) as session:
            from sqlalchemy import func, select
            total = session.scalar(
                select(func.count()).select_from(RespuestaFormulario).where(RespuestaFormulario.id_pregunta == "p1")
            )
            self.assertEqual(total, 2)

    def test_valor_booleano_is_nullable_tri_state(self):
        with Session(self.engine) as session, session.begin():
            session.add(Pregunta(id_pregunta="p1", id_formulario="f1", etiqueta="Riesgo"))
            session.add(EnvioFormulario(id_respuesta="e1", id_formulario="f1", usuario_respuesta="ana@example.com"))
            session.flush()
            session.add(RespuestaFormulario(id_detalle_respuesta="d1", id_respuesta="e1", id_pregunta="p1"))
        with Session(self.engine) as session:
            self.assertIsNone(session.get(RespuestaFormulario, "d1").valor_booleano)


if __name__ == "__main__":
    unittest.main()
