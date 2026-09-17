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
from app.models import Permission, Persona, Role, User
from app.services.security_seed import seed_security


class OficinaEntidadesApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(); self.engine = build_engine(f"sqlite:///{self.temp.name}/office-entities.db")
        self.original = db_session.engine; db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")
        with Session(self.engine) as session, session.begin():
            seed_security(session)
            session.add_all([
                Role(id_rol="ROLE_OFFICE_ENTITIES", nombre="Oficina", descripcion="Solo Oficina"),
                User(id_usuario="office-entities", correo="entities@example.com", nombre="Operadora", rol_id="ROLE_OFFICE_ENTITIES", estado="ACTIVO"),
                Persona(id_persona="persona", nombre="Ana Oficina", cedula="0012345678", area="Administración"),
            ])
            session.flush()
            session.add_all([
                Permission(id_permiso="entities-OFICINA", rol_id="ROLE_OFFICE_ENTITIES", modulo="OFICINA", puede_crear=True, puede_leer=True, puede_editar=True, puede_eliminar=True),
                Permission(id_permiso="entities-AUDITORIA", rol_id="ROLE_OFFICE_ENTITIES", modulo="AUDITORIA", puede_leer=True),
            ])
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
        self.assertEqual(self.client.post("/api/v1/auth/login", json={"correo": "entities@example.com", "password": "x"}).status_code, 200)

    def test_beneficios_types_person_author_scope_filters_and_lifecycle(self):
        self.assertEqual(self.client.get("/api/v1/oficina/beneficios").status_code, 401)
        self.login()
        self.assertEqual(self.client.get("/api/v1/produccion/atenciones").status_code, 403)
        records = []
        for benefit, management in (("TIA", "ACTIVACION"), ("TIA", "BLOQUEO"), ("FARMACIA", "ANULACION")):
            response = self.client.post("/api/v1/oficina/beneficios", json={"fecha": "2026-09-10", "persona_id": "persona", "tipo_beneficio": benefit, "tipo_gestion": management, "descripcion": "Gestión", "responsable": "Rosa"})
            self.assertEqual(response.status_code, 201, response.text); records.append(response.json())
        nullable = self.client.post("/api/v1/oficina/beneficios", json={"tipo_beneficio": "TIA", "tipo_gestion": "ACTIVACION"})
        self.assertEqual(nullable.status_code, 201, nullable.text); self.assertIsNone(nullable.json()["persona_id"])
        self.assertEqual(records[0]["registrado_por"], "entities@example.com")
        self.assertEqual(self.client.post("/api/v1/oficina/beneficios", json={"tipo_beneficio": "OTRO", "tipo_gestion": "ACTIVACION"}).status_code, 422)
        listed = self.client.get("/api/v1/oficina/beneficios", params={"nombre": "Ana", "cedula": "0012345678", "area": "Administración", "responsable": "Rosa", "fecha": "2026-09-10", "tipo": "TIA", "tipo_gestion": "ACTIVACION", "limite": 1, "offset": 0})
        self.assertEqual((listed.status_code, listed.json()["total"], len(listed.json()["items"])), (200, 1, 1))
        changed = self.client.patch(f"/api/v1/oficina/beneficios/{records[0]['id_beneficio']}", json={"expected_version": records[0]['version'], "observacion": "Actualizada"})
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertTrue(self.client.get(f"/api/v1/oficina/beneficios/{records[0]['id_beneficio']}/historial").json())
        self.assertEqual(self.client.post(f"/api/v1/oficina/beneficios/{records[0]['id_beneficio']}/eliminacion", json={"expected_version": changed.json()['version'], "motivo": "Archivo"}).status_code, 200)

    def test_prestamos_are_operational_and_do_not_require_financial_fields(self):
        self.login()
        for kind in ("PRESTAMO", "ANTICIPO"):
            response = self.client.post("/api/v1/oficina/prestamos", json={"fecha": "2026-09-10", "persona_id": "persona", "tipo": kind, "descripcion": "Gestión"})
            self.assertEqual(response.status_code, 201, response.text)
            self.assertNotIn("monto", response.json())
        nullable = self.client.post("/api/v1/oficina/prestamos", json={"tipo": "PRESTAMO"})
        self.assertEqual(nullable.status_code, 201, nullable.text); self.assertIsNone(nullable.json()["persona_id"])
        self.assertEqual(self.client.post("/api/v1/oficina/prestamos", json={"tipo": "CREDITO"}).status_code, 422)
        page = self.client.get("/api/v1/oficina/prestamos", params={"nombre": "Ana", "tipo": "ANTICIPO", "limite": 1, "offset": 0})
        self.assertEqual((page.status_code, page.json()["total"], len(page.json()["items"])), (200, 1, 1))

    def test_seguro_managements_allow_nullable_person_and_no_dependent_structure(self):
        self.login()
        for management in ("AFILIACION", "ENROLAMIENTO", "COBERTURA", "REEMBOLSO", "PRIMA", "DEPENDIENTE"):
            payload = {"fecha": "2026-09-10", "tipo_gestion": management, "descripcion": "Gestión"}
            if management != "DEPENDIENTE": payload["persona_id"] = "persona"
            response = self.client.post("/api/v1/oficina/seguro", json=payload)
            self.assertEqual(response.status_code, 201, response.text)
            if management == "DEPENDIENTE": self.assertIsNone(response.json()["persona_id"])
        self.assertEqual(self.client.post("/api/v1/oficina/seguro", json={"tipo_gestion": "POLIZA"}).status_code, 422)
        page = self.client.get("/api/v1/oficina/seguro", params={"tipo_gestion": "DEPENDIENTE", "limite": 1, "offset": 0})
        self.assertEqual((page.status_code, page.json()["total"], len(page.json()["items"])), (200, 1, 1))


class OficinaEntidadesMigrationTests(unittest.TestCase):
    def test_upgrade_downgrade_constraints_foreign_keys_and_indexes(self):
        with TemporaryDirectory() as directory:
            engine = build_engine(f"sqlite:///{directory}/migration.db"); original = db_session.engine; db_session.engine = engine
            try:
                config = Config("alembic.ini"); command.upgrade(config, "0021_contexto_operativo_atenciones"); command.upgrade(config, "0022_beneficios_prestamos_seguros")
                inspector = inspect(engine)
                for table, index in (("beneficios", "ix_beneficios_tipo_fecha"), ("prestamos", "ix_prestamos_tipo_fecha"), ("seguros", "ix_seguros_tipo_gestion_fecha")):
                    self.assertIn(table, inspector.get_table_names()); self.assertIn(index, {row["name"] for row in inspector.get_indexes(table)})
                    self.assertTrue(any(fk["referred_table"] == "personas" for fk in inspector.get_foreign_keys(table)))
                command.downgrade(config, "0021_contexto_operativo_atenciones")
                self.assertNotIn("beneficios", inspect(engine).get_table_names())
                command.upgrade(config, "0022_beneficios_prestamos_seguros"); self.assertIn("seguros", inspect(engine).get_table_names())
            finally:
                db_session.engine = original; engine.dispose()


if __name__ == "__main__":
    unittest.main()
