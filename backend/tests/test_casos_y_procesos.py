import unittest
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.db.session import build_engine
from app.models import (
    Atencion, Caso, Cierre, Compromiso, Derivacion, DetalleCasoSensible,
    HallazgoRecorrido, Novedad, Persona, Recorrido, Seguimiento,
)


class CasosYProcesosTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.engine = build_engine(f"sqlite:///{self.directory.name}/test.db")
        self._original_engine = db_session.engine
        db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")
        with Session(self.engine) as session, session.begin():
            session.add(Persona(id_persona="p1", nombre="Ana"))

    def tearDown(self):
        db_session.engine = self._original_engine
        self.engine.dispose()
        self.directory.cleanup()

    def test_full_case_lifecycle_chain_persists_and_links_correctly(self):
        # Sin relationship() declarada, el unit-of-work no infiere el orden de FK entre
        # mappers no relacionados: se hace flush() explícito entre padre e hijo.
        with Session(self.engine) as session, session.begin():
            session.add(Caso(id_caso="c1", codigo_caso="CAS-2026-0001", id_persona="p1", restriccion=True))
            session.flush()
            session.add(Seguimiento(id_seguimiento="s1", id_caso="c1", descripcion="Primer seguimiento"))
            session.flush()
            session.add(Compromiso(id_compromiso="cp1", id_caso="c1", id_seguimiento="s1"))
            session.add(Cierre(id_cierre="cl1", id_caso="c1", requiere_monitoreo=True))
            session.add(DetalleCasoSensible(id_detalle_sensible="d1", id_caso="c1", notas_privadas="confidencial"))
        with Session(self.engine) as session:
            caso = session.get(Caso, "c1")
            self.assertEqual(caso.codigo_caso, "CAS-2026-0001")
            self.assertTrue(caso.restriccion)
            self.assertFalse(caso.derivacion)
            self.assertEqual(session.get(Seguimiento, "s1").id_caso, "c1")
            self.assertEqual(session.get(Compromiso, "cp1").id_seguimiento, "s1")
            self.assertTrue(session.get(Cierre, "cl1").requiere_monitoreo)
            self.assertEqual(session.get(DetalleCasoSensible, "d1").id_caso, "c1")

    def test_codigo_caso_must_be_unique(self):
        with Session(self.engine) as session, session.begin():
            session.add(Caso(id_caso="c1", codigo_caso="CAS-2026-0001"))
        with self.assertRaises(IntegrityError):
            with Session(self.engine) as session, session.begin():
                session.add(Caso(id_caso="c2", codigo_caso="CAS-2026-0001"))

    def test_detalle_sensible_is_one_to_one_with_caso(self):
        with Session(self.engine) as session, session.begin():
            session.add(Caso(id_caso="c1", codigo_caso="CAS-2026-0001"))
            session.add(DetalleCasoSensible(id_detalle_sensible="d1", id_caso="c1"))
        with self.assertRaises(IntegrityError):
            with Session(self.engine) as session, session.begin():
                session.add(DetalleCasoSensible(id_detalle_sensible="d2", id_caso="c1"))

    def test_child_of_caso_requires_existing_caso(self):
        with self.assertRaises(IntegrityError):
            with Session(self.engine) as session, session.begin():
                session.add(Seguimiento(id_seguimiento="s1", id_caso="inexistente"))

    def test_hallazgo_recorrido_allows_findings_without_novedad_or_caso(self):
        with Session(self.engine) as session, session.begin():
            session.add(Recorrido(id_recorrido="r1", responsable="Ana"))
            session.flush()
            session.add(HallazgoRecorrido(id_hallazgo="h1", id_recorrido="r1"))
        with Session(self.engine) as session:
            hallazgo = session.get(HallazgoRecorrido, "h1")
            self.assertIsNone(hallazgo.id_novedad)
            self.assertIsNone(hallazgo.id_caso)
            self.assertFalse(hallazgo.genera_novedad)
            self.assertFalse(hallazgo.genera_caso)

    def test_hallazgo_recorrido_requires_existing_recorrido(self):
        with self.assertRaises(IntegrityError):
            with Session(self.engine) as session, session.begin():
                session.add(HallazgoRecorrido(id_hallazgo="h1", id_recorrido="inexistente"))

    def test_atencion_and_caso_allow_persona_nulo(self):
        # Fase 1 §4: id_persona FK nullable en atenciones y casos.
        with Session(self.engine) as session, session.begin():
            session.add(Atencion(id_atencion="a1"))
            session.add(Caso(id_caso="c1", codigo_caso="CAS-2026-0001"))
        with Session(self.engine) as session:
            self.assertIsNone(session.get(Atencion, "a1").id_persona)
            self.assertIsNone(session.get(Caso, "c1").id_persona)

    def test_novedad_boolean_flags_round_trip(self):
        with Session(self.engine) as session, session.begin():
            session.add(Novedad(id_novedad="n1", genera_atencion=True, genera_caso=False))
        with Session(self.engine) as session:
            novedad = session.get(Novedad, "n1")
            self.assertTrue(novedad.genera_atencion)
            self.assertFalse(novedad.genera_caso)


if __name__ == "__main__":
    unittest.main()
