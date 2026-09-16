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
from app.models import Atencion, Beneficio, EnvioFormulario, Formulario, FormularioDestino, Permission, Persona, Prestamo, Role, Seguro, User
from app.services.form_destinations import seed_form_destinations
from app.services.security_seed import seed_security


class OficinaAtencionesApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(); self.engine = build_engine(f"sqlite:///{self.temp.name}/office.db")
        self.original = db_session.engine; db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")
        with Session(self.engine) as session, session.begin():
            seed_security(session)
            seed_form_destinations(session)
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
            session.add_all([
                Permission(id_permiso="office-FORMULARIOS", rol_id="ROLE_OFFICE", modulo="FORMULARIOS", puede_leer=True),
                Permission(id_permiso="office-RESPUESTAS", rol_id="ROLE_OFFICE", modulo="RESPUESTAS", puede_crear=True, puede_leer=True),
                Permission(id_permiso="office-DOCUMENTOS", rol_id="ROLE_OFFICE", modulo="DOCUMENTOS", puede_crear=True, puede_leer=True, puede_editar=True, puede_eliminar=True),
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

    def test_forms_are_isolated_by_office_leaf_and_multidestination_keeps_real_destination(self):
        self.login()
        attention = self.client.post("/api/v1/oficina/atenciones", json={"fecha": "2026-09-10", "motivo": "Form", "estado": "ABIERTO"}).json()
        benefit = self.client.post("/api/v1/oficina/beneficios", json={"tipo_beneficio": "TIA", "tipo_gestion": "ACTIVACION"}).json()
        loan = self.client.post("/api/v1/oficina/prestamos", json={"tipo": "PRESTAMO"}).json()
        insurance = self.client.post("/api/v1/oficina/seguro", json={"tipo_gestion": "DEPENDIENTE"}).json()
        with Session(self.engine) as session, session.begin():
            session.add_all([
                Formulario(id_formulario="benefit-only", nombre="Beneficio", estado="PUBLICADO"),
                Formulario(id_formulario="attention-only", nombre="Atención", estado="PUBLICADO"),
                Formulario(id_formulario="loan-only", nombre="Préstamo", estado="PUBLICADO"),
                Formulario(id_formulario="insurance-only", nombre="Seguro", estado="PUBLICADO"),
                Formulario(id_formulario="shared", nombre="Compartido", estado="PUBLICADO"),
                Formulario(id_formulario="production", nombre="Producción", estado="PUBLICADO"),
                FormularioDestino(id_destino="benefit-only-assignment", id_formulario="benefit-only", modulo="BENEFICIOS", id_destino_catalogo="destino-beneficios"),
                FormularioDestino(id_destino="attention-only-assignment", id_formulario="attention-only", modulo="OFICINA_ATENCIONES", id_destino_catalogo="destino-oficina-atenciones"),
                FormularioDestino(id_destino="loan-only-assignment", id_formulario="loan-only", modulo="PRESTAMOS", id_destino_catalogo="destino-prestamos"),
                FormularioDestino(id_destino="insurance-only-assignment", id_formulario="insurance-only", modulo="SEGURO", id_destino_catalogo="destino-seguro"),
                FormularioDestino(id_destino="shared-benefit", id_formulario="shared", modulo="BENEFICIOS", id_destino_catalogo="destino-beneficios"),
                FormularioDestino(id_destino="shared-insurance", id_formulario="shared", modulo="SEGURO", id_destino_catalogo="destino-seguro"),
                FormularioDestino(id_destino="production-assignment", id_formulario="production", modulo="PRODUCCION_ATENCIONES", id_destino_catalogo="destino-produccion-atenciones"),
            ])
        records = (("atenciones", attention["id_atencion"], ["attention-only"]), ("beneficios", benefit["id_beneficio"], ["benefit-only", "shared"]), ("prestamos", loan["id_prestamo"], ["loan-only"]), ("seguro", insurance["id_seguro"], ["insurance-only", "shared"]))
        before = self.client.get("/api/v1/oficina/beneficios").json()["total"]
        for kind, record_id, expected in records:
            base = f"/api/v1/oficina/{kind}/{record_id}/formularios"
            forms = self.client.get(base)
            self.assertEqual(forms.status_code, 200, forms.text)
            self.assertEqual(sorted(item["id_formulario"] for item in forms.json()), expected)
        saved = self.client.post(f"/api/v1/oficina/beneficios/{benefit['id_beneficio']}/formularios/shared/respuestas", json={"borrador": True, "respuestas": [], "id_destino_respuesta": "destino-seguro", "contexto_tipo": "SEGUROS"})
        self.assertEqual(saved.status_code, 201, saved.text)
        self.assertEqual((saved.json()["contexto_tipo"], saved.json()["contexto_id"], saved.json()["id_destino_respuesta"]), ("BENEFICIOS", benefit["id_beneficio"], "destino-beneficios"))
        self.assertEqual(self.client.get("/api/v1/oficina/beneficios").json()["total"], before)
        with Session(self.engine) as session:
            self.assertEqual(session.query(EnvioFormulario).filter_by(id_destino_respuesta="destino-beneficios").count(), 1)

    def test_document_wrappers_validate_office_records_and_permissions(self):
        self.login()
        attention = self.client.post("/api/v1/oficina/atenciones", json={"fecha": "2026-09-10", "motivo": "Documento", "estado": "ABIERTO"}).json()
        benefit = self.client.post("/api/v1/oficina/beneficios", json={"tipo_beneficio": "FARMACIA", "tipo_gestion": "BLOQUEO"}).json()
        loan = self.client.post("/api/v1/oficina/prestamos", json={"tipo": "ANTICIPO"}).json()
        insurance = self.client.post("/api/v1/oficina/seguro", json={"tipo_gestion": "PRIMA"}).json()
        for kind, record_id in (("atenciones", attention["id_atencion"]), ("beneficios", benefit["id_beneficio"]), ("prestamos", loan["id_prestamo"]), ("seguro", insurance["id_seguro"])):
            base = f"/api/v1/oficina/{kind}/{record_id}/documentos"
            self.assertEqual(self.client.post(base, files={"archivo": ("evidencia.pdf", b"%PDF-1.4\n", "application/pdf")}).status_code, 201)
            self.assertEqual(self.client.get(base).status_code, 200)
            self.assertEqual(self.client.get(f"/api/v1/oficina/{kind}/missing/documentos").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/oficina/atenciones/production/documentos").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/oficina/atenciones/historic/documentos").status_code, 404)
        with Session(self.engine) as session, session.begin():
            session.get(Permission, "office-DOCUMENTOS").puede_leer = False
        self.assertEqual(self.client.get(f"/api/v1/oficina/beneficios/{benefit['id_beneficio']}/documentos").status_code, 403)
        with Session(self.engine) as session, session.begin():
            session.get(Permission, "office-DOCUMENTOS").puede_leer = True
            session.get(Permission, "office-OFICINA").puede_leer = False
        self.assertEqual(self.client.get(f"/api/v1/oficina/beneficios/{benefit['id_beneficio']}/documentos").status_code, 403)


if __name__ == "__main__":
    unittest.main()
