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
from app.models import Atencion, Formulario, FormularioDestino, Novedad, Permission, Persona, Recorrido, Role, User
from app.services.form_destinations import seed_form_destinations
from app.services.security_seed import seed_security


class ProduccionApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(); self.engine = build_engine(f"sqlite:///{self.temp.name}/production.db")
        self.original = db_session.engine; db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")
        with Session(self.engine) as session, session.begin():
            seed_security(session)
            seed_form_destinations(session)
            session.add_all([Role(id_rol="ROLE_PROD", nombre="Producción", descripcion="Solo Producción"),
                             User(id_usuario="prod", correo="prod@example.com", nombre="Operador", rol_id="ROLE_PROD", estado="ACTIVO"),
                             Persona(id_persona="persona", nombre="Ana Producción", cedula="0012345678", area="Planta")])
            session.flush()
            for module, rights in {"PRODUCCION": {"puede_crear": True, "puede_leer": True, "puede_editar": True, "puede_eliminar": True}, "FORMULARIOS": {"puede_leer": True}, "RESPUESTAS": {"puede_crear": True, "puede_leer": True}, "DOCUMENTOS": {"puede_crear": True, "puede_leer": True, "puede_editar": True, "puede_eliminar": True}, "AUDITORIA": {"puede_leer": True}}.items():
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

    def test_production_forms_force_real_destination_and_exclude_other_branches(self):
        self.login()
        attention = self.client.post("/api/v1/produccion/atenciones", json={"fecha": "2026-09-10", "motivo": "Formulario", "estado": "ABIERTO"}).json()
        with Session(self.engine) as session, session.begin():
            session.add_all([
                Formulario(id_formulario="form-attention", nombre="Atención", estado="PUBLICADO"),
                Formulario(id_formulario="form-round", nombre="Recorrido", estado="PUBLICADO"),
                FormularioDestino(id_destino="assign-attention", id_formulario="form-attention", modulo="PRODUCCION_ATENCIONES", id_destino_catalogo="destino-produccion-atenciones"),
                FormularioDestino(id_destino="assign-round", id_formulario="form-round", modulo="RECORRIDOS", id_destino_catalogo="destino-recorridos"),
            ])
        url = f"/api/v1/produccion/atenciones/{attention['id_atencion']}/formularios"
        forms = self.client.get(url)
        self.assertEqual(forms.status_code, 200, forms.text)
        self.assertEqual([item["id_formulario"] for item in forms.json()], ["form-attention"])
        saved = self.client.post(f"{url}/form-attention/respuestas", json={"borrador": True, "respuestas": [], "id_destino_respuesta": "destino-recorridos", "contexto_tipo": "RECORRIDOS"})
        self.assertEqual(saved.status_code, 201, saved.text)
        self.assertEqual(saved.json()["contexto_tipo"], "ATENCIONES")
        self.assertEqual(saved.json()["contexto_id"], attention["id_atencion"])
        self.assertEqual(saved.json()["id_destino_respuesta"], "destino-produccion-atenciones")

    def test_recorridos_novedades_and_multidestination_keep_concrete_response_destination(self):
        self.login()
        recorrido = self.client.post("/api/v1/produccion/recorridos", json={"fecha": "2026-09-10", "objetivo": "Formulario"}).json()
        novedad = self.client.post("/api/v1/produccion/novedades", json={"fecha": "2026-09-10", "descripcion": "Formulario", "estado": "ABIERTO"}).json()
        with Session(self.engine) as session, session.begin():
            session.add_all([
                Formulario(id_formulario="form-multi", nombre="Multidestino", estado="PUBLICADO"),
                Formulario(id_formulario="form-other", nombre="Otra rama", estado="PUBLICADO"),
                FormularioDestino(id_destino="multi-round", id_formulario="form-multi", modulo="RECORRIDOS", id_destino_catalogo="destino-recorridos"),
                FormularioDestino(id_destino="multi-news", id_formulario="form-multi", modulo="NOVEDADES_PLANTA", id_destino_catalogo="destino-novedades-planta"),
                FormularioDestino(id_destino="other-attention", id_formulario="form-other", modulo="PRODUCCION_ATENCIONES", id_destino_catalogo="destino-produccion-atenciones"),
            ])
        for kind, record_id, destination in (("recorridos", recorrido["id_recorrido"], "destino-recorridos"), ("novedades", novedad["id_novedad"], "destino-novedades-planta")):
            base = f"/api/v1/produccion/{kind}/{record_id}/formularios"
            listed = self.client.get(base); self.assertEqual(listed.status_code, 200, listed.text)
            self.assertEqual([item["id_formulario"] for item in listed.json()], ["form-multi"])
            saved = self.client.post(f"{base}/form-multi/respuestas", json={"borrador": True, "respuestas": [], "id_destino_respuesta": "destino-produccion-atenciones"})
            self.assertEqual(saved.status_code, 201, saved.text); self.assertEqual(saved.json()["id_destino_respuesta"], destination)

    def test_production_document_wrappers_validate_scope_and_permissions(self):
        self.login()
        attention = self.client.post("/api/v1/produccion/atenciones", json={"fecha": "2026-09-10", "motivo": "Documento", "estado": "ABIERTO"}).json()
        base = f"/api/v1/produccion/atenciones/{attention['id_atencion']}/documentos"
        uploaded = self.client.post(base, files={"archivo": ("evidencia.pdf", b"%PDF-1.4\n", "application/pdf")})
        self.assertEqual(uploaded.status_code, 201, uploaded.text)
        self.assertEqual(self.client.get(base).json()[0]["id_registro"], attention["id_atencion"])
        self.assertEqual(self.client.get("/api/v1/produccion/atenciones/historic/documentos").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/produccion/atenciones/office/documentos").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/produccion/atenciones/missing/documentos").status_code, 404)
        with Session(self.engine) as session, session.begin(): session.get(Permission, "prod-DOCUMENTOS").puede_leer = False
        self.assertEqual(self.client.get(base).status_code, 403)
        with Session(self.engine) as session, session.begin():
            session.get(Permission, "prod-DOCUMENTOS").puede_leer = True; session.get(Permission, "prod-PRODUCCION").puede_leer = False
        self.assertEqual(self.client.get(base).status_code, 403)

    def test_recorridos_and_novedades_document_wrappers_validate_record_scope(self):
        self.login()
        recorrido = self.client.post("/api/v1/produccion/recorridos", json={"fecha": "2026-09-10", "objetivo": "Documento"}).json()
        novedad = self.client.post("/api/v1/produccion/novedades", json={"fecha": "2026-09-10", "descripcion": "Documento", "estado": "ABIERTO"}).json()
        for kind, record_id in (("recorridos", recorrido["id_recorrido"]), ("novedades", novedad["id_novedad"])):
            base = f"/api/v1/produccion/{kind}/{record_id}/documentos"
            self.assertEqual(self.client.post(base, files={"archivo": ("evidencia.pdf", b"%PDF-1.4\n", "application/pdf")}).status_code, 201)
            self.assertEqual(self.client.get(base).status_code, 200)
            self.assertEqual(self.client.get(f"/api/v1/produccion/{kind}/missing/documentos").status_code, 404)


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
