"""Recorrido HTTP de los flujos críticos con una base temporal aislada."""

import unittest
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_db
import app.db.session as db_session
from app.db.session import build_engine
from app.main import app
from app.models import User
from app.services.security_seed import seed_security


class ApiIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.engine = build_engine(f"sqlite:///{self.directory.name}/integration.db")
        self._original_engine = db_session.engine
        db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")
        with Session(self.engine) as session, session.begin():
            seed_security(session)
            session.add(User(id_usuario="admin", correo="admin@example.com", nombre="Admin",
                             rol_id="ROLE_ADMIN", estado="ACTIVO"))

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

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        db_session.engine = self._original_engine
        self.engine.dispose()
        self.directory.cleanup()

    def test_auth_case_followup_document_history_close_and_logout(self):
        login = self.client.post("/api/v1/auth/login", json={"correo": "admin@example.com", "password": "ClaveSegura123"})
        self.assertEqual(login.status_code, 200)
        self.assertIn("HttpOnly", login.headers["set-cookie"])

        created = self.client.post("/api/v1/casos", json={
            "responsable": "Ana", "estado_caso": "PENDIENTE", "prioridad": "ALTA",
            "fecha_apertura": "2026-09-06", "motivo_auditoria": "Prueba integral",
        })
        self.assertEqual(created.status_code, 201)
        case = created.json()
        case_id = case["id_caso"]

        updated = self.client.patch(f"/api/v1/casos/{case_id}", json={
            "responsable": "Beatriz", "expected_version": case["version"], "motivo_auditoria": "Asignación",
        })
        self.assertEqual(updated.status_code, 200)

        followup = self.client.post(f"/api/v1/casos/{case_id}/seguimientos", json={
            "fecha": "2026-09-06", "descripcion": "Contacto realizado", "fecha_proxima_accion": "2026-09-07",
        })
        self.assertEqual(followup.status_code, 201)
        self.assertEqual(len(self.client.get(f"/api/v1/casos/{case_id}/seguimientos").json()), 1)

        pdf = b"%PDF-1.4\n%integration\n%%EOF"
        uploaded = self.client.post("/api/v1/documentos", data={"tipo_registro": "CASOS", "id_registro": case_id},
                                    files={"archivo": ("reporte.pdf", pdf, "application/pdf")})
        self.assertEqual(uploaded.status_code, 201)
        document = uploaded.json()
        self.assertEqual(self.client.get(f"/api/v1/documentos/{document['id_archivo']}/contenido").content, pdf)
        deleted = self.client.post(f"/api/v1/documentos/{document['id_archivo']}/eliminacion", json={
            "expected_version": document["version"], "motivo": "Archivo duplicado",
        })
        self.assertEqual(deleted.status_code, 200)

        current = self.client.get(f"/api/v1/casos/{case_id}").json()
        closed = self.client.post(f"/api/v1/casos/{case_id}/cierres", json={
            "expected_version": current["version"], "fecha_cierre_caso": "2026-09-06",
            "responsable": "Beatriz", "motivo_cierre": "Resuelto",
        })
        self.assertEqual(closed.status_code, 201)
        self.assertGreaterEqual(len(self.client.get(f"/api/v1/casos/{case_id}/historial").json()), 3)

        self.assertEqual(self.client.post("/api/v1/auth/logout").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/casos").status_code, 401)


if __name__ == "__main__":
    unittest.main()
