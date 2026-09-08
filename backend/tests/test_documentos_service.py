import hashlib
import unittest
import zlib
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

import app.db.session as db_session
from app.core.errors import AppError
from app.core.permissions import resolve_current_user
from app.db.session import build_engine
from app.models import Auditoria, Caso, Catalogo, EnvioFormulario, Formulario, Persona, Seguimiento, User
from app.services.documentos import (
    MAX_FILES_PER_RECORD, download_documento, list_documentos, soft_delete_documento, upload_documento,
)
from app.services.security_seed import seed_security

PDF_BYTES = b"%PDF-1.4\n%dummy pdf content for tests\n%%EOF"
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 32
WEBP_BYTES = b"RIFF" + (16).to_bytes(4, "little") + b"WEBPVP8 " + b"\x00" * 8
WRONG_SIGNATURE_JPEG = PDF_BYTES  # contenido de PDF con nombre .jpg


class DocumentosServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.engine = build_engine(f"sqlite:///{self.directory.name}/test.db")
        self._original_engine = db_session.engine
        db_session.engine = self.engine
        command.upgrade(Config("alembic.ini"), "head")
        with Session(self.engine) as session, session.begin():
            seed_security(session)
            session.add(User(id_usuario="ts", correo="ts@example.com", nombre="Trabajador",
                              rol_id="ROLE_TRABAJADOR_SOCIAL", estado="ACTIVO"))
            session.add(User(id_usuario="ts2", correo="ts2@example.com", nombre="Trabajador 2",
                              rol_id="ROLE_TRABAJADOR_SOCIAL", estado="ACTIVO"))
            session.add(User(id_usuario="consulta", correo="consulta@example.com", nombre="Consulta",
                              rol_id="ROLE_CONSULTA", estado="ACTIVO"))
            session.add(User(id_usuario="admin", correo="admin@example.com", nombre="Admin",
                              rol_id="ROLE_ADMIN", estado="ACTIVO"))
            session.add(Persona(id_persona="p1", nombre="Ana"))
            session.add(Caso(id_caso="c1", codigo_caso="CAS-2026-0001", nivel_sensibilidad="ALTA"))
            session.add(Caso(id_caso="c2", codigo_caso="CAS-2026-0002"))
            session.add(Formulario(id_formulario="f1", nombre="Adjuntos"))
            session.flush()
            session.add(Seguimiento(id_seguimiento="s1", id_caso="c1", descripcion="Seguimiento de caso sensible"))
            session.add(EnvioFormulario(id_respuesta="r1", id_formulario="f1", usuario_respuesta="ts@example.com",
                                        estado="BORRADOR", contexto_tipo="GENERAL"))
            session.add(Catalogo(id_catalogo="cat1", tipo="NIVEL_SENSIBILIDAD", codigo="ALTA", valor="Alta",
                                  es_sensible=True))

    def tearDown(self):
        db_session.engine = self._original_engine
        self.engine.dispose()
        self.directory.cleanup()

    def _user(self, session, correo):
        return resolve_current_user(session, correo)

    def test_upload_requires_edit_permission_on_parent_module(self):
        with Session(self.engine) as session, session.begin():
            consulta = self._user(session, "consulta@example.com")
            with self.assertRaises(AppError) as ctx:
                upload_documento(session, consulta, tipo_registro="PERSONAS", id_registro="p1",
                                  nombre_archivo="foto.jpg", mime_type="image/jpeg", contenido=JPEG_BYTES)
            self.assertEqual(ctx.exception.code, "FORBIDDEN")

    def test_upload_rejects_unknown_tipo_registro(self):
        with Session(self.engine) as session, session.begin():
            ts = self._user(session, "ts@example.com")
            with self.assertRaises(AppError) as ctx:
                upload_documento(session, ts, tipo_registro="INVENTADO", id_registro="p1",
                                  nombre_archivo="foto.jpg", mime_type="image/jpeg", contenido=JPEG_BYTES)
            self.assertEqual(ctx.exception.code, "INVALID_ENTITY")

    def test_upload_rejects_missing_parent_record(self):
        with Session(self.engine) as session, session.begin():
            ts = self._user(session, "ts@example.com")
            with self.assertRaises(AppError) as ctx:
                upload_documento(session, ts, tipo_registro="PERSONAS", id_registro="no-existe",
                                  nombre_archivo="foto.jpg", mime_type="image/jpeg", contenido=JPEG_BYTES)
            self.assertEqual(ctx.exception.code, "NOT_FOUND")

    def test_upload_rejects_extension_mime_mismatch(self):
        with Session(self.engine) as session, session.begin():
            ts = self._user(session, "ts@example.com")
            with self.assertRaises(AppError) as ctx:
                upload_documento(session, ts, tipo_registro="PERSONAS", id_registro="p1",
                                  nombre_archivo="notas.txt", mime_type="text/plain", contenido=b"hola")
            self.assertEqual(ctx.exception.code, "INVALID_FILE_TYPE")

    def test_upload_rejects_binary_signature_mismatch(self):
        with Session(self.engine) as session, session.begin():
            ts = self._user(session, "ts@example.com")
            with self.assertRaises(AppError) as ctx:
                upload_documento(session, ts, tipo_registro="PERSONAS", id_registro="p1",
                                  nombre_archivo="foto.jpg", mime_type="image/jpeg",
                                  contenido=WRONG_SIGNATURE_JPEG)
            self.assertEqual(ctx.exception.code, "FILE_SIGNATURE_MISMATCH")

    def test_webp_requires_riff_and_webp_signature(self):
        with Session(self.engine) as session, session.begin():
            ts = self._user(session, "ts@example.com")
            document = upload_documento(session, ts, tipo_registro="PERSONAS", id_registro="p1",
                                         nombre_archivo="foto.webp", mime_type="image/webp", contenido=WEBP_BYTES)
            self.assertEqual(document.extension, "webp")
            with self.assertRaises(AppError) as ctx:
                upload_documento(session, ts, tipo_registro="PERSONAS", id_registro="p1",
                                  nombre_archivo="falso.webp", mime_type="image/webp",
                                  contenido=b"RIFF" + b"\x00" * 20)
            self.assertEqual(ctx.exception.code, "FILE_SIGNATURE_MISMATCH")

    def test_response_attachment_round_trip_and_ownership(self):
        with Session(self.engine) as session, session.begin():
            owner = self._user(session, "ts@example.com")
            document = upload_documento(session, owner, tipo_registro="RESPUESTAS_FORMULARIO", id_registro="r1",
                                         nombre_archivo="evidencia.pdf", mime_type="application/pdf", contenido=PDF_BYTES)
            document_id = document.id_archivo
        with Session(self.engine) as session, session.begin():
            owner = self._user(session, "ts@example.com")
            self.assertEqual(download_documento(session, owner, document_id)[1], PDF_BYTES)
            other = self._user(session, "ts2@example.com")
            with self.assertRaises(AppError) as ctx:
                upload_documento(session, other, tipo_registro="RESPUESTAS_FORMULARIO", id_registro="r1",
                                  nombre_archivo="ajeno.pdf", mime_type="application/pdf", contenido=PDF_BYTES)
            self.assertEqual(ctx.exception.code, "FORBIDDEN")

    def test_upload_enforces_size_limit(self):
        with Session(self.engine) as session, session.begin():
            ts = self._user(session, "ts@example.com")
            enorme = JPEG_BYTES[:3] + b"\x00" * (10 * 1024 * 1024 + 1)
            with self.assertRaises(AppError) as ctx:
                upload_documento(session, ts, tipo_registro="PERSONAS", id_registro="p1",
                                  nombre_archivo="foto.jpg", mime_type="image/jpeg", contenido=enorme)
            self.assertEqual(ctx.exception.code, "FILE_TOO_LARGE")

    def test_upload_enforces_max_files_per_record(self):
        with Session(self.engine) as session, session.begin():
            ts = self._user(session, "ts@example.com")
            for _ in range(MAX_FILES_PER_RECORD):
                upload_documento(session, ts, tipo_registro="PERSONAS", id_registro="p1",
                                  nombre_archivo="foto.jpg", mime_type="image/jpeg", contenido=JPEG_BYTES)
            with self.assertRaises(AppError) as ctx:
                upload_documento(session, ts, tipo_registro="PERSONAS", id_registro="p1",
                                  nombre_archivo="foto.jpg", mime_type="image/jpeg", contenido=JPEG_BYTES)
            self.assertEqual(ctx.exception.code, "TOO_MANY_FILES")

    def test_upload_compresses_content_and_computes_sha256_of_original(self):
        with Session(self.engine) as session, session.begin():
            ts = self._user(session, "ts@example.com")
            documento = upload_documento(session, ts, tipo_registro="PERSONAS", id_registro="p1",
                                          nombre_archivo="../../etc/reporte.pdf", mime_type="application/pdf",
                                          contenido=PDF_BYTES)
            self.assertEqual(documento.sha256, hashlib.sha256(PDF_BYTES).hexdigest())
            self.assertEqual(documento.tamano_bytes, len(PDF_BYTES))
            self.assertEqual(zlib.decompress(documento.contenido_comprimido), PDF_BYTES)
            self.assertNotIn("/", documento.nombre_archivo)
            self.assertNotIn("..", documento.nombre_archivo)

    def test_upload_writes_create_audit_row(self):
        with Session(self.engine) as session, session.begin():
            ts = self._user(session, "ts@example.com")
            documento = upload_documento(session, ts, tipo_registro="PERSONAS", id_registro="p1",
                                          nombre_archivo="foto.jpg", mime_type="image/jpeg", contenido=JPEG_BYTES)
            id_archivo = documento.id_archivo
        with Session(self.engine) as session:
            filas = session.query(Auditoria).filter_by(tabla="documentos", id_registro=id_archivo).all()
            self.assertTrue(any(f.accion == "CREATE" for f in filas))

    def test_download_round_trips_original_bytes(self):
        with Session(self.engine) as session, session.begin():
            ts = self._user(session, "ts@example.com")
            documento = upload_documento(session, ts, tipo_registro="PERSONAS", id_registro="p1",
                                          nombre_archivo="reporte.pdf", mime_type="application/pdf",
                                          contenido=PDF_BYTES)
            id_archivo = documento.id_archivo
        with Session(self.engine) as session, session.begin():
            ts = self._user(session, "ts@example.com")
            _documento, contenido = download_documento(session, ts, id_archivo)
            self.assertEqual(contenido, PDF_BYTES)

    def test_download_denies_sensitive_document_without_sensitive_permission(self):
        with Session(self.engine) as session, session.begin():
            admin = self._user(session, "admin@example.com")
            documento = upload_documento(session, admin, tipo_registro="SEGUIMIENTOS", id_registro="s1",
                                          nombre_archivo="reporte.pdf", mime_type="application/pdf",
                                          contenido=PDF_BYTES)
            id_archivo = documento.id_archivo
        with Session(self.engine) as session, session.begin():
            ts = self._user(session, "ts@example.com")
            with self.assertRaises(AppError) as ctx:
                download_documento(session, ts, id_archivo)
            self.assertEqual(ctx.exception.code, "SENSITIVE_FORBIDDEN")
        with Session(self.engine) as session, session.begin():
            admin = self._user(session, "admin@example.com")
            _documento, contenido = download_documento(session, admin, id_archivo)
            self.assertEqual(contenido, PDF_BYTES)

    def test_download_of_non_sensitive_case_document_allowed_without_sensitive_permission(self):
        with Session(self.engine) as session, session.begin():
            admin = self._user(session, "admin@example.com")
            documento = upload_documento(session, admin, tipo_registro="CASOS", id_registro="c2",
                                          nombre_archivo="reporte.pdf", mime_type="application/pdf",
                                          contenido=PDF_BYTES)
            id_archivo = documento.id_archivo
        with Session(self.engine) as session, session.begin():
            ts = self._user(session, "ts@example.com")
            _documento, contenido = download_documento(session, ts, id_archivo)
            self.assertEqual(contenido, PDF_BYTES)

    def test_list_documentos_filters_by_record_and_excludes_deleted(self):
        with Session(self.engine) as session, session.begin():
            ts = self._user(session, "ts@example.com")
            upload_documento(session, ts, tipo_registro="PERSONAS", id_registro="p1",
                              nombre_archivo="a.jpg", mime_type="image/jpeg", contenido=JPEG_BYTES)
            upload_documento(session, ts, tipo_registro="PERSONAS", id_registro="p1",
                              nombre_archivo="b.jpg", mime_type="image/jpeg", contenido=JPEG_BYTES)
        with Session(self.engine) as session, session.begin():
            ts = self._user(session, "ts@example.com")
            listado = list_documentos(session, ts, tipo_registro="PERSONAS", id_registro="p1")
            self.assertEqual(len(listado), 2)

    def test_soft_delete_requires_delete_permission(self):
        # ROLE_TRABAJADOR_SOCIAL no tiene DOCUMENTOS:delete en el seed.
        with Session(self.engine) as session, session.begin():
            ts = self._user(session, "ts@example.com")
            documento = upload_documento(session, ts, tipo_registro="PERSONAS", id_registro="p1",
                                          nombre_archivo="a.jpg", mime_type="image/jpeg", contenido=JPEG_BYTES)
            id_archivo, version = documento.id_archivo, documento.version
        with Session(self.engine) as session, session.begin():
            ts = self._user(session, "ts@example.com")
            with self.assertRaises(AppError) as ctx:
                soft_delete_documento(session, ts, id_archivo, expected_version=version, motivo="Duplicado")
            self.assertEqual(ctx.exception.code, "FORBIDDEN")

    def test_soft_delete_requires_reason_and_expected_version(self):
        with Session(self.engine) as session, session.begin():
            admin = self._user(session, "admin@example.com")
            documento = upload_documento(session, admin, tipo_registro="PERSONAS", id_registro="p1",
                                          nombre_archivo="a.jpg", mime_type="image/jpeg", contenido=JPEG_BYTES)
            id_archivo, version = documento.id_archivo, documento.version
        with Session(self.engine) as session, session.begin():
            admin = self._user(session, "admin@example.com")
            with self.assertRaises(AppError) as ctx:
                soft_delete_documento(session, admin, id_archivo, expected_version=None, motivo="Duplicado")
            self.assertEqual(ctx.exception.code, "EXPECTED_VERSION_REQUIRED")
        with Session(self.engine) as session, session.begin():
            admin = self._user(session, "admin@example.com")
            with self.assertRaises(AppError) as ctx:
                soft_delete_documento(session, admin, id_archivo, expected_version=version, motivo="")
            self.assertEqual(ctx.exception.code, "DELETE_REASON_REQUIRED")
        with Session(self.engine) as session, session.begin():
            admin = self._user(session, "admin@example.com")
            soft_delete_documento(session, admin, id_archivo, expected_version=version, motivo="Duplicado")
        with Session(self.engine) as session, session.begin():
            ts = self._user(session, "ts@example.com")
            listado = list_documentos(session, ts, tipo_registro="PERSONAS", id_registro="p1")
            self.assertEqual(listado, [])


if __name__ == "__main__":
    unittest.main()
