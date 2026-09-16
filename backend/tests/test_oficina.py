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
from app.models import Atencion, Permission, Persona, Role, User
from app.services.security_seed import seed_security


class OficinaAtencionesApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(); self.engine = build_engine(f"sqlite:///{self.temp.name}/office.db")
        self.original = db_session.engine; db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")
        with Session(self.engine) as session, session.begin():
            seed_security(session)
            session.add_all([
                Role(id_rol="ROLE_OFFICE", nombre="Oficina", descripcion="Solo Oficina"),
                User(id_usuario="office", correo="office@example.com", nombre="Operadora", rol_id="ROLE_OFFICE", estado="ACTIVO"),
                Persona(id_persona="persona", nombre="Ana Oficina", cedula="0012345678", area="Administración"),
                Atencion(id_atencion="historic", fecha="2026-09-01", motivo="Histórica", contexto_operativo=None),
                Atencion(id_atencion="production", fecha="2026-09-02", motivo="Producción", contexto_operativo="PRODUCCION"),
            ])
            session.flush()
            session.add(Permission(id_permiso="office-OFICINA", rol_id="ROLE_OFFICE", modulo="OFICINA",
                                   puede_crear=True, puede_leer=True, puede_editar=True, puede_eliminar=True))
            session.add(Permission(id_permiso="office-AUDITORIA", rol_id="ROLE_OFFICE", modulo="AUDITORIA", puede_leer=True))

        def override():
            with Session(self.engine) as session:
                try:
                    yield session; session.commit()
                except Exception:
                    session.rollback(); raise
        app.dependency_overrides[get_db] = override; self.client = TestClient(app)

    def tearDown(self):
        self.client.close(); app.dependency_overrides.clear(); db_session.engine = self.original
        self.engine.dispose(); self.temp.cleanup()

    def login(self):
        self.assertEqual(self.client.post("/api/v1/auth/login", json={"correo": "office@example.com", "password": "x"}).status_code, 200)

    def test_context_is_forced_isolated_and_paged(self):
        self.assertEqual(self.client.get("/api/v1/oficina/atenciones").status_code, 401)
        self.login()
        self.assertEqual(self.client.get("/api/v1/produccion/atenciones").status_code, 403)
        created = self.client.post("/api/v1/oficina/atenciones", json={
            "fecha": "2026-09-10", "motivo": "Oficina", "responsable": "Rosa", "estado": "ABIERTO",
            "id_persona": "persona", "contexto_operativo": "PRODUCCION",
        })
        self.assertEqual(created.status_code, 201, created.text); created = created.json()
        self.assertEqual(created["contexto_operativo"], "OFICINA")
        listed = self.client.get("/api/v1/oficina/atenciones", params={
            "nombre": "Ana", "cedula": "0012345678", "area": "Administración", "responsable": "Rosa",
            "estado": "ABIERTO", "desde": "2026-09-01", "hasta": "2026-09-10", "limite": 1, "offset": 0,
        })
        self.assertEqual((listed.status_code, listed.json()["total"], len(listed.json()["items"])), (200, 1, 1))
        self.assertEqual(self.client.get("/api/v1/oficina/atenciones/production").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/oficina/atenciones/historic").status_code, 404)
        changed = self.client.patch(f"/api/v1/oficina/atenciones/{created['id_atencion']}", json={
            "expected_version": created["version"], "motivo": "Editada", "contexto_operativo": "PRODUCCION",
        })
        self.assertEqual(changed.status_code, 200, changed.text); changed = changed.json()
        self.assertEqual(changed["contexto_operativo"], "OFICINA")
        self.assertTrue(self.client.get(f"/api/v1/oficina/atenciones/{created['id_atencion']}/historial").json())
        deleted = self.client.post(f"/api/v1/oficina/atenciones/{created['id_atencion']}/eliminacion", json={"expected_version": changed["version"], "motivo": "Archivo"})
        self.assertEqual(deleted.status_code, 200, deleted.text)

    def test_scope_is_additive_and_does_not_grant_transversal_access(self):
        self.login()
        self.assertEqual(self.client.get("/api/v1/atenciones").status_code, 403)
        self.assertEqual(self.client.get("/api/v1/produccion/atenciones").status_code, 403)


if __name__ == "__main__":
    unittest.main()
