import unittest
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.db.session import build_engine
from app.models import Catalogo, Formulario, OpcionPregunta, Pregunta
from app.services.matrix_seed import seed_institutional_matrix


class MatrixSeedTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.engine = build_engine(f"sqlite:///{self.directory.name}/test.db")
        self._original_engine = db_session.engine
        db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")

    def tearDown(self):
        db_session.engine = self._original_engine
        self.engine.dispose()
        self.directory.cleanup()

    def test_seeds_the_real_counts(self):
        with Session(self.engine) as session, session.begin():
            seed_institutional_matrix(session)
        with Session(self.engine) as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(Catalogo)), 457)
            self.assertEqual(session.scalar(select(func.count()).select_from(Formulario)), 1)
            self.assertEqual(session.scalar(select(func.count()).select_from(Pregunta)), 24)
            self.assertEqual(session.scalar(select(func.count()).select_from(OpcionPregunta)), 454)

    def test_is_idempotent(self):
        with Session(self.engine) as session, session.begin():
            seed_institutional_matrix(session)
        with Session(self.engine) as session, session.begin():
            seed_institutional_matrix(session)
        with Session(self.engine) as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(Catalogo)), 457)
            self.assertEqual(session.scalar(select(func.count()).select_from(Pregunta)), 24)
            self.assertEqual(session.scalar(select(func.count()).select_from(OpcionPregunta)), 454)

    def test_formulario_is_the_real_published_one(self):
        with Session(self.engine) as session, session.begin():
            seed_institutional_matrix(session)
        with Session(self.engine) as session:
            formulario = session.scalar(select(Formulario))
            self.assertEqual(formulario.nombre, "Ficha integral de gestion de casos")
            self.assertEqual(formulario.estado, "PUBLICADO")

    def test_orphaned_form_questions_are_excluded(self):
        # "Como esta" / "Como esta (copia)" pertenecian a un IdFormulario inexistente.
        with Session(self.engine) as session, session.begin():
            seed_institutional_matrix(session)
        with Session(self.engine) as session:
            etiquetas = set(session.scalars(select(Pregunta.etiqueta)))
            self.assertNotIn("Como esta", etiquetas)

    def test_abandoned_dropdown_experiment_is_excluded(self):
        # La pregunta desactivada con 21,803 opciones no debe sembrarse.
        with Session(self.engine) as session, session.begin():
            seed_institutional_matrix(session)
        with Session(self.engine) as session:
            huerfana = session.get(Pregunta, "PREGUNTA-FDFFE940D6E64A619527A83DDB8EC7B4")
            self.assertIsNone(huerfana)

    def test_nivel_sensibilidad_still_not_present_in_real_data(self):
        with Session(self.engine) as session, session.begin():
            seed_institutional_matrix(session)
        with Session(self.engine) as session:
            count = session.scalar(
                select(func.count()).select_from(Catalogo).where(Catalogo.tipo == "NIVEL_SENSIBILIDAD")
            )
            self.assertEqual(count, 0)

    def test_estado_caso_pregunta_uses_the_nine_workflow_labels(self):
        with Session(self.engine) as session, session.begin():
            seed_institutional_matrix(session)
        with Session(self.engine) as session:
            pregunta = session.get(Pregunta, "PREGUNTA-8675868D14704202A4568C4D63D8D343")
            self.assertEqual(pregunta.etiqueta, "EstadoCaso")
            opciones = session.scalars(
                select(OpcionPregunta).where(OpcionPregunta.id_pregunta == pregunta.id_pregunta)
            ).all()
            self.assertEqual(len(opciones), 9)
            self.assertIn("Cerrado", {o.etiqueta for o in opciones})

    def test_derivacion_dependent_question_keeps_its_condition(self):
        with Session(self.engine) as session, session.begin():
            seed_institutional_matrix(session)
        with Session(self.engine) as session:
            estado_derivacion = session.get(Pregunta, "PREGUNTA-168BA67AF3934D33AD4D255D4E2EF69A")
            self.assertEqual(estado_derivacion.campo_dependiente, "PREGUNTA-51692DF9DA434FD4B642ADC9208C0E98")


if __name__ == "__main__":
    unittest.main()
