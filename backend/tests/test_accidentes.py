import unittest
from io import BytesIO
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.api.deps import get_db
from app.db.session import build_engine
from app.main import app
from app.models import Accidente, Persona, User
from app.services.security_seed import seed_security


def xlsx(headers, rows):
    book = Workbook(); sheet = book.active; sheet.append(headers)
    for row in rows: sheet.append(row)
    output = BytesIO(); book.save(output); return output.getvalue()


class AccidentesApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(); self.engine = build_engine(f"sqlite:///{self.temp.name}/test.db"); self.original = db_session.engine; db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")
        with Session(self.engine) as session, session.begin():
            seed_security(session); session.add_all([User(id_usuario="admin", correo="admin@example.com", nombre="Admin", rol_id="ROLE_ADMIN", estado="ACTIVO"), User(id_usuario="consulta", correo="consulta@example.com", nombre="Consulta", rol_id="ROLE_CONSULTA", estado="ACTIVO"), Persona(id_persona="ana", nombre="Ana", cedula="0012345678", area="Operaciones")])
        def override():
            with Session(self.engine) as session:
                try: yield session; session.commit()
                except Exception: session.rollback(); raise
        app.dependency_overrides[get_db] = override; self.client = TestClient(app); self.login("admin@example.com")
    def tearDown(self): self.client.close(); app.dependency_overrides.clear(); db_session.engine = self.original; self.engine.dispose(); self.temp.cleanup()
    def login(self, email): self.assertEqual(self.client.post("/api/v1/auth/login", json={"correo":email,"password":"x"}).status_code, 200)
    def test_manual_list_detail_filters_and_auth(self):
        self.client.post("/api/v1/auth/logout"); self.assertEqual(self.client.get("/api/v1/accidentes").status_code, 401); self.login("consulta@example.com"); self.assertEqual(self.client.get("/api/v1/accidentes").status_code, 403); self.login("admin@example.com")
        bad = self.client.post("/api/v1/accidentes", json={"persona_id":"no","fecha_accidente":"2026-09-01","clasificacion":"LEVE","descripcion":"x"}); self.assertEqual(bad.status_code, 422)
        created = self.client.post("/api/v1/accidentes", json={"persona_id":"ana","fecha_accidente":"2026-09-01","clasificacion":"LEVE","descripcion":"Golpe"}); self.assertEqual(created.status_code, 201); record = created.json(); self.assertEqual(record["origen"], "REGISTRO_MANUAL")
        self.assertEqual(self.client.get("/api/v1/accidentes", params={"nombre":"Ana","clasificacion":"LEVE","limite":1}).json()["total"], 1); self.assertEqual(self.client.get(f"/api/v1/accidentes/{record['id_accidente']}").status_code, 200)
    def test_import_analysis_issues_atomic_confirmation_and_history(self):
        invalid = self.client.post("/api/v1/importaciones/accidentes/analizar", files={"archivo":("x.txt",b"x","text/plain")}); self.assertEqual(invalid.status_code, 422)
        content = xlsx(["cedula","fecha_accidente","clasificacion","descripcion"], [["0012345678","2026-09-02","LEVE","Golpe"],["0012345678","2026-09-02","LEVE","Duplicado"]])
        analysis = self.client.post("/api/v1/importaciones/accidentes/analizar", files={"archivo":("accidentes.xlsx",content,"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}); self.assertEqual(analysis.status_code, 201); lot = analysis.json()["lote"]; self.assertFalse(analysis.json()["puede_confirmarse"]); self.assertEqual(self.client.get(f"/api/v1/importaciones/accidentes/{lot['id_lote']}/errores").json()["total"], 1); self.assertEqual(self.client.post(f"/api/v1/importaciones/accidentes/{lot['id_lote']}/confirmar").status_code, 422)
        valid = xlsx(["cedula","fecha_accidente","clasificacion","descripcion","estado"], [["0012345678","2026-09-03","GRAVE","Caída","ABIERTO"]]); response = self.client.post("/api/v1/importaciones/accidentes/analizar", files={"archivo":("validos.xlsx",valid,"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}); lot = response.json()["lote"]; confirmed = self.client.post(f"/api/v1/importaciones/accidentes/{lot['id_lote']}/confirmar"); self.assertEqual(confirmed.status_code, 200); self.assertEqual(self.client.post(f"/api/v1/importaciones/accidentes/{lot['id_lote']}/confirmar").status_code, 409); self.assertEqual(self.client.get("/api/v1/importaciones/accidentes").json()["total"], 2)
        with Session(self.engine) as session: self.assertEqual(session.query(Accidente).count(), 1)
