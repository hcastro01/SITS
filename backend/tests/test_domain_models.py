import unittest
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.db.session import build_engine
from app.models import Catalogo, Configuracion, Persona
from app.services.catalog_seed import TECHNICAL_CATALOGS, seed_technical_catalogs


class DomainModelTests(unittest.TestCase):
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

    def test_personas_allows_duplicate_cedula(self):
        # MIGRACION_FASE_1.md §4: no declarar único hasta auditar duplicados reales.
        with Session(self.engine) as session, session.begin():
            session.add(Persona(id_persona="p1", nombre="Ana", cedula="0102030405"))
            session.add(Persona(id_persona="p2", nombre="Beto", cedula="0102030405"))
        with Session(self.engine) as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(Persona)), 2)

    def test_persona_cedula_preserves_leading_zeros_as_text(self):
        with Session(self.engine) as session, session.begin():
            session.add(Persona(id_persona="p1", nombre="Ana", cedula="0102030405"))
        with Session(self.engine) as session:
            self.assertEqual(session.get(Persona, "p1").cedula, "0102030405")

    def test_catalogo_rejects_duplicate_tipo_codigo(self):
        with Session(self.engine) as session, session.begin():
            session.add(Catalogo(id_catalogo="c1", tipo="ESTADO_CASO", codigo="X", valor="X"))
        with self.assertRaises(IntegrityError):
            with Session(self.engine) as session, session.begin():
                session.add(Catalogo(id_catalogo="c2", tipo="ESTADO_CASO", codigo="X", valor="Otro"))

    def test_configuracion_has_no_metadata_block(self):
        self.assertFalse(hasattr(Configuracion, "activo"))
        self.assertFalse(hasattr(Configuracion, "version"))

    def test_seed_technical_catalogs_matches_setup_gs_exactly(self):
        with Session(self.engine) as session, session.begin():
            seed_technical_catalogs(session)
        with Session(self.engine) as session:
            rows = {row.id_catalogo: row for row in session.scalars(select(Catalogo)).all()}
            self.assertEqual(len(rows), len(TECHNICAL_CATALOGS))
            for id_catalogo, tipo, codigo, valor, orden in TECHNICAL_CATALOGS:
                row = rows[id_catalogo]
                self.assertEqual((row.tipo, row.codigo, row.valor, row.orden), (tipo, codigo, valor, orden))
                self.assertFalse(row.es_sensible)

    def test_seed_technical_catalogs_is_idempotent(self):
        with Session(self.engine) as session, session.begin():
            seed_technical_catalogs(session)
        with Session(self.engine) as session, session.begin():
            seed_technical_catalogs(session)
        with Session(self.engine) as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(Catalogo)), len(TECHNICAL_CATALOGS))

    def test_nivel_sensibilidad_is_not_seeded(self):
        # Hallazgo H2: Base Sistema nunca definió estos valores. No se inventan aquí.
        with Session(self.engine) as session, session.begin():
            seed_technical_catalogs(session)
        with Session(self.engine) as session:
            count = session.scalar(
                select(func.count()).select_from(Catalogo).where(Catalogo.tipo == "NIVEL_SENSIBILIDAD")
            )
            self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
