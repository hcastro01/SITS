import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.api.documentos import _serialize, cargar, descargar
from app.core.errors import AppError
from app.services.documentos import MAX_FILE_BYTES


class BoundedUpload:
    filename = "archivo.pdf"
    content_type = "application/pdf"

    def __init__(self) -> None:
        self.requested_size: int | None = None

    async def read(self, size: int = -1) -> bytes:
        self.requested_size = size
        return b"%PDF-" + b"x" * 10


class DocumentosApiTests(unittest.TestCase):
    def test_upload_reads_only_the_maximum_size_plus_one_byte(self):
        upload = BoundedUpload()
        with patch("app.api.documentos.upload_documento", side_effect=AppError("STOP", "stop", 422)):
            with self.assertRaises(AppError):
                asyncio.run(cargar(
                    tipo_registro="CASOS", id_registro="case-1", archivo=upload,
                    categoria_documento=None, request=SimpleNamespace(state=SimpleNamespace(correlation_id="test")),
                    db=None, user=None,
                ))
        self.assertEqual(upload.requested_size, MAX_FILE_BYTES + 1)

    def test_metadata_serialization_never_includes_blob_content(self):
        documento = SimpleNamespace(
            id_archivo="d1", tipo_registro="PERSONAS", id_registro="p1", nombre_archivo="foto.jpg",
            mime_type="image/jpeg", extension="jpg", tamano_bytes=3, tamano_comprimido_bytes=11,
            contenido_comprimido=b"never serialize this", sha256="hash", categoria_documento=None,
            version=1, activo=True, eliminado=False, fecha_creacion="2026-09-16", creado_por="ts@example.com",
        )
        metadata = _serialize(documento)
        self.assertNotIn("contenido_comprimido", metadata)
        self.assertNotIn(b"never serialize this", metadata.values())

    def test_download_returns_private_security_headers_and_safe_filename(self):
        documento = SimpleNamespace(nombre_archivo="foto segura.jpg", mime_type="image/jpeg")
        with patch("app.api.documentos.download_documento", return_value=(documento, b"bytes")):
            response = descargar("d1", db=None, user=None)
        self.assertEqual(response.body, b"bytes")
        self.assertEqual(response.headers["cache-control"], "private, no-store")
        self.assertEqual(response.headers["pragma"], "no-cache")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertIn("attachment", response.headers["content-disposition"])


if __name__ == "__main__":
    unittest.main()
