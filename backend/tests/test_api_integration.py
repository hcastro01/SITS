"""Recorrido HTTP de los flujos críticos con una base temporal aislada."""

import unittest
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_db
import app.db.session as db_session
from app.db.session import build_engine
from app.main import app
from app.models import Auditoria, User
from app.services.passwords import verify_password
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
            session.add(User(id_usuario="consulta", correo="consulta@example.com", nombre="Consulta",
                             rol_id="ROLE_CONSULTA", estado="ACTIVO"))

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

    def test_admin_can_create_a_user_that_can_authenticate(self):
        self.assertEqual(self.client.post(
            "/api/v1/auth/login", json={"correo": "admin@example.com", "password": "ClaveSegura123"},
        ).status_code, 200)
        password = "TemporalSegura123"
        response = self.client.post("/api/v1/admin/usuarios", json={
            "correo": " NUEVA@Example.COM ", "nombre": " Nueva Persona ",
            "rol_id": "ROLE_TRABAJADOR_SOCIAL", "password": password,
        })
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["correo"], "nueva@example.com")
        self.assertNotIn("password", body)
        self.assertNotIn("password_hash", body)

        with Session(self.engine) as session:
            usuario = session.get(User, body["id_usuario"])
            self.assertIsNotNone(usuario)
            self.assertNotEqual(usuario.password_hash, password)
            self.assertTrue(verify_password(password, usuario.password_hash))
            auditorias = session.query(Auditoria).filter_by(
                tabla="usuarios", id_registro=body["id_usuario"], accion="CREATE",
            ).all()
            self.assertTrue(auditorias)
            self.assertTrue(all(row.campo not in {"password", "password_hash"} for row in auditorias))

        password_settings = SimpleNamespace(
            auth_mode="password", cookie_secure=False, cookie_samesite="lax", session_ttl_hours=12,
        )
        with patch("app.api.auth.get_settings", return_value=password_settings):
            login = self.client.post("/api/v1/auth/login", json={
                "correo": "nueva@example.com", "password": password,
            })
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.json()["id_usuario"], body["id_usuario"])

    def test_user_without_create_permission_receives_403(self):
        self.assertEqual(self.client.post(
            "/api/v1/auth/login", json={"correo": "consulta@example.com", "password": "irrelevante"},
        ).status_code, 200)
        response = self.client.post("/api/v1/admin/usuarios", json={
            "correo": "otra@example.com", "nombre": "Otra Persona",
            "rol_id": "ROLE_CONSULTA", "password": "TemporalSegura123",
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "FORBIDDEN")

    def test_form_delete_endpoint_exposes_permission_and_enforces_rbac(self):
        self.assertEqual(self.client.post(
            "/api/v1/auth/login", json={"correo": "admin@example.com", "password": "irrelevante"},
        ).status_code, 200)
        created_response = self.client.post("/api/v1/formularios", json={
            "nombre": "Formulario eliminable", "destinos": ["GENERAL"],
            "motivo_auditoria": "Prueba de eliminación",
        })
        self.assertEqual(created_response.status_code, 201)
        created = created_response.json()
        self.assertTrue(created["acciones"]["eliminar"])
        form_id = created["id_formulario"]

        listed = self.client.get("/api/v1/formularios")
        self.assertEqual(listed.status_code, 200)
        self.assertTrue(next(item for item in listed.json() if item["id_formulario"] == form_id)["acciones"]["eliminar"])

        self.assertEqual(self.client.post("/api/v1/auth/logout").status_code, 200)
        self.assertEqual(self.client.post(
            "/api/v1/auth/login", json={"correo": "consulta@example.com", "password": "irrelevante"},
        ).status_code, 200)
        consulta_list = self.client.get("/api/v1/formularios")
        self.assertEqual(consulta_list.status_code, 200)
        self.assertFalse(next(item for item in consulta_list.json() if item["id_formulario"] == form_id)["acciones"]["eliminar"])
        forbidden = self.client.post(f"/api/v1/formularios/{form_id}/eliminacion", json={
            "expected_version": created["version"], "motivo": "No autorizado",
        })
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(forbidden.json()["code"], "FORBIDDEN")

        self.assertEqual(self.client.post("/api/v1/auth/logout").status_code, 200)
        self.assertEqual(self.client.post(
            "/api/v1/auth/login", json={"correo": "admin@example.com", "password": "irrelevante"},
        ).status_code, 200)
        deleted = self.client.post(f"/api/v1/formularios/{form_id}/eliminacion", json={
            "expected_version": created["version"], "motivo": "Formulario descartado",
        })
        self.assertEqual(deleted.status_code, 200)
        self.assertTrue(deleted.json()["eliminado"])
        self.assertNotIn(form_id, {item["id_formulario"] for item in self.client.get("/api/v1/formularios").json()})

    def test_admin_user_creation_returns_expected_validation_errors(self):
        self.client.post("/api/v1/auth/login", json={"correo": "admin@example.com", "password": "irrelevante"})
        cases = (
            ({"correo": "ADMIN@example.com", "nombre": "Duplicado", "rol_id": "ROLE_CONSULTA",
              "password": "TemporalSegura123"}, 409, "USER_ALREADY_EXISTS"),
            ({"correo": "otra@example.com", "nombre": "Otra", "rol_id": "ROLE_INEXISTENTE",
              "password": "TemporalSegura123"}, 422, "ROLE_NOT_FOUND"),
            ({"correo": "otra@example.com", "nombre": "Otra", "rol_id": "ROLE_CONSULTA",
              "password": "debil"}, 422, "WEAK_PASSWORD"),
        )
        for payload, status_code, code in cases:
            with self.subTest(code=code):
                response = self.client.post("/api/v1/admin/usuarios", json=payload)
                self.assertEqual(response.status_code, status_code)
                self.assertEqual(response.json()["code"], code)


if __name__ == "__main__":
    unittest.main()
