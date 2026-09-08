import unittest
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from sqlalchemy import text

import app.db.session as db_session
from app.db.session import build_engine


class FormulariosMigrationTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.engine = build_engine(f"sqlite:///{self.directory.name}/migration.db")
        self.original_engine = db_session.engine
        db_session.engine = self.engine

    def tearDown(self):
        db_session.engine = self.original_engine
        self.engine.dispose()
        self.directory.cleanup()

    def test_upgrade_preserves_legacy_forms_destinations_and_response_context(self):
        config = Config("alembic.ini")
        command.upgrade(config, "0009_password_auth")
        with self.engine.begin() as connection:
            connection.execute(text("INSERT INTO formularios "
                                    "(id_formulario, nombre, proceso, activo, eliminado, version) VALUES "
                                    "('f-caso', 'Ficha caso', 'CASO', 1, 0, 1), "
                                    "('f-general', 'Ficha general', NULL, 1, 0, 1)"))
            connection.execute(text("INSERT INTO envios_formulario "
                                    "(id_respuesta, id_formulario, usuario_respuesta, id_registro_proceso, estado, fecha_creacion, activo, eliminado, version) VALUES "
                                    "('e-caso', 'f-caso', 'ana@example.com', 'caso-1', 'REGISTRADO', '2024-01-01T10:00:00Z', 1, 0, 1), "
                                    "('e-general', 'f-general', 'ana@example.com', 'legacy-1', 'REGISTRADO', '2024-01-02T10:00:00Z', 1, 0, 1), "
                                    "('e-draft', 'f-general', 'ana@example.com', NULL, 'BORRADOR', '2024-01-03T10:00:00Z', 1, 0, 1)"))
        command.upgrade(config, "head")
        with self.engine.connect() as connection:
            destinations = dict(connection.execute(text(
                "SELECT id_formulario, modulo FROM formulario_destinos ORDER BY id_formulario"
            )).all())
            responses = {row.id_respuesta: (row.contexto_tipo, row.contexto_id) for row in connection.execute(text(
                "SELECT id_respuesta, contexto_tipo, contexto_id FROM envios_formulario ORDER BY id_respuesta"
            ))}
            codes = {row.id_respuesta: (row.numero_secuencial, row.codigo_respuesta) for row in connection.execute(text(
                "SELECT id_respuesta, numero_secuencial, codigo_respuesta FROM envios_formulario ORDER BY id_respuesta"
            ))}
            last_number = connection.execute(text(
                "SELECT ultimo_numero FROM secuencias_respuestas_formulario WHERE nombre = 'GLOBAL'"
            )).scalar_one()
        self.assertEqual(destinations, {"f-caso": "CASOS", "f-general": "GENERAL"})
        self.assertEqual(responses["e-caso"], ("CASOS", "caso-1"))
        self.assertEqual(responses["e-general"], ("GENERAL", None))
        self.assertEqual(codes["e-caso"], (1, "TTHH_RRLL_00000000001"))
        self.assertEqual(codes["e-general"], (2, "TTHH_RRLL_00000000002"))
        self.assertEqual(codes["e-draft"], (None, None))
        self.assertEqual(last_number, 2)


if __name__ == "__main__":
    unittest.main()
