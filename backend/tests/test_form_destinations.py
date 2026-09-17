import unittest
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, resolve_current_user
from app.db.session import build_engine
from app.models import Auditoria, DestinoFormulario, EnvioFormulario, FormularioDestino, User
from app.services.form_destinations import (
    DESTINOS_INICIALES, list_active_destinations, list_destination_responses,
    list_destination_tree, list_form_destinations, seed_form_destinations, set_form_destinations,
)
from app.services.formularios import change_status, create_formulario
from app.services.preguntas import preguntas
from app.services.respuestas_formulario import save_response
from app.services.security_seed import seed_security


class FormDestinationTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.engine = build_engine(f"sqlite:///{self.directory.name}/destinations.db")
        self.original_engine = db_session.engine
        db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")
        with Session(self.engine) as session, session.begin():
            seed_security(session)
            seed_form_destinations(session)
            session.add_all([
                User(id_usuario="admin", correo="admin@example.com", nombre="Admin", rol_id="ROLE_ADMIN", estado="ACTIVO"),
                User(id_usuario="ts", correo="ts@example.com", nombre="TS", rol_id="ROLE_TRABAJADOR_SOCIAL", estado="ACTIVO"),
            ])

    def tearDown(self):
        db_session.engine = self.original_engine
        self.engine.dispose()
        self.directory.cleanup()

    def _user(self, session, email="admin@example.com"):
        return resolve_current_user(session, email)

    def _published_form(self, session):
        admin = self._user(session)
        form = create_formulario(session, admin, motivo_auditoria="Alta", correlation_id="form",
                                 nombre="Formulario de destino", destinos=["GENERAL"])
        question = preguntas.create(session, admin, motivo_auditoria="Pregunta", correlation_id="question",
                                    id_formulario=form.id_formulario, etiqueta="Detalle")
        change_status(session, admin, form.id_formulario, "PUBLICADO",
                      expected_version=form.version, correlation_id="publish")
        return form, question

    def test_catalog_tree_codes_hierarchy_and_idempotent_seed(self):
        with Session(self.engine) as session, session.begin():
            admin = self._user(session)
            initial_count = session.query(DestinoFormulario).count()
            seed_form_destinations(session)
            self.assertEqual(session.query(DestinoFormulario).count(), initial_count)
            self.assertEqual(initial_count, len(DESTINOS_INICIALES))
            roots = list_destination_tree(session, admin)
            self.assertEqual([(item["codigo"], item["nivel"]) for item in roots], [("TRABAJO_SOCIAL", "MACROPROCESO")])
            production = next(item for item in roots[0]["hijos"] if item["codigo"] == "PRODUCCION")
            self.assertEqual([item["codigo"] for item in production["hijos"]],
                             ["PRODUCCION_ATENCIONES", "RECORRIDOS", "NOVEDADES_PLANTA"])
            self.assertEqual(len({row.codigo for row in session.scalars(select(DestinoFormulario))}), initial_count)

    def test_only_active_leaves_of_valid_branch_are_assignable(self):
        with Session(self.engine) as session, session.begin():
            admin = self._user(session)
            leaves = {item["codigo"] for item in list_active_destinations(session, admin)}
            self.assertIn("RECORRIDOS", leaves)
            self.assertNotIn("PRODUCCION", leaves)
            form, _ = self._published_form(session)
            with self.assertRaises(AppError) as ctx:
                set_form_destinations(session, admin, form.id_formulario, ["destino-produccion"])
            self.assertEqual(ctx.exception.code, "INVALID_FORM_DESTINATION")
            session.get(DestinoFormulario, "destino-recorridos").activo = False
            with self.assertRaises(AppError) as ctx:
                set_form_destinations(session, admin, form.id_formulario, ["destino-recorridos"])
            self.assertEqual(ctx.exception.code, "INVALID_FORM_DESTINATION")

    def test_multiple_assignments_are_unique_audited_and_soft_retired(self):
        with Session(self.engine) as session, session.begin():
            admin = self._user(session)
            form, _ = self._published_form(session)
            assigned = set_form_destinations(session, admin, form.id_formulario,
                                             ["destino-recorridos", "destino-novedades-planta"], correlation_id="assign")
            self.assertEqual({item["destino"]["codigo"] for item in assigned}, {"RECORRIDOS", "NOVEDADES_PLANTA"})
            with self.assertRaises(AppError) as ctx:
                set_form_destinations(session, admin, form.id_formulario,
                                      ["destino-recorridos", "destino-recorridos"])
            self.assertEqual(ctx.exception.code, "DUPLICATE_FORM_DESTINATION")
            assigned = set_form_destinations(session, admin, form.id_formulario,
                                             ["destino-novedades-planta"], correlation_id="retire")
            self.assertEqual([item["destino"]["codigo"] for item in assigned], ["NOVEDADES_PLANTA"])
            historical = list_form_destinations(session, admin, form.id_formulario, include_inactive=True)
            retired = next(item for item in historical if item["destino"]["codigo"] == "RECORRIDOS")
            self.assertFalse(retired["activo"])
            self.assertTrue(retired["eliminado"])
            self.assertTrue(session.scalar(select(Auditoria).where(Auditoria.tabla == "formulario_destinos")))

    def test_response_destination_is_validated_preserved_and_isolated(self):
        with Session(self.engine) as session, session.begin():
            admin = self._user(session)
            form, question = self._published_form(session)
            set_form_destinations(session, admin, form.id_formulario,
                                  ["destino-recorridos", "destino-novedades-planta"])
            response = save_response(session, admin, form.id_formulario, draft=False,
                                     respuestas=[{"id_pregunta": question.id_pregunta, "valor_texto": "ok"}],
                                     id_destino_respuesta="destino-recorridos", correlation_id="response")
            self.assertEqual(response.id_destino_respuesta, "destino-recorridos")
            self.assertEqual([item.id_respuesta for item in list_destination_responses(
                session, admin, "destino-recorridos")], [response.id_respuesta])
            self.assertEqual(list_destination_responses(session, admin, "destino-novedades-planta"), [])
            set_form_destinations(session, admin, form.id_formulario, ["destino-novedades-planta"])
            self.assertEqual(session.get(EnvioFormulario, response.id_respuesta).id_destino_respuesta, "destino-recorridos")
            with self.assertRaises(AppError) as ctx:
                save_response(session, admin, form.id_formulario, draft=False,
                              respuestas=[{"id_pregunta": question.id_pregunta, "valor_texto": "bad"}],
                              id_envio_cliente="not-allowed", id_destino_respuesta="destino-recorridos", correlation_id="bad")
            self.assertEqual(ctx.exception.code, "RESPONSE_DESTINATION_NOT_ALLOWED")
            with self.assertRaises(AppError) as ctx:
                save_response(session, admin, form.id_formulario, draft=False,
                              respuestas=[{"id_pregunta": question.id_pregunta, "valor_texto": "bad"}],
                              id_envio_cliente="missing", id_destino_respuesta="missing", correlation_id="missing")
            self.assertEqual(ctx.exception.code, "RESPONSE_DESTINATION_NOT_FOUND")

    def test_legacy_text_destinations_and_historical_responses_remain_unclassified(self):
        with Session(self.engine) as session, session.begin():
            admin = self._user(session)
            form, question = self._published_form(session)
            historic = save_response(session, admin, form.id_formulario, draft=False,
                                     respuestas=[{"id_pregunta": question.id_pregunta, "valor_texto": "legacy"}],
                                     correlation_id="legacy")
            self.assertIsNone(historic.id_destino_respuesta)
            legacy = session.scalar(select(FormularioDestino).where(
                FormularioDestino.id_formulario == form.id_formulario,
                FormularioDestino.id_destino_catalogo.is_(None), FormularioDestino.modulo == "GENERAL",
            ))
            self.assertIsNotNone(legacy)

    def test_destination_administration_requires_form_permission(self):
        limited = AuthenticatedUser(
            id_usuario="limited", correo="limited@example.com", nombre="Limited", rol_id="LIMITED",
            rol_nombre="Limited", permisos={"FORMULARIOS": {"read": True, "create": False, "edit": False, "delete": False, "sensitive": False, "export": False}},
        )
        with Session(self.engine) as session, session.begin():
            form, _ = self._published_form(session)
            with self.assertRaises(AppError) as ctx:
                set_form_destinations(session, limited, form.id_formulario, ["destino-recorridos"])
            self.assertEqual(ctx.exception.code, "FORBIDDEN")

    def test_migration_schema_has_foreign_keys_and_indexes(self):
        inspector = inspect(self.engine)
        self.assertIn("destinos_formulario", inspector.get_table_names())
        self.assertIn("id_destino_catalogo", {c["name"] for c in inspector.get_columns("formulario_destinos")})
        self.assertIn("id_destino_respuesta", {c["name"] for c in inspector.get_columns("envios_formulario")})
        self.assertTrue(any(fk["referred_table"] == "destinos_formulario" for fk in inspector.get_foreign_keys("envios_formulario")))
        self.assertIn("ix_envios_formulario_id_destino_respuesta", {item["name"] for item in inspector.get_indexes("envios_formulario")})


if __name__ == "__main__":
    unittest.main()
