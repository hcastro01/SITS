from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RiesgoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    persona_id: str
    fecha_apertura: str
    responsable: str | None = None
    estado_caso: Literal["ABIERTO", "EN_SEGUIMIENTO", "CERRADO"] = "ABIERTO"
    prioridad: str | None = None
    resultado: str | None = Field(default=None, min_length=1)


class RiesgoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int
    responsable: str | None = None
    estado_caso: Literal["ABIERTO", "EN_SEGUIMIENTO", "CERRADO"] | None = None
    prioridad: str | None = None
    resultado: str | None = Field(default=None, min_length=1)


class RiesgoSeguimiento(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fecha: str
    descripcion: str = Field(min_length=1)
    responsable: str | None = None
    resultado: str | None = None
    proxima_accion: str | None = None
    fecha_proxima_accion: str | None = None
    estado: str | None = None


class RiesgoCierre(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int
    fecha_cierre_caso: str | None = None
    responsable: str | None = None
    motivo_cierre: str = Field(min_length=1)
    resultado_final: str | None = None
