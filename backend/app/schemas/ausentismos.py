from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class AusentismoFilaAnalizada(BaseModel):
    model_config = ConfigDict(frozen=True)

    fila: int
    cedula: str | None = None
    persona_id: str | None = None
    fecha_inicio: str | None = None
    fecha_fin: str | None = None
    tipo_ausentismo: str | None = None
    motivo: str | None = None
    observacion: str | None = None
    estado: Literal["VALIDA", "DUPLICADA", "ERROR"]
    errores: tuple[str, ...] = ()


class AusentismoAnalisis(BaseModel):
    model_config = ConfigDict(frozen=True)

    encabezados: tuple[str, ...]
    total_filas: int
    filas_validas: int
    filas_duplicadas: int
    filas_con_error: int
    puede_confirmarse: bool
    filas: tuple[AusentismoFilaAnalizada, ...]


class AusentismoTablaEntrada(BaseModel):
    """Entrada tabular del futuro lector XLSX; no expone aún un endpoint."""

    encabezados: list[Any]
    filas: list[list[Any]]


class LoteImportacionAusentismoRespuesta(BaseModel):
    model_config = ConfigDict(frozen=True)

    id_lote: str
    nombre_archivo: str
    usuario_id: str
    estado: str
    total_filas: int
    filas_validas: int
    filas_con_error: int
    filas_duplicadas: int
    filas_importadas: int
    fecha_creacion: str | None
    fecha_actualizacion: str | None
    version: int


class ErrorImportacionAusentismoRespuesta(BaseModel):
    model_config = ConfigDict(frozen=True)

    id_error: str
    numero_fila: int
    codigo: str
    mensaje: str
    datos_fila: str | None
