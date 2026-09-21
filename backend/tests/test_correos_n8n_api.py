import os
import unittest
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

os.environ["N8N_SITS_API_KEY"] = "test-n8n-key-not-a-secret"

from app.api.correos import get_db as correos_get_db
from app.core.config import get_settings
import app.db.session as db_session
from app.db.session import build_engine
from app.main import app
from app.models import Correo


class CorreosN8nApiTests(unittest.TestCase):
    def setUp(self):
        get_settings.cache_clear()
        self.directory = TemporaryDirectory()
        self.engine = build_engine(f"sqlite:///{self.directory.name}/test.db")
        self.original_engine = db_session.engine
        db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")

        def test_db():
            with Session(self.engine) as session:
                try:
                    yield session
                    session.commit()
                except Exception:
                    session.rollback()
                    raise
        # El router captura la dependencia al importarse; sobrescribimos esa referencia.
        app.dependency_overrides[correos_get_db] = test_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        db_session.engine = self.original_engine
        self.engine.dispose()
        self.directory.cleanup()

    @staticmethod
    def payload(**overrides):
        payload = {
            "MessageId": "<n8n-message-1@example.test>", "Subject": "Solicitud válida",
            "From": "ana@example.test", "To": "social@example.test",
            "ReceivedTime": "2026-09-21T08:30:00-05:00", "Body": "Contenido con ñ y <script>alert(1)</script>",
            "HasAttachments": False, "IsRead": False, "Category": "CASOS_TALENTO_HUMANO",
        }
        payload.update(overrides)
        return payload

    def test_requires_a_valid_bearer_token_and_is_idempotent(self):
        url = "/api/v1/correos/integraciones/n8n"
        self.assertEqual(self.client.post(url, json=self.payload()).status_code, 401)
        self.assertEqual(self.client.post(url, headers={"Authorization": "Bearer invalid"}, json=self.payload()).status_code, 401)
        first = self.client.post(url, headers={"Authorization": "Bearer test-n8n-key-not-a-secret"}, json=self.payload())
        again = self.client.post(url, headers={"Authorization": "Bearer test-n8n-key-not-a-secret"}, json=self.payload())
        self.assertEqual((first.status_code, again.status_code), (201, 200))
        self.assertEqual((first.json()["created"], again.json()["duplicate"]), (True, True))
        with Session(self.engine) as session:
            rows = session.scalars(select(Correo).where(Correo.id_externo_correo == "<n8n-message-1@example.test>")).all()
            self.assertEqual(len(rows), 1)

    def test_rejects_missing_message_id_and_invalid_date_without_echoing_key(self):
        headers = {"Authorization": "Bearer test-n8n-key-not-a-secret"}
        missing = self.client.post("/api/v1/correos/integraciones/n8n", headers=headers, json=self.payload(MessageId=""))
        invalid_date = self.client.post("/api/v1/correos/integraciones/n8n", headers=headers, json=self.payload(ReceivedTime="not-a-date"))
        self.assertEqual((missing.status_code, invalid_date.status_code), (422, 422))
        self.assertNotIn("test-n8n-key-not-a-secret", str(missing.json()) + str(invalid_date.json()))


if __name__ == "__main__":
    unittest.main()
