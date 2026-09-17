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


class AusentismoOperativoRespuesta(BaseModel):
    """Contrato mínimo para la consulta operativa; no expone datos médicos adicionales."""

    model_config = ConfigDict(frozen=True)

    id_ausentismo: str
    persona_id: str
    persona: str
    cedula: str | None
    area: str | None
    fecha_inicio: str
    fecha_fin: str
    tipo_ausentismo: str
    motivo: str
    observacion: str | None
    fecha_registro: str | None
    registrado_por_id: str | None
    registrado_por: str | None
    origen: str | None
    lote_id: str | None
    lote_nombre_archivo: str | None


class AusentismoOperativoPaginado(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: tuple[AusentismoOperativoRespuesta, ...]
    total: int
    limite: int
    offset: int
