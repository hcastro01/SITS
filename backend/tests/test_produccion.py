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
from app.models import Atencion, Novedad, Permission, Persona, Recorrido, Role, User
from app.services.security_seed import seed_security


class ProduccionApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(); self.engine = build_engine(f"sqlite:///{self.temp.name}/production.db")
        self.original = db_session.engine; db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")
        with Session(self.engine) as session, session.begin():
            seed_security(session)
            session.add_all([Role(id_rol="ROLE_PROD", nombre="Producción", descripcion="Solo Producción"),
                             User(id_usuario="prod", correo="prod@example.com", nombre="Operador", rol_id="ROLE_PROD", estado="ACTIVO"),
                             Persona(id_persona="persona", nombre="Ana Producción", cedula="0012345678", area="Planta")])
            session.flush()
            for module, rights in {"PRODUCCION": {"puede_crear": True, "puede_leer": True, "puede_editar": True, "puede_eliminar": True}, "AUDITORIA": {"puede_leer": True}}.items():
                session.add(Permission(id_permiso=f"prod-{module}", rol_id="ROLE_PROD", modulo=module, **rights))
            session.add_all([
                Atencion(id_atencion="historic", fecha="2026-09-01", motivo="Histórica", contexto_operativo=None),
                Atencion(id_atencion="office", fecha="2026-09-02", motivo="Oficina", contexto_operativo="OFICINA"),
            ])
        def override():
            with Session(self.engine) as session:
                try: yield session; session.commit()
                except Exception: session.rollback(); raise
        app.dependency_overrides[get_db] = override; self.client = TestClient(app)

    def tearDown(self):
        self.client.close(); app.dependency_overrides.clear(); db_session.engine = self.original; self.engine.dispose(); self.temp.cleanup()

    def login(self):
        self.assertEqual(self.client.post("/api/v1/auth/login", json={"correo": "prod@example.com", "password": "x"}).status_code, 200)

    def test_atenciones_force_context_scope_filters_pagination_and_history(self):
        self.assertEqual(self.client.get("/api/v1/produccion/atenciones").status_code, 401)
        self.login(); self.assertEqual(self.client.get("/api/v1/atenciones").status_code, 403)
        first = self.client.post("/api/v1/produccion/atenciones", json={"id_persona": "persona", "fecha": "2026-09-10", "motivo": "Producción", "responsable": "Rosa", "estado": "ABIERTO", "contexto_operativo": "OFICINA"})
        self.assertEqual(first.status_code, 201, first.text); created = first.json()
        self.assertEqual(created["contexto_operativo"], "PRODUCCION"); self.assertEqual(created["persona"], "Ana Producción"); self.assertEqual(created["cedula"], "0012345678")
        second = self.client.post("/api/v1/produccion/atenciones", json={"fecha": "2026-09-11", "motivo": "Otra", "estado": "CERRADO"}).json()
        listed = self.client.get("/api/v1/produccion/atenciones", params={"nombre": "Ana", "cedula": "0012345678", "area": "Planta", "responsable": "Rosa", "estado": "ABIERTO", "desde": "2026-09-01", "hasta": "2026-09-10", "limite": 1, "offset": 0}).json()
        self.assertEqual((listed["total"], len(listed["items"])), (1, 1)); self.assertEqual(self.client.get("/api/v1/produccion/atenciones/historic").status_code, 404); self.assertEqual(self.client.get("/api/v1/produccion/atenciones/office").status_code, 404)
        changed = self.client.patch(f"/api/v1/produccion/atenciones/{created['id_atencion']}", json={"expected_version": created["version"], "motivo": "Editada", "contexto_operativo": "OFICINA"})
        self.assertEqual(changed.status_code, 200); self.assertEqual(changed.json()["contexto_operativo"], "PRODUCCION")
        self.assertTrue(self.client.get(f"/api/v1/produccion/atenciones/{created['id_atencion']}/historial").json())
        self.assertEqual(self.client.get(f"/api/v1/produccion/atenciones/{second['id_atencion']}").status_code, 200)

    def test_recorridos_and_novedades_reuse_models_with_production_scope(self):
        self.login()
        recorrido = self.client.post("/api/v1/produccion/recorridos", json={"fecha": "2026-09-10", "objetivo": "Recorrido", "id_persona": "persona"})
        self.assertEqual(recorrido.status_code, 201, recorrido.text); recorrido = recorrido.json()
        self.assertEqual(self.client.get("/api/v1/produccion/recorridos", params={"nombre": "Ana", "limite": 1}).json()["total"], 1)
        self.assertEqual(self.client.patch(f"/api/v1/produccion/recorridos/{recorrido['id_recorrido']}", json={"expected_version": recorrido["version"], "objetivo": "Editado"}).status_code, 200)
        novedad = self.client.post("/api/v1/produccion/novedades", json={"fecha": "2026-09-10", "descripcion": "Novedad de planta", "estado": "ABIERTO"})
        self.assertEqual(novedad.status_code, 201, novedad.text); novedad = novedad.json()
        self.assertIsNone(novedad["id_persona"]); self.assertEqual(self.client.get("/api/v1/produccion/novedades", params={"estado": "ABIERTO", "limite": 1}).json()["total"], 1)
        self.assertEqual(self.client.patch(f"/api/v1/produccion/novedades/{novedad['id_novedad']}", json={"expected_version": novedad["version"], "descripcion": "Editada"}).status_code, 200)
        with Session(self.engine) as session:
            self.assertIsNotNone(session.get(Recorrido, recorrido["id_recorrido"])); self.assertIsNotNone(session.get(Novedad, novedad["id_novedad"]))


class ProduccionMigrationTests(unittest.TestCase):
    def test_context_upgrade_downgrade_upgrade_and_null_history(self):
        with TemporaryDirectory() as directory:
            engine = build_engine(f"sqlite:///{directory}/migration.db"); original = db_session.engine; db_session.engine = engine
            try:
                config = Config("alembic.ini"); command.upgrade(config, "0020_indice_casos_riesgos")
                with engine.begin() as connection: connection.execute(Atencion.__table__.insert().values(id_atencion="historic", motivo="Antes"))
                command.upgrade(config, "head")
                columns = {row["name"] for row in inspect(engine).get_columns("atenciones")}; indexes = {row["name"] for row in inspect(engine).get_indexes("atenciones")}
                self.assertIn("contexto_operativo", columns); self.assertIn("ix_atenciones_contexto_fecha", indexes)
                with Session(engine) as session: self.assertIsNone(session.get(Atencion, "historic").contexto_operativo)
                command.downgrade(config, "0020_indice_casos_riesgos"); self.assertNotIn("contexto_operativo", {row["name"] for row in inspect(engine).get_columns("atenciones")})
                command.upgrade(config, "head"); self.assertIn("contexto_operativo", {row["name"] for row in inspect(engine).get_columns("atenciones")})
            finally: db_session.engine = original; engine.dispose()


if __name__ == "__main__": unittest.main()
