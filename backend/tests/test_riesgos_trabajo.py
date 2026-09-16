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
from app.models import Caso, DestinoFormulario, EnvioFormulario, Formulario, FormularioDestino, Permission, Persona, Role, User
from app.services.form_destinations import seed_form_destinations
from app.services.security_seed import seed_security


class RiesgosTrabajoApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.engine = build_engine(f"sqlite:///{self.temp.name}/riesgos.db")
        self.original = db_session.engine
        db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")
        with Session(self.engine) as session, session.begin():
            seed_security(session)
            seed_form_destinations(session)
            session.add_all([
                User(id_usuario="admin", correo="admin@example.com", nombre="Admin", rol_id="ROLE_ADMIN", estado="ACTIVO"),
                Persona(id_persona="ana", nombre="Ana López", cedula="0012345678", area="Operaciones"),
                Persona(id_persona="beto", nombre="Beto Pérez", cedula="0098765432", area="Planta"),
                Caso(id_caso="generic", codigo_caso="CAS-GENERIC", tipo_caso="GENERAL", estado_caso="ABIERTO"),
            ])
            session.add(Role(id_rol="ROLE_RIESGOS", nombre="Riesgos", descripcion="Solo Riesgos"))
            session.flush()
            for module, rights in {
                "RIESGOS_TRABAJO": {"puede_crear": True, "puede_leer": True, "puede_editar": True},
                "PERSONAS": {"puede_leer": True}, "SEGUIMIENTOS": {"puede_crear": True, "puede_leer": True},
                "COMPROMISOS": {"puede_leer": True}, "AUDITORIA": {"puede_leer": True},
            }.items():
                session.add(Permission(id_permiso=f"risk-{module}", rol_id="ROLE_RIESGOS", modulo=module, **rights))
            session.add(User(id_usuario="risk", correo="risk@example.com", nombre="Operador Riesgos", rol_id="ROLE_RIESGOS", estado="ACTIVO"))

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

    def login(self, correo="admin@example.com"):
        self.assertEqual(self.client.post("/api/v1/auth/login", json={"correo": correo, "password": "x"}).status_code, 200)

    def create(self, persona="ana", fecha="2026-09-10", **extra):
        payload = {"persona_id": persona, "fecha_apertura": fecha, "responsable": "Ana Responsable", "resultado": "Evaluación inicial"}
        payload.update(extra)
        response = self.client.post("/api/v1/riesgos-trabajo", json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_auth_creation_scope_and_historical_cases(self):
        self.assertEqual(self.client.get("/api/v1/riesgos-trabajo").status_code, 401)
        self.login("risk@example.com")
        self.assertEqual(self.client.get("/api/v1/casos").status_code, 403)
        created = self.create()
        self.assertEqual(created["tipo_caso"], "RIESGOS_TRABAJO")
        self.assertEqual(created["persona_id"], "ana")
        self.assertEqual(created["registrado_por"], "risk@example.com")
        self.assertEqual(self.client.post("/api/v1/riesgos-trabajo", json={"persona_id": "missing", "fecha_apertura": "2026-09-10"}).status_code, 404)
        self.assertEqual(self.client.get("/api/v1/riesgos-trabajo/generic").status_code, 404)
        with Session(self.engine) as session:
            self.assertEqual(session.get(Caso, "generic").tipo_caso, "GENERAL")

    def test_list_filters_pagination_detail_update_close_and_followups(self):
        self.login()
        first = self.create(persona="ana", fecha="2026-09-10", estado_caso="ABIERTO", responsable="Rosa", resultado="Primer riesgo")
        second = self.create(persona="beto", fecha="2026-09-11", estado_caso="EN_SEGUIMIENTO", responsable="Luis", resultado="Segundo riesgo")
        self.assertEqual(self.client.get("/api/v1/riesgos-trabajo", params={"nombre": "Ana", "cedula": "0012345678", "area": "Operaciones", "estado": "ABIERTO", "responsable": "Rosa", "desde": "2026-09-01", "hasta": "2026-09-10"}).json()["total"], 1)
        page = self.client.get("/api/v1/riesgos-trabajo", params={"limite": 1, "offset": 1}).json()
        self.assertEqual(page["total"], 2)
        self.assertEqual(len(page["items"]), 1)
        self.assertNotIn("generic", {item["id_caso"] for item in self.client.get("/api/v1/riesgos-trabajo").json()["items"]})
        detail = self.client.get(f"/api/v1/riesgos-trabajo/{first['id_caso']}")
        self.assertEqual(detail.status_code, 200)
        changed = self.client.patch(f"/api/v1/riesgos-trabajo/{first['id_caso']}", json={"expected_version": first["version"], "estado_caso": "EN_SEGUIMIENTO", "resultado": "Actualizado"})
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(changed.json()["tipo_caso"], "RIESGOS_TRABAJO")
        self.assertEqual(self.client.patch(f"/api/v1/riesgos-trabajo/{first['id_caso']}", json={"expected_version": changed.json()["version"], "tipo_caso": "GENERAL"}).status_code, 422)
        self.assertEqual(self.client.patch("/api/v1/riesgos-trabajo/generic", json={"expected_version": 1, "estado_caso": "CERRADO"}).status_code, 404)
        seguimiento = self.client.post(f"/api/v1/riesgos-trabajo/{first['id_caso']}/seguimientos", json={"fecha": "2026-09-12", "descripcion": "Se contactó a la Persona", "proxima_accion": "Revisar"})
        self.assertEqual(seguimiento.status_code, 201)
        self.assertEqual(seguimiento.json()["creado_por"], "admin@example.com")
        self.assertEqual(len(self.client.get(f"/api/v1/riesgos-trabajo/{first['id_caso']}/seguimientos").json()), 1)
        self.assertEqual(self.client.post("/api/v1/riesgos-trabajo/generic/seguimientos", json={"fecha": "2026-09-12", "descripcion": "No debe entrar"}).status_code, 404)
        current = self.client.get(f"/api/v1/riesgos-trabajo/{first['id_caso']}").json()
        closed = self.client.post(f"/api/v1/riesgos-trabajo/{first['id_caso']}/cierres", json={"expected_version": current["version"], "fecha_cierre_caso": "2026-09-13", "responsable": "Rosa", "motivo_cierre": "Finalizado"})
        self.assertEqual(closed.status_code, 201)
        self.assertEqual(self.client.post("/api/v1/riesgos-trabajo/generic/cierres", json={"expected_version": 1, "motivo_cierre": "No"}).status_code, 404)
        self.assertTrue(self.client.get(f"/api/v1/riesgos-trabajo/{first['id_caso']}/historial").json())
        self.assertEqual(self.client.get(f"/api/v1/riesgos-trabajo/{second['id_caso']}").status_code, 200)

    def test_forms_destination_documents_mapping_and_migration_index(self):
        self.login()
        risk = self.create()
        with Session(self.engine) as session:
            self.assertEqual(session.get(Caso, risk["id_caso"]).tipo_caso, "RIESGOS_TRABAJO")
            from app.services.documentos import TIPO_REGISTRO_MODELOS
            self.assertEqual(TIPO_REGISTRO_MODELOS["CASOS"][0], Caso)
            self.assertTrue(session.get(type(session.get(Caso, risk["id_caso"])), risk["id_caso"]))
            from app.models import DestinoFormulario
            self.assertEqual(session.get(DestinoFormulario, "destino-riesgos-trabajo").codigo, "RIESGOS_TRABAJO")

    def test_contextual_forms_documents_commitments_and_generic_rejection(self):
        self.login()
        risk = self.create()
        with Session(self.engine) as session, session.begin():
            session.add_all([
                Formulario(id_formulario="form-risk", nombre="Formulario Riesgo", estado="PUBLICADO"),
                Formulario(id_formulario="form-accident", nombre="Solo Accidentes", estado="PUBLICADO"),
                Formulario(id_formulario="form-absence", nombre="Solo Ausentismos", estado="PUBLICADO"),
                FormularioDestino(id_destino="assign-risk", id_formulario="form-risk", modulo="RIESGOS_TRABAJO", id_destino_catalogo="destino-riesgos-trabajo"),
                FormularioDestino(id_destino="assign-accident", id_formulario="form-accident", modulo="ACCIDENTES", id_destino_catalogo="destino-accidentes"),
                FormularioDestino(id_destino="assign-absence", id_formulario="form-absence", modulo="AUSENTISMOS", id_destino_catalogo="destino-ausentismos"),
            ])
        forms = self.client.get(f"/api/v1/riesgos-trabajo/{risk['id_caso']}/formularios")
        self.assertEqual(forms.status_code, 200, forms.text)
        self.assertEqual([item["id_formulario"] for item in forms.json()], ["form-risk"])
        saved = self.client.post(f"/api/v1/riesgos-trabajo/{risk['id_caso']}/formularios/form-risk/respuestas", json={"borrador": True, "respuestas": [], "id_destino_respuesta": "destino-accidentes"})
        self.assertEqual(saved.status_code, 201, saved.text)
        self.assertEqual(saved.json()["id_destino_respuesta"], "destino-riesgos-trabajo")
        self.assertEqual(self.client.get("/api/v1/riesgos-trabajo/generic/formularios").status_code, 404)
        compromiso = self.client.post(f"/api/v1/riesgos-trabajo/{risk['id_caso']}/compromisos", json={"responsable": "Rosa", "descripcion": "Entregar informe", "fecha_limite": "2026-10-01", "estado": "PENDIENTE"})
        self.assertEqual(compromiso.status_code, 201, compromiso.text)
        self.assertEqual(compromiso.json()["responsable"], "Rosa")
        self.assertEqual(compromiso.json()["fecha_limite"], "2026-10-01")
        self.assertEqual(compromiso.json()["creado_por"], "admin@example.com")
        self.assertEqual(len(self.client.get(f"/api/v1/riesgos-trabajo/{risk['id_caso']}/compromisos").json()), 1)
        self.assertEqual(self.client.post("/api/v1/riesgos-trabajo/generic/compromisos", json={"descripcion": "No"}).status_code, 404)
        uploaded = self.client.post(f"/api/v1/riesgos-trabajo/{risk['id_caso']}/documentos", files={"archivo": ("evidencia.pdf", b"%PDF-1.4\\n", "application/pdf")})
        self.assertEqual(uploaded.status_code, 201, uploaded.text)
        documents = self.client.get(f"/api/v1/riesgos-trabajo/{risk['id_caso']}/documentos")
        self.assertEqual(documents.status_code, 200)
        self.assertEqual(documents.json()[0]["id_registro"], risk["id_caso"])
        self.assertEqual(self.client.get(f"/api/v1/riesgos-trabajo/{risk['id_caso']}/documentos/{uploaded.json()['id_archivo']}/contenido").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/riesgos-trabajo/generic/documentos").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/riesgos-trabajo/generic/historial").status_code, 404)


class RiesgosTrabajoMigrationTests(unittest.TestCase):
    def test_index_upgrade_downgrade_and_final_upgrade(self):
        with TemporaryDirectory() as directory:
            engine = build_engine(f"sqlite:///{directory}/migration.db")
            original = db_session.engine
            db_session.engine = engine
            try:
                config = Config("alembic.ini")
                command.upgrade(config, "0019_destinos_jerarquicos_formularios")
                command.upgrade(config, "head")
                self.assertIn("ix_casos_tipo_estado_fecha_apertura", {row["name"] for row in inspect(engine).get_indexes("casos")})
                command.downgrade(config, "0019_destinos_jerarquicos_formularios")
                self.assertNotIn("ix_casos_tipo_estado_fecha_apertura", {row["name"] for row in inspect(engine).get_indexes("casos")})
                command.upgrade(config, "head")
                self.assertIn("ix_casos_tipo_estado_fecha_apertura", {row["name"] for row in inspect(engine).get_indexes("casos")})
            finally:
                db_session.engine = original
                engine.dispose()


if __name__ == "__main__":
    unittest.main()
