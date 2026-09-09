import json
import unittest
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, resolve_current_user
from app.db.session import build_engine
from app.models import Auditoria, Caso, Catalogo, EnvioFormulario, FormularioVersion, Persona, User
from app.services.dynamic_responses import soft_delete_dynamic_response
from app.services.form_builder import duplicate_form, get_definition, save_definition
from app.services.form_integrations import (
    list_available_forms, list_module_responses, person_records, response_by_code,
)
from app.services.form_search import list_sources, search_options
from app.services.formularios import change_status, create_formulario, soft_delete_formulario
from app.services.preguntas import preguntas
from app.services.respuestas_formulario import save_response
from app.services.security_seed import seed_security


class FormModuleIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.engine = build_engine(f"sqlite:///{self.directory.name}/integration.db")
        self.original_engine = db_session.engine
        db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")
        with Session(self.engine) as session, session.begin():
            seed_security(session)
            session.add_all([
                User(id_usuario="admin", correo="admin@example.com", nombre="Admin", rol_id="ROLE_ADMIN", estado="ACTIVO"),
                User(id_usuario="ts", correo="ts@example.com", nombre="TS", rol_id="ROLE_TRABAJADOR_SOCIAL", estado="ACTIVO"),
                Persona(id_persona="ana", nombre="Ana López García", cedula="0101",
                        codigo_empleado="EMP-01", area="CONTROL DE CALIDAD", centro="CC-01 PLANTA"),
                Persona(id_persona="beto", nombre="Beto Pérez", cedula="0202",
                        codigo_empleado="EMP-02", area="GESTIÓN DE CALIDAD", centro="CC-02 OFICINAS"),
            ])

    def tearDown(self):
        db_session.engine = self.original_engine
        self.engine.dispose()
        self.directory.cleanup()

    def _form(self, session, name, destinations, *, publish=True, active=True, multiple=False):
        admin = resolve_current_user(session, "admin@example.com")
        form = create_formulario(
            session, admin, motivo_auditoria="Alta", correlation_id=name,
            nombre=name, destinos=destinations, permite_multiples_respuestas=multiple,
        )
        question = preguntas.create(
            session, admin, motivo_auditoria="Pregunta", correlation_id=name,
            id_formulario=form.id_formulario, etiqueta="Detalle",
        )
        if publish:
            change_status(session, admin, form.id_formulario, "PUBLICADO",
                          expected_version=form.version, correlation_id=name)
        if not active:
            form.activo = False
        return form, question

    @staticmethod
    def _answer(question, value="OK"):
        return [{"id_pregunta": question.id_pregunta, "valor_texto": value}]

    def test_selector_filters_destination_publication_and_activity_and_supports_multiple_destinations(self):
        """Cubre selección 1-6: destino exacto, multi-destino, borrador e inactivo."""
        with Session(self.engine) as session, session.begin():
            case, _ = self._form(session, "Solo casos", ["CASOS"])
            shared, _ = self._form(session, "Compartido", ["CASOS", "ATENCIONES"])
            self._form(session, "Borrador", ["CASOS"], publish=False)
            self._form(session, "Inactivo", ["CASOS"], active=False)
            admin = resolve_current_user(session, "admin@example.com")
            cases = {item["id_formulario"] for item in list_available_forms(session, admin, "CASOS")}
            attentions = {item["id_formulario"] for item in list_available_forms(session, admin, "ATENCIONES")}
            self.assertEqual(cases, {case.id_formulario, shared.id_formulario})
            self.assertEqual(attentions, {shared.id_formulario})

    def test_deleted_form_does_not_reappear_in_module_selector(self):
        with Session(self.engine) as session, session.begin():
            form, _ = self._form(session, "Para retirar", ["CASOS"])
            admin = resolve_current_user(session, "admin@example.com")
            self.assertIn(
                form.id_formulario,
                {item["id_formulario"] for item in list_available_forms(session, admin, "CASOS")},
            )
            unpublished = change_status(
                session, admin, form.id_formulario, "INACTIVO",
                expected_version=form.version, correlation_id="unpublish",
            )
            soft_delete_formulario(
                session, admin, form.id_formulario, expected_version=unpublished.version,
                motivo="Retiro definitivo", correlation_id="delete",
            )
            self.assertNotIn(
                form.id_formulario,
                {item["id_formulario"] for item in list_available_forms(session, admin, "CASOS")},
            )

    def test_draft_final_global_sequence_multiple_submissions_and_idempotency(self):
        """Cubre 7-14 y 31-32: renderer payload, borradores, secuencia global y reintento."""
        with Session(self.engine) as session, session.begin():
            form, question = self._form(session, "Multi", ["CASOS", "ATENCIONES"], multiple=True)
            admin = resolve_current_user(session, "admin@example.com")
            draft = save_response(
                session, admin, form.id_formulario, draft=True, respuestas=self._answer(question, "borrador"),
                contexto_tipo="CASOS", crear_contexto=True, id_persona="ana",
                id_envio_cliente="draft", correlation_id="draft",
            )
            self.assertIsNone(draft.codigo_respuesta)
            draft = save_response(
                session, admin, form.id_formulario, draft=True, respuestas=self._answer(question, "borrador 2"),
                id_respuesta=draft.id_respuesta, expected_version=draft.version,
                contexto_tipo="CASOS", contexto_id=draft.contexto_id,
                id_envio_cliente="draft", correlation_id="draft2",
            )
            self.assertIsNone(draft.numero_secuencial)
            first = save_response(
                session, admin, form.id_formulario, draft=False, respuestas=self._answer(question, "final"),
                id_respuesta=draft.id_respuesta, expected_version=draft.version,
                contexto_tipo="CASOS", contexto_id=draft.contexto_id,
                id_envio_cliente="draft", correlation_id="final",
            )
            second = save_response(
                session, admin, form.id_formulario, draft=False, respuestas=self._answer(question, "atención"),
                contexto_tipo="ATENCIONES", crear_contexto=True, id_persona="ana",
                id_envio_cliente="attention", correlation_id="attention",
            )
            third = save_response(
                session, admin, form.id_formulario, draft=False, respuestas=self._answer(question, "otro"),
                contexto_tipo="CASOS", crear_contexto=True, id_persona="ana",
                id_envio_cliente="other", correlation_id="other",
            )
            retry = save_response(
                session, admin, form.id_formulario, draft=False, respuestas=self._answer(question, "ignorado"),
                contexto_tipo="CASOS", crear_contexto=True, id_persona="ana",
                id_envio_cliente="draft", correlation_id="retry",
            )
            self.assertEqual([first.numero_secuencial, second.numero_secuencial, third.numero_secuencial], [1, 2, 3])
            self.assertEqual(retry.codigo_respuesta, first.codigo_respuesta)
            self.assertNotEqual(first.codigo_respuesta, third.codigo_respuesta)

    def test_edit_preserves_code_sequence_context_person_and_audit(self):
        """Cubre 15, 20, 24-25: edición versionada sin consumir otro correlativo."""
        with Session(self.engine) as session, session.begin():
            form, question = self._form(session, "Editable", ["NOVEDADES"])
            admin = resolve_current_user(session, "admin@example.com")
            response = save_response(
                session, admin, form.id_formulario, draft=False, respuestas=self._answer(question),
                contexto_tipo="NOVEDADES", crear_contexto=True, id_persona="ana", correlation_id="create",
            )
            identity = (response.codigo_respuesta, response.numero_secuencial, response.contexto_id)
            edited = save_response(
                session, admin, form.id_formulario, draft=False, respuestas=self._answer(question, "cambio"),
                id_respuesta=response.id_respuesta, expected_version=response.version,
                editar_registrado=True, correlation_id="edit",
            )
            self.assertEqual((edited.codigo_respuesta, edited.numero_secuencial, edited.contexto_id), identity)
            self.assertGreater(edited.version, 1)
            audit = list(session.scalars(select(Auditoria).where(
                Auditoria.tabla == "envios_formulario", Auditoria.id_registro == edited.id_respuesta,
                Auditoria.accion == "UPDATE",
            )))
            self.assertTrue(any(row.motivo == "Edición de respuesta definitiva" for row in audit))
            records = person_records(session, admin, "ana", module=None, state=None, page=1, page_size=20)
            self.assertEqual(records["items"][0]["contexto_tipo"], "NOVEDADES")

    def test_structural_person_search_indirect_relations_code_filters_and_pagination(self):
        """Cubre 17-24 y 33-34: búsqueda canónica, relaciones, código, filtros y páginas."""
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin@example.com")
            found = search_options(session, admin, "PERSONAS", "Ana", limit=15)
            self.assertEqual([(row["id"], row["data"]["nombre"]) for row in found], [("ana", "Ana López García")])
            created = []
            for module, person_id, text in [("CASOS", "ana", "Ana"), ("ATENCIONES", "ana", "Ana"),
                                             ("RECORRIDOS", "ana", "Ana"), ("NOVEDADES", "beto", "Ana López García")]:
                form, question = self._form(session, f"Form {module}", [module])
                created.append(save_response(
                    session, admin, form.id_formulario, draft=False, respuestas=self._answer(question, text),
                    contexto_tipo=module, crear_contexto=True, id_persona=person_id,
                    correlation_id=module,
                ))
            ana = person_records(session, admin, "ana", module=None, state=None, page=1, page_size=2)
            self.assertEqual(ana["total"], 3)
            self.assertEqual(len(ana["items"]), 2)
            self.assertEqual(ana["total_paginas"], 2)
            second_page = person_records(session, admin, "ana", module=None, state=None, page=2, page_size=2)
            self.assertEqual(len(second_page["items"]), 1)
            only_cases = person_records(session, admin, "ana", module="CASOS", state="REGISTRADO", page=1, page_size=20)
            self.assertEqual(only_cases["total"], 1)
            self.assertEqual(response_by_code(session, admin, created[0].codigo_respuesta)["id_respuesta"], created[0].id_respuesta)
            beto = person_records(session, admin, "beto", module=None, state=None, page=1, page_size=20)
            self.assertEqual(beto["total"], 1)

    def test_search_sources_are_separated_browsable_limited_and_accent_insensitive(self):
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin@example.com")
            source_codes = {source["codigo"] for source in list_sources(admin)}
            self.assertTrue({"PERSONAS", "RESPONSABLES", "AREAS", "CENTROS_COSTO"} <= source_codes)

            responsible = search_options(session, admin, "RESPONSABLES", "lopez")
            self.assertEqual([(item["id"], item["label"]) for item in responsible], [("ana", "Ana López García")])
            self.assertEqual(responsible[0]["data"]["codigo_empleado"], "EMP-01")

            areas = search_options(session, admin, "AREAS", "gestion")
            self.assertEqual([item["label"] for item in areas], ["GESTIÓN DE CALIDAD"])
            self.assertTrue(all(set(item["data"]) == {"area"} for item in areas))

            centers = search_options(session, admin, "CENTROS_COSTO", "cc-0", limit=1)
            self.assertEqual(len(centers), 1)
            self.assertEqual(set(centers[0]["data"]), {"centro"})

            self.assertEqual(search_options(session, admin, "PERSONAS", ""), [])
            self.assertEqual(search_options(session, admin, "PERSONAS", "a"), [])
            self.assertEqual(search_options(session, admin, "PERSONAS", "%%"), [])
            self.assertEqual(search_options(session, admin, "PERSONAS", "' OR 1=1 --"), [])
            browsed = search_options(session, admin, "PERSONAS", "", limit=1, browse=True)
            self.assertEqual(len(browsed), 1)
            selected = search_options(session, admin, "RESPONSABLES", "", selected_id="ana")
            self.assertEqual([(item["id"], item["label"]) for item in selected], [("ana", "Ana López García")])
            self.assertEqual(search_options(session, admin, "RESPONSABLES", "", selected_id="missing"), [])

            session.add_all([
                Catalogo(id_catalogo=f"limit-{index}", tipo="AUDIT_LIMIT", codigo=f"L-{index:02}",
                         valor=f"Elemento {index:02}", orden=index)
                for index in range(25)
            ])
            limited = search_options(
                session, admin, "CATALOGOS", "", catalog_type="AUDIT_LIMIT", limit=999, browse=True,
            )
            self.assertEqual(len(limited), 20)

    def test_search_configuration_survives_save_publish_duplicate_and_validates_selected_id(self):
        with Session(self.engine) as session, session.begin():
            admin = resolve_current_user(session, "admin@example.com")
            form = create_formulario(
                session, admin, motivo_auditoria="Autocomplete", correlation_id="autocomplete",
                nombre="Autocomplete", destinos=["GENERAL"],
            )
            search_id, target_id = "search-person", "target-name"
            saved = save_definition(session, admin, form.id_formulario, {
                "expected_version": form.version,
                "nombre": form.nombre,
                "destinos": ["GENERAL"],
                "secciones": [],
                "preguntas": [{
                    "id_pregunta": search_id, "etiqueta": "Responsable", "tipo": "BUSQUEDA",
                    "obligatoria": True, "fuente_datos": "RESPONSABLES",
                    "configuracion": {"placeholder": "Busque una persona"},
                    "mapping": {"nombre": target_id}, "opciones": [],
                }, {
                    "id_pregunta": target_id, "etiqueta": "Nombre", "tipo": "TEXTO_CORTO",
                    "obligatoria": False, "configuracion": {}, "mapping": {}, "opciones": [],
                }],
                "reglas": [],
            }, correlation_id="autocomplete-save")
            reloaded = get_definition(session, form.id_formulario)
            search = next(question for question in reloaded["preguntas"] if question["id_pregunta"] == search_id)
            self.assertEqual(search["fuente_datos"], "RESPONSABLES")
            self.assertEqual(search["configuracion"], {"placeholder": "Busque una persona"})
            self.assertEqual(search["mapping"], {"nombre": target_id})

            change_status(session, admin, form.id_formulario, "PUBLICADO",
                          expected_version=saved["version"], correlation_id="autocomplete-publish")
            version = session.scalar(select(FormularioVersion).where(
                FormularioVersion.id_formulario == form.id_formulario,
            ))
            version_definition = json.loads(version.definicion_json)
            version_search = next(question for question in version_definition["preguntas"]
                                  if question["id_pregunta"] == search_id)
            self.assertEqual(version_search["fuente_datos"], "RESPONSABLES")
            self.assertEqual(version_search["mapping"], {"nombre": target_id})

            with self.assertRaisesRegex(AppError, "Seleccione una opción válida"):
                save_response(
                    session, admin, form.id_formulario, draft=True,
                    respuestas=[{"id_pregunta": search_id, "valor_opcion": "texto-arbitrario"}],
                    correlation_id="invalid-search",
                )
            response = save_response(
                session, admin, form.id_formulario, draft=False,
                respuestas=[{"id_pregunta": search_id, "valor_opcion": "ana"}],
                correlation_id="valid-search",
            )
            self.assertEqual(response.estado, "REGISTRADO")

            copy = duplicate_form(session, admin, form.id_formulario, correlation_id="autocomplete-copy")
            copied_definition = get_definition(session, copy.id_formulario)
            copied_search = next(question for question in copied_definition["preguntas"]
                                 if question["etiqueta"] == "Responsable")
            copied_target = next(question for question in copied_definition["preguntas"]
                                 if question["etiqueta"] == "Nombre")
            self.assertEqual(copied_search["fuente_datos"], "RESPONSABLES")
            self.assertEqual(copied_search["configuracion"], {"placeholder": "Busque una persona"})
            self.assertEqual(copied_search["mapping"], {"nombre": copied_target["id_pregunta"]})
            self.assertNotEqual(copied_target["id_pregunta"], target_id)

    def test_permissions_sensitive_visibility_delete_and_audit_and_no_code_reuse(self):
        """Cubre 16 y 26-30: RBAC granular, sensibilidad y eliminación lógica auditada."""
        with Session(self.engine) as session, session.begin():
            form, question = self._form(session, "Restringido", ["CASOS"])
            admin = resolve_current_user(session, "admin@example.com")
            response = save_response(
                session, admin, form.id_formulario, draft=False, respuestas=self._answer(question),
                contexto_tipo="CASOS", crear_contexto=True, id_persona="ana", correlation_id="create",
            )
            first_number = response.numero_secuencial
            limited = AuthenticatedUser(
                id_usuario="limited", correo="limited@example.com", nombre="Limited", rol_id="LIMITED",
                rol_nombre="Limited", permisos={
                    "RESPUESTAS": {"read": True, "create": False, "edit": False, "delete": False, "sensitive": False, "export": False},
                    "CASOS": {"read": True, "create": False, "edit": False, "delete": False, "sensitive": False, "export": False},
                    "PERSONAS": {"read": True, "create": False, "edit": False, "delete": False, "sensitive": False, "export": False},
                },
            )
            with self.assertRaises(AppError):
                save_response(session, limited, form.id_formulario, draft=False, respuestas=self._answer(question),
                              id_respuesta=response.id_respuesta, expected_version=response.version,
                              editar_registrado=True, correlation_id="forbidden-edit")
            with self.assertRaises(AppError):
                soft_delete_dynamic_response(session, limited, response.id_respuesta,
                                             expected_version=response.version, reason="No", correlation_id="no")
            deleted = soft_delete_dynamic_response(
                session, admin, response.id_respuesta, expected_version=response.version,
                reason="Duplicado validado", correlation_id="delete",
            )
            self.assertTrue(deleted.eliminado)
            self.assertEqual(deleted.codigo_respuesta, "TTHH_RRLL_00000000001")
            self.assertTrue(session.scalar(select(Auditoria).where(
                Auditoria.tabla == "envios_formulario", Auditoria.id_registro == deleted.id_respuesta,
                Auditoria.accion == "DELETE", Auditoria.motivo == "Duplicado validado",
            )))
            next_response = save_response(
                session, admin, form.id_formulario, draft=False, respuestas=self._answer(question),
                contexto_tipo="CASOS", crear_contexto=True, id_persona="ana", correlation_id="next",
            )
            self.assertEqual(next_response.numero_secuencial, first_number + 1)

            session.add(Catalogo(id_catalogo="sensible", tipo="NIVEL_SENSIBILIDAD", codigo="ALTO",
                                 valor="Alto", es_sensible=True, orden=1))
            session.add(Caso(id_caso="sensitive-case", codigo_caso="CAS-S", id_persona="ana",
                             nivel_sensibilidad="ALTO"))
            hidden = save_response(
                session, admin, form.id_formulario, draft=False, respuestas=self._answer(question),
                contexto_tipo="CASOS", contexto_id="sensitive-case", correlation_id="sensitive",
            )
            visible_ids = {item.get("id_respuesta") for item in person_records(
                session, limited, "ana", module=None, state=None, page=1, page_size=20,
            )["items"]}
            self.assertNotIn(hidden.id_respuesta, visible_ids)

    def test_module_listing_is_paginated_and_state_filtered(self):
        with Session(self.engine) as session, session.begin():
            form, question = self._form(session, "Listado", ["RECORRIDOS"], multiple=True)
            admin = resolve_current_user(session, "admin@example.com")
            save_response(session, admin, form.id_formulario, draft=True, respuestas=self._answer(question),
                          contexto_tipo="RECORRIDOS", crear_contexto=True, id_persona="ana", correlation_id="d")
            save_response(session, admin, form.id_formulario, draft=False, respuestas=self._answer(question),
                          contexto_tipo="RECORRIDOS", crear_contexto=True, id_persona="ana", correlation_id="f")
            page = list_module_responses(session, admin, "RECORRIDOS", state="BORRADOR", page=1, page_size=1)
            self.assertEqual(page["total"], 1)
            self.assertEqual(page["items"][0]["estado"], "BORRADOR")
            self.assertIsNone(page["items"][0]["codigo_respuesta"])
            self.assertFalse(page["items"][0]["acciones"]["ver"])
            self.assertTrue(page["items"][0]["acciones"]["continuar"])


if __name__ == "__main__":
    unittest.main()
