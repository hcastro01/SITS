import unittest
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.api.deps import get_db
from app.db.session import build_engine
from app.main import app
from app.models import Ausentismo, LoteImportacionAusentismo, Persona, User
from app.services.security_seed import seed_security


class AusentismosOperativosApiTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.engine = build_engine(f"sqlite:///{self.directory.name}/ausentismos.db")
        self.original_engine = db_session.engine
        db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")
        with Session(self.engine) as session, session.begin():
            seed_security(session)
            session.add_all([
                User(id_usuario="admin", correo="admin@example.com", nombre="Administradora", rol_id="ROLE_ADMIN", estado="ACTIVO"),
                User(id_usuario="consulta", correo="consulta@example.com", nombre="Consulta", rol_id="ROLE_CONSULTA", estado="ACTIVO"),
                Persona(id_persona="ana", nombre="Ana Cero", cedula="0012345678", area="Operaciones"),
                Persona(id_persona="bea", nombre="Beatriz Dos", cedula="0098765432", area="Talento Humano"),
            ])
            session.flush()
            session.add(LoteImportacionAusentismo(
                id_lote="lote-xlsx", nombre_archivo="ausencias.xlsx", contenido_archivo=b"xlsx", usuario_id="admin",
                estado="CONFIRMADO", total_filas=1, filas_validas=1, filas_con_error=0, filas_duplicadas=0,
                filas_importadas=1, fecha_creacion="2026-09-15T10:00:00+00:00", creado_por="admin@example.com",
            ))
            session.flush()
            session.add_all([
                Ausentismo(id_ausentismo="historico", persona_id="ana", fecha_inicio="2026-09-01", fecha_fin="2026-09-02",
                            tipo_ausentismo="MEDICO", motivo="Histórico", fecha_creacion="2026-09-01T09:00:00+00:00"),
                Ausentismo(id_ausentismo="importado", persona_id="ana", lote_id="lote-xlsx", fecha_inicio="2026-09-10", fecha_fin="2026-09-12",
                            tipo_ausentismo="MEDICO", motivo="Certificado", observacion="Revisado",
                            fecha_creacion="2026-09-15T10:00:00+00:00"),
                Ausentismo(id_ausentismo="personal", persona_id="bea", fecha_inicio="2026-09-08", fecha_fin="2026-09-08",
                            tipo_ausentismo="PERSONAL", motivo="Permiso", fecha_creacion="2026-09-08T10:00:00+00:00"),
            ])

        def override_db():
            with Session(self.engine) as session:
                try:
                    yield session
                    session.commit()
                except Exception:
                    session.rollback()
                    raise

        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)
        self.login("admin@example.com")

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        db_session.engine = self.original_engine
        self.engine.dispose()
        self.directory.cleanup()

    def login(self, correo):
        response = self.client.post("/api/v1/auth/login", json={"correo": correo, "password": "irrelevante"})
        self.assertEqual(response.status_code, 200)

    def test_list_returns_individual_records_with_real_person_lot_author_and_pagination(self):
        response = self.client.get("/api/v1/ausentismos", params={"limite": 1, "offset": 0})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual((body["total"], body["limite"], body["offset"], len(body["items"])), (3, 1, 0, 1))
        item = body["items"][0]
        self.assertEqual(item["id_ausentismo"], "importado")
        self.assertEqual(item["persona_id"], "ana")
        self.assertEqual(item["persona"], "Ana Cero")
        self.assertEqual(item["cedula"], "0012345678")
        self.assertEqual(item["area"], "Operaciones")
        self.assertEqual(item["tipo_ausentismo"], "MEDICO")
        self.assertEqual(item["origen"], "IMPORTACION_XLSX")
        self.assertEqual((item["lote_id"], item["lote_nombre_archivo"]), ("lote-xlsx", "ausencias.xlsx"))
        self.assertEqual((item["registrado_por_id"], item["registrado_por"]), ("admin", "Administradora"))
        second_page = self.client.get("/api/v1/ausentismos", params={"limite": 1, "offset": 1}).json()
        self.assertEqual(second_page["items"][0]["id_ausentismo"], "personal")

    def test_filters_are_server_side_and_combinable(self):
        cases = (
            ({"nombre": "Ana"}, {"historico", "importado"}),
            ({"cedula": "0012345678"}, {"historico", "importado"}),
            ({"area": "Talento Humano"}, {"personal"}),
            ({"tipo_ausentismo": "PERSONAL"}, {"personal"}),
            ({"desde": "2026-09-09"}, {"importado"}),
            ({"hasta": "2026-09-08"}, {"historico", "personal"}),
            ({"lote_id": "lote-xlsx"}, {"importado"}),
            ({"origen": "IMPORTACION_XLSX"}, {"importado"}),
            ({"nombre": "Ana", "tipo_ausentismo": "MEDICO", "desde": "2026-09-09", "lote_id": "lote-xlsx"}, {"importado"}),
        )
        for params, expected in cases:
            with self.subTest(params=params):
                response = self.client.get("/api/v1/ausentismos", params=params)
                self.assertEqual(response.status_code, 200)
                self.assertEqual({item["id_ausentismo"] for item in response.json()["items"]}, expected)
        invalid = self.client.get("/api/v1/ausentismos", params={"origen": "MANUAL"})
        self.assertEqual((invalid.status_code, invalid.json()["code"]), (422, "INVALID_ORIGIN"))

    def test_detail_exposes_only_operational_data_and_historical_record_does_not_invent_author(self):
        response = self.client.get("/api/v1/ausentismos/importado")
        self.assertEqual(response.status_code, 200)
        item = response.json()
        self.assertEqual((item["fecha_inicio"], item["fecha_fin"], item["motivo"], item["observacion"]),
                         ("2026-09-10", "2026-09-12", "Certificado", "Revisado"))
        self.assertNotIn("contenido_archivo", item)
        historic = self.client.get("/api/v1/ausentismos/historico")
        self.assertEqual(historic.status_code, 200)
        self.assertIsNone(historic.json()["origen"])
        self.assertIsNone(historic.json()["lote_id"])
        self.assertIsNone(historic.json()["registrado_por_id"])
        self.assertIsNone(historic.json()["registrado_por"])
        absent = self.client.get("/api/v1/ausentismos/no-existe")
        self.assertEqual((absent.status_code, absent.json()["code"]), (404, "NOT_FOUND"))

    def test_list_and_detail_require_session_and_ausentismo_read_permission(self):
        self.assertEqual(self.client.post("/api/v1/auth/logout").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/ausentismos").status_code, 401)
        self.login("consulta@example.com")
        self.assertEqual(self.client.get("/api/v1/ausentismos").status_code, 403)
        self.assertEqual(self.client.get("/api/v1/ausentismos/importado").status_code, 403)
