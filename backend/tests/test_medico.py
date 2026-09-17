import unittest
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.api.deps import get_db
from app.db.session import build_engine
from app.main import app
from app.models import Atencion, Permission, Role, User
from app.services.security_seed import seed_security


class MedicoAtencionesApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.engine = build_engine(f"sqlite:///{self.temp.name}/medico.db")
        self.original = db_session.engine
        db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")
        with Session(self.engine) as session, session.begin():
            seed_security(session)
            session.add_all([
                Role(id_rol="ROLE_MED", nombre="Médico", descripcion="Atenciones médicas"),
                User(id_usuario="med", correo="med@example.com", nombre="Médica", rol_id="ROLE_MED", estado="ACTIVO"),
                Atencion(id_atencion="legacy", motivo="Legado", contexto_operativo=None),
                Atencion(id_atencion="production", motivo="Producción", contexto_operativo="PRODUCCION"),
                Atencion(id_atencion="office", motivo="Oficina", contexto_operativo="OFICINA"),
            ])
            session.flush()
            for module, rights in {
                "ATENCIONES": {"puede_crear": True, "puede_leer": True, "puede_editar": True, "puede_eliminar": True},
                "DOCUMENTOS": {"puede_crear": True, "puede_leer": True, "puede_editar": True, "puede_eliminar": True},
                "AUDITORIA": {"puede_leer": True},
            }.items():
                session.add(Permission(id_permiso=f"med-{module}", rol_id="ROLE_MED", modulo=module, **rights))

        def override():
            with Session(self.engine) as session:
                try:
                    yield session
                    session.commit()
                except Exception:
                    session.rollback()
                    raise
        app.dependency_overrides[get_db] = override
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        db_session.engine = self.original
        self.engine.dispose()
        self.temp.cleanup()

    def login(self):
        self.assertEqual(self.client.post("/api/v1/auth/login", json={"correo": "med@example.com", "password": "x"}).status_code, 200)

    def test_medical_surface_is_explicit_and_isolates_legacy_and_other_contexts(self):
        self.login()
        created = self.client.post("/api/v1/medico/atenciones", json={"motivo": "Consulta", "contexto_operativo": "OFICINA"})
        self.assertEqual(created.status_code, 201, created.text)
        created = created.json()
        self.assertEqual(created["contexto_operativo"], "MEDICO")
        listed = self.client.get("/api/v1/medico/atenciones")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual([item["id_atencion"] for item in listed.json()["items"]], [created["id_atencion"]])
        for record_id in ("legacy", "production", "office"):
            self.assertEqual(self.client.get(f"/api/v1/medico/atenciones/{record_id}").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/atenciones").json()[0]["id_atencion"], "legacy")
        self.assertEqual(self.client.post("/api/v1/atenciones", json={"motivo": "No clasificada"}).status_code, 409)

    def test_transversal_mutations_history_restore_and_documents_are_not_reachable(self):
        self.login()
        for record_id in ("production", "office"):
            self.assertEqual(self.client.patch(f"/api/v1/medico/atenciones/{record_id}", json={"expected_version": 1, "motivo": "Ajeno"}).status_code, 404)
            self.assertEqual(self.client.post(f"/api/v1/medico/atenciones/{record_id}/eliminacion", json={"expected_version": 1, "motivo": "Ajeno"}).status_code, 404)
            self.assertEqual(self.client.post(f"/api/v1/medico/atenciones/{record_id}/restauracion").status_code, 404)
            self.assertEqual(self.client.get(f"/api/v1/medico/atenciones/{record_id}/historial").status_code, 404)
            self.assertEqual(self.client.get(f"/api/v1/medico/atenciones/{record_id}/documentos").status_code, 404)
        created = self.client.post("/api/v1/medico/atenciones", json={"motivo": "Válida"}).json()
        self.assertEqual(self.client.get(f"/api/v1/medico/atenciones/{created['id_atencion']}/historial").status_code, 200)
        deleted = self.client.post(f"/api/v1/medico/atenciones/{created['id_atencion']}/eliminacion", json={"expected_version": created['version'], "motivo": "Archivo"})
        self.assertEqual(deleted.status_code, 200, deleted.text)
        self.assertEqual(self.client.post(f"/api/v1/medico/atenciones/{created['id_atencion']}/restauracion").status_code, 200)


class MedicoMigrationTests(unittest.TestCase):
    def test_0024_accepts_medico_without_reclassifying_null_legacy(self):
        with TemporaryDirectory() as directory:
            engine = build_engine(f"sqlite:///{directory}/migration.db")
            original = db_session.engine
            db_session.engine = engine
            try:
                config = Config("alembic.ini")
                command.upgrade(config, "0023_respuesta_documentos")
                with engine.begin() as connection:
                    connection.execute(Atencion.__table__.insert().values(id_atencion="legacy", motivo="Antes", contexto_operativo=None))
                command.upgrade(config, "head")
                with Session(engine) as session:
                    self.assertIsNone(session.get(Atencion, "legacy").contexto_operativo)
                    session.add(Atencion(id_atencion="medical", motivo="Después", contexto_operativo="MEDICO"))
                    session.commit()
                    session.delete(session.get(Atencion, "medical"))
                    session.commit()
                command.downgrade(config, "0023_respuesta_documentos")
                self.assertIn("contexto_operativo", {column["name"] for column in inspect(engine).get_columns("atenciones")})
            finally:
                db_session.engine = original
                engine.dispose()


if __name__ == "__main__":
    unittest.main()
