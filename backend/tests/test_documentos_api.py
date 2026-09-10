import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.api.documentos import cargar
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


if __name__ == "__main__":
    unittest.main()
