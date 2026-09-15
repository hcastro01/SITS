import unittest
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.db.session import build_engine
from app.models import ModuloSistema
from app.services.security_seed import seed_module_catalog, seed_security


class NavigationCatalogTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.engine = build_engine(f"sqlite:///{self.directory.name}/navigation.db")
        self.original_engine = db_session.engine
        db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")

    def tearDown(self):
        db_session.engine = self.original_engine
        self.engine.dispose()
        self.directory.cleanup()

    def test_catalog_matches_the_phase_one_navigation_and_is_idempotent(self):
        with Session(self.engine) as session, session.begin():
            seed_security(session)
            seed_module_catalog(session)
        with Session(self.engine) as session:
            first_count = len(session.scalars(select(ModuloSistema)).all())
        with Session(self.engine) as session, session.begin():
            seed_module_catalog(session)
        with Session(self.engine) as session:
            nodes = {node.id_modulo: node for node in session.scalars(select(ModuloSistema)).all()}
            self.assertEqual(nodes["sits-trabajo-social"].nombre, "Trabajo Social")
            self.assertEqual(nodes["sits-inicio"].padre_id_modulo, "sits-trabajo-social")
            self.assertEqual(nodes["sits-actividades-formularios"].ruta, "/trabajo-social/actividades/formularios")
            self.assertEqual(nodes["sits-produccion-recorridos"].ruta, "/trabajo-social/produccion/recorridos")
            self.assertEqual(nodes["sits-oficina-formularios"].ruta, "/trabajo-social/oficina/formularios")
            self.assertEqual(nodes["sits-repositorio-formularios"].padre_id_modulo, None)
            self.assertEqual(nodes["sits-admin-usuarios"].padre_id_modulo, "sits-administracion")
            self.assertEqual(len(nodes), first_count)

    def test_migration_includes_every_common_metadata_column(self):
        columns = {column["name"] for column in inspect(self.engine).get_columns("modulos")}
        self.assertIn("motivo_eliminacion", columns)
        self.assertIn("padre_id_modulo", columns)


if __name__ == "__main__":
    unittest.main()
