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
from app.models import Auditoria, Caso, Catalogo, User
from app.services.passwords import hash_password, verify_password
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
        self.assertEqual(
            login.headers["permissions-policy"],
            "camera=(), microphone=(), geolocation=()",
        )

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

    def test_admin_updates_user_data_and_resets_password_without_exposing_credentials(self):
        old_password = "ClaveAnterior123"
        new_password = "ClaveNueva456"
        with Session(self.engine) as session, session.begin():
            self.assertEqual(session.get(User, "consulta").version, 1)
            session.get(User, "consulta").password_hash = hash_password(old_password)
        self.assertEqual(self.client.post(
            "/api/v1/auth/login", json={"correo": "admin@example.com", "password": "irrelevante"},
        ).status_code, 200)

        updated = self.client.patch("/api/v1/admin/usuarios/consulta", json={
            "nombre": " Consulta Actualizada ", "correo": " CONSULTA.NUEVA@EXAMPLE.COM ",
            "rol_id": "ROLE_CONSULTA", "estado": "ACTIVO", "expected_version": 1,
        })
        self.assertEqual(updated.status_code, 200)
        updated_body = updated.json()
        self.assertEqual(updated_body["nombre"], "Consulta Actualizada")
        self.assertEqual(updated_body["correo"], "consulta.nueva@example.com")
        self.assertEqual(updated_body["estado"], "ACTIVO")
        self.assertNotIn("password", updated_body)
        self.assertNotIn("password_hash", updated_body)

        reset = self.client.put("/api/v1/admin/usuarios/consulta/password", json={
            "password": new_password, "expected_version": updated_body["version"],
        })
        self.assertEqual(reset.status_code, 200)
        self.assertNotIn("password", reset.json())
        self.assertNotIn("password_hash", reset.json())

        with Session(self.engine) as session:
            usuario = session.get(User, "consulta")
            self.assertTrue(verify_password(new_password, usuario.password_hash))
            self.assertFalse(verify_password(old_password, usuario.password_hash))
            auditorias = session.query(Auditoria).filter_by(
                tabla="usuarios", id_registro="consulta", accion="UPDATE",
            ).all()
            self.assertTrue(auditorias)
            self.assertTrue(all(row.campo not in {"password", "password_hash"} for row in auditorias))
            self.assertNotIn(new_password, " ".join((row.valor_nuevo or "") for row in auditorias))
            self.assertNotIn(usuario.password_hash, " ".join((row.valor_nuevo or "") for row in auditorias))

        password_settings = SimpleNamespace(
            auth_mode="password", cookie_secure=False, cookie_samesite="lax", session_ttl_hours=12,
        )
        self.assertEqual(self.client.post("/api/v1/auth/logout").status_code, 200)
        with patch("app.api.auth.get_settings", return_value=password_settings):
            self.assertEqual(self.client.post(
                "/api/v1/auth/login", json={"correo": "consulta.nueva@example.com", "password": old_password},
            ).status_code, 401)
            self.assertEqual(self.client.post(
                "/api/v1/auth/login", json={"correo": "consulta.nueva@example.com", "password": new_password},
            ).status_code, 200)

    def test_admin_user_update_and_password_reset_enforce_validation_and_edit_permission(self):
        self.assertEqual(self.client.post(
            "/api/v1/auth/login", json={"correo": "admin@example.com", "password": "irrelevante"},
        ).status_code, 200)
        invalid_email = self.client.patch("/api/v1/admin/usuarios/consulta", json={
            "nombre": "Consulta", "correo": "inválido", "rol_id": "ROLE_CONSULTA", "estado": "ACTIVO", "expected_version": 1,
        })
        self.assertEqual(invalid_email.status_code, 422)
        self.assertEqual(invalid_email.json()["code"], "INVALID_EMAIL")
        weak_password = self.client.put("/api/v1/admin/usuarios/consulta/password", json={
            "password": "débil", "expected_version": 1,
        })
        self.assertEqual(weak_password.status_code, 422)
        self.assertEqual(weak_password.json()["code"], "WEAK_PASSWORD")
        stale_version = self.client.put("/api/v1/admin/usuarios/consulta/password", json={
            "password": "ClaveNueva456", "expected_version": 99,
        })
        self.assertEqual(stale_version.status_code, 409)
        self.assertEqual(stale_version.json()["code"], "VERSION_CONFLICT")

        self.assertEqual(self.client.post("/api/v1/auth/logout").status_code, 200)
        self.assertEqual(self.client.post(
            "/api/v1/auth/login", json={"correo": "consulta@example.com", "password": "irrelevante"},
        ).status_code, 200)
        forbidden = self.client.put("/api/v1/admin/usuarios/admin/password", json={
            "password": "ClaveNueva456", "expected_version": 1,
        })
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(forbidden.json()["code"], "FORBIDDEN")

    def test_admin_soft_deletes_and_restores_user_without_exposing_secrets(self):
        target_client = TestClient(app)
        password_plana = "ClaveTemporalEliminacion123"
        try:
            with Session(self.engine) as session, session.begin():
                session.get(User, "consulta").password_hash = hash_password(password_plana)
            self.assertEqual(target_client.post(
                "/api/v1/auth/login", json={"correo": "consulta@example.com", "password": password_plana},
            ).status_code, 200)
            token_sesion = target_client.cookies.get("sits_session")
            self.assertEqual(self.client.post(
                "/api/v1/auth/login", json={"correo": "admin@example.com", "password": "irrelevante"},
            ).status_code, 200)

            deleted = self.client.post("/api/v1/admin/usuarios/consulta/eliminacion", json={
                "expected_version": 1, "motivo": "Salida de la compañía",
            })
            self.assertEqual(deleted.status_code, 200)
            self.assertTrue(deleted.json()["eliminado"])
            self.assertFalse(deleted.json()["activo"])
            self.assertNotIn("password", deleted.json())
            self.assertNotIn("password_hash", deleted.json())
            self.assertEqual(target_client.get("/api/v1/auth/me").status_code, 401)
            self.assertEqual(target_client.post(
                "/api/v1/auth/login", json={"correo": "consulta@example.com", "password": password_plana},
            ).status_code, 403)

            normal_list = self.client.get("/api/v1/admin/usuarios")
            self.assertEqual(normal_list.status_code, 200)
            self.assertNotIn("consulta", {item["id_usuario"] for item in normal_list.json()["usuarios"]})
            deleted_list = self.client.get("/api/v1/admin/usuarios?incluir_eliminados=true")
            self.assertEqual(deleted_list.status_code, 200)
            self.assertIn("consulta", {item["id_usuario"] for item in deleted_list.json()["usuarios"]})
            self.assertTrue(deleted_list.json()["puede_eliminar_usuarios"])

            repeated = self.client.post("/api/v1/admin/usuarios/consulta/eliminacion", json={
                "expected_version": 2, "motivo": "Reintento",
            })
            self.assertEqual(repeated.status_code, 409)
            self.assertEqual(repeated.json()["code"], "USER_ALREADY_DELETED")
            restored = self.client.post("/api/v1/admin/usuarios/consulta/restauracion", json={"expected_version": 2})
            self.assertEqual(restored.status_code, 200)
            self.assertFalse(restored.json()["eliminado"])
            self.assertTrue(restored.json()["activo"])
            self.assertEqual(target_client.get("/api/v1/auth/me").status_code, 401)
            self.assertEqual(target_client.post(
                "/api/v1/auth/login", json={"correo": "consulta@example.com", "password": password_plana},
            ).status_code, 200)

            with Session(self.engine) as session:
                usuario = session.get(User, "consulta")
                auditorias = session.query(Auditoria).filter_by(tabla="usuarios", id_registro="consulta").all()
                self.assertIsNotNone(usuario)
                self.assertFalse(usuario.eliminado)
                self.assertIsNone(usuario.motivo_eliminacion)
                self.assertEqual({row.accion for row in auditorias}, {"DELETE", "RESTORE"})
                self.assertTrue(all(row.campo in {"id_usuario", "correo", "nombre", "rol_id", "estado", "activo", "eliminado", "version"} for row in auditorias))
                audit_text = " ".join((row.valor_nuevo or "") for row in auditorias)
                self.assertNotIn(password_plana, audit_text)
                self.assertNotIn("password_hash", audit_text)
                if usuario.password_hash:
                    self.assertNotIn(usuario.password_hash, audit_text)
                if token_sesion:
                    self.assertNotIn(token_sesion, audit_text)

            self.assertEqual(self.client.post("/api/v1/auth/logout").status_code, 200)
            self.assertEqual(self.client.post(
                "/api/v1/auth/login", json={"correo": "consulta@example.com", "password": password_plana},
            ).status_code, 200)
            forbidden = self.client.post("/api/v1/admin/usuarios/admin/eliminacion", json={
                "expected_version": 1, "motivo": "Sin permiso",
            })
            self.assertEqual(forbidden.status_code, 403)
            self.assertEqual(forbidden.json()["code"], "FORBIDDEN")
            self.assertEqual(self.client.get("/api/v1/admin/usuarios?incluir_eliminados=true").status_code, 403)
        finally:
            target_client.close()

    def test_sensitive_cases_are_not_exposed_in_lists_or_autocomplete(self):
        with Session(self.engine) as session, session.begin():
            session.add(Catalogo(
                id_catalogo="sensitive-high", tipo="NIVEL_SENSIBILIDAD", codigo="ALTA",
                valor="Alta", es_sensible=True,
            ))
            session.add(Caso(
                id_caso="sensitive-case", codigo_caso="CAS-SECRET-1", colaborador="Persona reservada",
                nivel_sensibilidad="ALTA", estado_caso="ABIERTO",
            ))
            session.add(Caso(
                id_caso="standard-case", codigo_caso="CAS-PUBLIC-1", colaborador="Persona visible",
                nivel_sensibilidad="NORMAL", estado_caso="ABIERTO",
            ))

        self.assertEqual(self.client.post(
            "/api/v1/auth/login", json={"correo": "consulta@example.com", "password": "irrelevante"},
        ).status_code, 200)
        listed = self.client.get("/api/v1/casos")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual({item["id_caso"] for item in listed.json()}, {"standard-case"})

        autocomplete = self.client.get(
            "/api/v1/formularios/search-options",
            params={"source": "CASOS", "q": "CAS-", "browse": "true"},
        )
        self.assertEqual(autocomplete.status_code, 200)
        self.assertEqual({item["id"] for item in autocomplete.json()}, {"standard-case"})
        self.assertEqual(self.client.get("/api/v1/casos/sensitive-case").status_code, 403)

    def test_listing_deleted_records_requires_delete_permission(self):
        with Session(self.engine) as session, session.begin():
            session.add(Caso(
                id_caso="deleted-case", codigo_caso="CAS-DELETED-1", eliminado=True,
                activo=False, motivo_eliminacion="Registro descartado",
            ))
        self.assertEqual(self.client.post(
            "/api/v1/auth/login", json={"correo": "consulta@example.com", "password": "irrelevante"},
        ).status_code, 200)
        response = self.client.get("/api/v1/casos?incluir_eliminados=true")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "FORBIDDEN")

    def test_admin_payloads_reject_ambiguous_permission_values_and_missing_fields(self):
        self.assertEqual(self.client.post(
            "/api/v1/auth/login", json={"correo": "admin@example.com", "password": "irrelevante"},
        ).status_code, 200)
        administration = self.client.get("/api/v1/admin/usuarios").json()
        permission = next(item for item in administration["permisos"]
                          if item["rol_id"] == "ROLE_CONSULTA" and item["modulo"] == "CASOS")

        invalid_permission = self.client.put(
            "/api/v1/admin/roles/ROLE_CONSULTA/permisos/CASOS",
            json={"derechos": {"read": "false"}, "expected_version": permission["version"]},
        )
        self.assertEqual(invalid_permission.status_code, 422)
        self.assertEqual(invalid_permission.json()["code"], "INVALID_INPUT")

        missing_role = self.client.patch("/api/v1/admin/usuarios/consulta", json={
            "estado": "ACTIVO", "expected_version": 1,
        })
        self.assertEqual(missing_role.status_code, 422)
        self.assertEqual(missing_role.json()["code"], "INVALID_INPUT")

        ambiguous_draft = self.client.post("/api/v1/formularios/missing/respuestas", json={
            "borrador": "false", "respuestas": [],
        })
        self.assertEqual(ambiguous_draft.status_code, 422)
        self.assertEqual(ambiguous_draft.json()["code"], "INVALID_INPUT")

        invalid_page_size = self.client.get("/api/v1/busqueda?tamano_pagina=0")
        self.assertEqual(invalid_page_size.status_code, 422)
        self.assertEqual(invalid_page_size.json()["code"], "INVALID_INPUT")


if __name__ == "__main__":
    unittest.main()
