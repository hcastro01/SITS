"""Bloque 4: adjuntos repetibles de respuestas dinámicas.

Estas pruebas ejercitan el servicio transaccional, no una simulación HTTP: por eso
pueden comprobar directamente que un ``flush`` previo no deja filas huérfanas.
"""

import json
import unittest
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.core.errors import AppError
from app.core.permissions import resolve_current_user
from app.db.session import build_engine
from app.models import Documento, EnvioFormulario, Formulario, Pregunta, RespuestaDocumento, RespuestaFormulario, User
from app.services.dynamic_responses import get_user_response
from app.services.formularios import change_status, create_formulario
from app.services.preguntas import preguntas
from app.services.respuestas_formulario import save_response
from app.services.security_seed import seed_security
from app.services.documentos import upload_documento

PDF = b"%PDF-1.4\nBloque 4\n%%EOF"
JPEG = b"\xff\xd8\xff\xe0" + b"x" * 32
PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 32
WEBP = b"RIFF" + (16).to_bytes(4, "little") + b"WEBPVP8 " + b"x" * 8


class FormResponseAttachmentTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.engine = build_engine(f"sqlite:///{self.directory.name}/attachments.db")
        self.original_engine = db_session.engine
        db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")
        with Session(self.engine) as session, session.begin():
            seed_security(session)
            session.add(User(id_usuario="admin", correo="admin@example.com", nombre="Admin", rol_id="ROLE_ADMIN", estado="ACTIVO"))
            session.add(User(id_usuario="ts", correo="ts@example.com", nombre="TS", rol_id="ROLE_TRABAJADOR_SOCIAL", estado="ACTIVO"))
            session.add(User(id_usuario="consulta", correo="consulta@example.com", nombre="Consulta", rol_id="ROLE_CONSULTA", estado="ACTIVO"))
            admin = resolve_current_user(session, "admin@example.com")
            form = create_formulario(session, admin, motivo_auditoria="Alta", correlation_id="setup", nombre="Adjuntos")
            form.permite_multiples_respuestas = True
            self.form_id = form.id_formulario
            self.text_id = self._question(session, admin, "Nota", "TEXTO_CORTO")
            self.file_a = self._question(session, admin, "Archivo A", "ARCHIVO", max_files=3)
            self.file_b = self._question(session, admin, "Archivo B", "ARCHIVO", max_files=3)
            self.photo_id = self._question(session, admin, "Foto", "FOTOGRAFIA", max_files=3)
            change_status(session, admin, self.form_id, "PUBLICADO", expected_version=form.version, correlation_id="publish")

    def tearDown(self):
        db_session.engine = self.original_engine
        self.engine.dispose()
        self.directory.cleanup()

    def _question(self, session, user, label, kind, **config):
        row = preguntas.create(session, user, motivo_auditoria="Alta", correlation_id=label,
                                id_formulario=self.form_id, etiqueta=label, tipo=kind,
                                configuracion=json.dumps(config))
        return row.id_pregunta

    def _user(self, session):
        return resolve_current_user(session, "ts@example.com")

    @staticmethod
    def attachment(question_id, name, mime, content):
        return {"id_pregunta": question_id, "nombre_archivo": name, "mime_type": mime, "contenido": content}

    def _save(self, session, *, answers=None, attachments=None, key=None):
        return save_response(session, self._user(session), self.form_id, draft=False,
                             respuestas=answers or [], adjuntos=attachments or [],
                             id_envio_cliente=key, correlation_id="attachments")

    @staticmethod
    def _counts(session):
        return tuple(session.scalar(select(func.count()).select_from(model)) for model in
                     (EnvioFormulario, RespuestaFormulario, RespuestaDocumento, Documento))

    def test_historical_and_optional_file_responses_have_no_links(self):
        with Session(self.engine) as session, session.begin():
            response = self._save(session, answers=[{"id_pregunta": self.text_id, "valor_texto": "histórica"}])
            serialized = get_user_response(session, self._user(session), response.id_respuesta)
            self.assertNotIn("adjuntos", serialized["respuestas"][0])
            self.assertEqual(session.scalar(select(func.count()).select_from(RespuestaDocumento)), 0)

    def test_archive_formats_and_traceability_are_persisted_without_blob_serialization(self):
        files = [
            self.attachment(self.file_a, "a.pdf", "application/pdf", PDF),
            self.attachment(self.file_a, "a.jpg", "image/jpeg", JPEG),
            self.attachment(self.file_b, "b.png", "image/png", PNG),
            self.attachment(self.photo_id, "c.webp", "image/webp", WEBP),
        ]
        with Session(self.engine) as session, session.begin():
            response = self._save(session, answers=[{"id_pregunta": self.text_id, "valor_texto": "nota"}], attachments=files)
            rows = session.execute(select(RespuestaDocumento, RespuestaFormulario, Documento).join(
                RespuestaFormulario, RespuestaFormulario.id_detalle_respuesta == RespuestaDocumento.id_detalle_respuesta
            ).join(Documento, Documento.id_archivo == RespuestaDocumento.id_archivo)).all()
            self.assertEqual(len(rows), 4)
            self.assertEqual({detail.id_pregunta for _, detail, _ in rows}, {self.file_a, self.file_b, self.photo_id})
            self.assertTrue(all(detail.id_respuesta == response.id_respuesta for _, detail, _ in rows))
            self.assertEqual({document.nombre_archivo for _, _, document in rows}, {"a.pdf", "a.jpg", "b.png", "c.webp"})
            data = get_user_response(session, self._user(session), response.id_respuesta)
            self.assertEqual(sum(len(answer.get("adjuntos", [])) for answer in data["respuestas"]), 4)
            self.assertNotIn("contenido_comprimido", str(data))

    def test_multipart_parser_collects_starlette_upload_files(self):
        from app.api.formularios import response_request_payload

        app = FastAPI()

        @app.post("/")
        async def parse(request: Request):
            _payload, attachments = await response_request_payload(request)
            return {"count": len(attachments), "name": attachments[0]["nombre_archivo"] if attachments else None}

        with TestClient(app) as client:
            response = client.post(
                "/", data={"payload": json.dumps({"borrador": False})},
                files=[("archivo:foto", ("foto.jpg", JPEG, "image/jpeg"))],
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"count": 1, "name": "foto.jpg"})

    def test_photo_rejects_pdf_and_document_validates_extension_mime_and_signature(self):
        cases = [
            (self.photo_id, "photo.pdf", "application/pdf", PDF, "INVALID_FILE_TYPE"),
            (self.file_a, "bad.txt", "text/plain", b"text", "INVALID_FILE_TYPE"),
            (self.file_a, "bad.jpg", "image/jpeg", PDF, "FILE_SIGNATURE_MISMATCH"),
        ]
        for question_id, name, mime, content, code in cases:
            with self.subTest(name=name):
                with self.assertRaises(AppError) as ctx:
                    with Session(self.engine) as session, session.begin():
                        self._save(session, attachments=[self.attachment(question_id, name, mime, content)])
                self.assertEqual(ctx.exception.code, code)

    def test_limits_apply_per_question_and_never_exceed_global_limit(self):
        with Session(self.engine) as session, session.begin():
            # La configuración se ajusta sólo para esta prueba; 5 MiB no acepta 6 MiB.
            question = session.get(Pregunta, self.file_a)
            question.configuracion = json.dumps({"max_files": 1, "max_size_mb": 5})
            with self.assertRaises(AppError) as ctx:
                self._save(session, attachments=[self.attachment(self.file_a, "large.jpg", "image/jpeg", JPEG[:3] + b"x" * (6 * 1024 * 1024))])
            self.assertEqual(ctx.exception.code, "FILE_TOO_LARGE")
        with Session(self.engine) as session, session.begin():
            question = session.get(Pregunta, self.file_a)
            question.configuracion = json.dumps({"max_files": 1, "max_size_mb": 20})
            with self.assertRaises(AppError) as ctx:
                self._save(session, attachments=[self.attachment(self.file_a, "global.jpg", "image/jpeg", JPEG[:3] + b"x" * (10 * 1024 * 1024 + 1))])
            self.assertEqual(ctx.exception.code, "FILE_TOO_LARGE")

    def test_max_files_is_per_question_and_capped_by_global_document_limit(self):
        with Session(self.engine) as session, session.begin():
            question = session.get(Pregunta, self.file_a)
            question.configuracion = json.dumps({"max_files": 1})
            with self.assertRaises(AppError) as ctx:
                self._save(session, attachments=[self.attachment(self.file_a, "one.jpg", "image/jpeg", JPEG), self.attachment(self.file_a, "two.jpg", "image/jpeg", JPEG)])
            self.assertEqual(ctx.exception.code, "TOO_MANY_FILES")
        with Session(self.engine) as session, session.begin():
            response = self._save(session, attachments=[self.attachment(self.file_a, "one.jpg", "image/jpeg", JPEG), self.attachment(self.file_b, "two.jpg", "image/jpeg", JPEG)])
            self.assertIsNotNone(response.id_respuesta)

    def test_invalid_later_file_rolls_back_all_four_tables(self):
        with Session(self.engine) as session:
            before = self._counts(session)
        with self.assertRaises(AppError):
            with Session(self.engine) as session, session.begin():
                self._save(session, attachments=[self.attachment(self.file_a, "first.pdf", "application/pdf", PDF), self.attachment(self.file_a, "bad.jpg", "image/jpeg", PDF)])
        with Session(self.engine) as session:
            self.assertEqual(self._counts(session), before)

    def test_cross_question_invalid_file_rolls_back_all_four_tables(self):
        with Session(self.engine) as session:
            before = self._counts(session)
        with self.assertRaises(AppError):
            with Session(self.engine) as session, session.begin():
                self._save(session, attachments=[self.attachment(self.file_a, "valid.pdf", "application/pdf", PDF), self.attachment(self.file_b, "bad.jpg", "image/jpeg", PDF)])
        with Session(self.engine) as session:
            self.assertEqual(self._counts(session), before)

    def test_response_with_attachment_cannot_be_edited_but_plain_response_can(self):
        with Session(self.engine) as session, session.begin():
            attached = self._save(session, attachments=[self.attachment(self.file_a, "a.pdf", "application/pdf", PDF)], key="attached")
            attached_id, attached_version = attached.id_respuesta, attached.version
        with Session(self.engine) as session, session.begin():
            with self.assertRaises(AppError) as ctx:
                save_response(session, self._user(session), self.form_id, draft=False,
                              respuestas=[{"id_pregunta": self.text_id, "valor_texto": "attempt"}],
                              id_respuesta=attached_id, expected_version=attached_version,
                              editar_registrado=True, correlation_id="edit-attached")
            self.assertEqual(ctx.exception.code, "FORM_RESPONSE_WITH_ATTACHMENTS_IMMUTABLE")
            self.assertIsNotNone(attached_id)
        with Session(self.engine) as session, session.begin():
            plain = self._save(session, answers=[{"id_pregunta": self.text_id, "valor_texto": "before"}], key="plain")
            plain_id, plain_version = plain.id_respuesta, plain.version
        with Session(self.engine) as session, session.begin():
            updated = save_response(session, self._user(session), self.form_id, draft=False,
                                    respuestas=[{"id_pregunta": self.text_id, "valor_texto": "after"}],
                                    id_respuesta=plain_id, expected_version=plain_version,
                                    editar_registrado=True, correlation_id="edit")
            self.assertEqual(updated.id_respuesta, plain_id)

    def test_draft_with_attachment_can_be_finalized_and_preserves_document(self):
        with Session(self.engine) as session, session.begin():
            draft = save_response(
                session, self._user(session), self.form_id, draft=True,
                respuestas=[{"id_pregunta": self.text_id, "valor_texto": "borrador"}],
                id_envio_cliente="draft-with-file", correlation_id="draft",
                adjuntos=[self.attachment(self.photo_id, "draft.jpg", "image/jpeg", JPEG)],
            )
            draft_id, draft_version = draft.id_respuesta, draft.version
        with Session(self.engine) as session, session.begin():
            finalized = save_response(
                session, self._user(session), self.form_id, draft=False,
                respuestas=[{"id_pregunta": self.text_id, "valor_texto": "final"}],
                id_respuesta=draft_id, expected_version=draft_version, correlation_id="final",
            )
            data = get_user_response(session, self._user(session), finalized.id_respuesta)
            attachments = [item for answer in data["respuestas"] for item in answer.get("adjuntos", [])]
            self.assertEqual(finalized.estado, "REGISTRADO")
            self.assertEqual([item["nombre_archivo"] for item in attachments], ["draft.jpg"])

    def test_download_requires_the_exact_response_document_link_and_active_document(self):
        """El id del documento por sí solo no permite cruzar respuestas ni omitir el puente."""
        from app.api.formularios import descargar_adjunto_respuesta
        request = SimpleNamespace(state=SimpleNamespace(correlation_id="attachment-download"))
        with Session(self.engine) as session, session.begin():
            owner = self._user(session)
            first = self._save(session, attachments=[self.attachment(self.file_a, "first.pdf", "application/pdf", PDF)], key="first")
            second = self._save(session, attachments=[self.attachment(self.file_b, "second.pdf", "application/pdf", PDF)], key="second")
            first_doc = session.scalar(select(Documento).where(Documento.id_registro == first.id_respuesta))
            second_doc = session.scalar(select(Documento).where(Documento.id_registro == second.id_respuesta))
            unlinked = upload_documento(session, owner, tipo_registro="RESPUESTAS_FORMULARIO", id_registro=first.id_respuesta,
                                        nombre_archivo="unlinked.pdf", mime_type="application/pdf", contenido=PDF)
            allowed = descargar_adjunto_respuesta(first.id_respuesta, first_doc.id_archivo, request, session, owner)
            self.assertEqual(allowed.body, PDF)
            for document_id in (second_doc.id_archivo, unlinked.id_archivo):
                with self.subTest(document_id=document_id), self.assertRaises(AppError) as ctx:
                    descargar_adjunto_respuesta(first.id_respuesta, document_id, request, session, owner)
                self.assertEqual(ctx.exception.code, "FORM_ATTACHMENT_NOT_FOUND")
            first_doc.eliminado = True
            with self.assertRaises(AppError) as ctx:
                descargar_adjunto_respuesta(first.id_respuesta, first_doc.id_archivo, request, session, owner)
            self.assertEqual(ctx.exception.code, "NOT_FOUND")

    def test_download_rejects_authenticated_user_without_response_permission(self):
        from app.api.formularios import descargar_adjunto_respuesta
        request = SimpleNamespace(state=SimpleNamespace(correlation_id="attachment-forbidden"))
        with Session(self.engine) as session, session.begin():
            response = self._save(session, attachments=[self.attachment(self.file_a, "private.pdf", "application/pdf", PDF)])
            document = session.scalar(select(Documento).where(Documento.id_registro == response.id_respuesta))
            consulta = resolve_current_user(session, "consulta@example.com")
            with self.assertRaises(AppError) as ctx:
                descargar_adjunto_respuesta(response.id_respuesta, document.id_archivo, request, session, consulta)
            self.assertEqual(ctx.exception.code, "FORBIDDEN")


if __name__ == "__main__":
    unittest.main()
