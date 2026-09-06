"""Auditoría transaccional. Equivalente a Base Sistema/AuditService.gs (TSAudit).

A diferencia del legacy —donde la fila de auditoría se escribe después de la mutación, sin
relación ACID entre ambas (Base Sistema/DataService.gs:214 vs CaseService.gs:55-56;
MIGRACION_FASE_1.md discrepancia D9)— aquí la mutación y la auditoría comparten la misma
sesión y transacción de SQLAlchemy: si `log_change` falla, la mutación también se revierte.
"""

import re
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import Auditoria

# Las 8 acciones de Base Sistema/AuditService.gs:2.
ACTIONS = ("CREATE", "UPDATE", "DELETE", "RESTORE", "VIEW_SENSITIVE", "DOWNLOAD_FILE", "IMPORT", "LOGIN")

# Adaptación a snake_case de los patrones genéricos de Base Sistema/AuditService.gs:3,5.
# Las reglas específicas por tabla (DetalleCasosSensibles, RespuestasFormulario.Valor*,
# Documentos) se añaden en la Fase C, cuando esas tablas existan en el esquema nuevo.
_SENSITIVE_FIELD_PATTERN = re.compile(
    r"cedula|sensible|diagnostico|antecedente|notaprivada|descripcionsensible", re.IGNORECASE
)
_ALWAYS_VISIBLE_FIELD_PATTERN = re.compile(
    r"^(id_[a-z_]+|codigo_caso|estado|estado_caso|prioridad|nivel_sensibilidad|fecha[a-z_]*|activo|eliminado|version)$",
    re.IGNORECASE,
)
REDACTED_PLACEHOLDER = "[VALOR SENSIBLE MODIFICADO]"


def redact(field: str, value, sensitive_record: bool = False) -> str | None:
    if value is None:
        return None
    if _SENSITIVE_FIELD_PATTERN.search(field) or (sensitive_record and not _ALWAYS_VISIBLE_FIELD_PATTERN.match(field)):
        return REDACTED_PLACEHOLDER
    return str(value)


def log_change(
    session: Session,
    tabla: str,
    id_registro: str,
    accion: str,
    before: dict,
    after: dict,
    usuario: str,
    motivo: str = "",
    correlation_id: str = "",
    sensitive_record: bool = False,
) -> list[Auditoria]:
    if accion not in ACTIONS:
        raise ValueError(f"Acción de auditoría inválida: {accion!r}")
    fecha_hora = datetime.now(UTC).isoformat()
    fields = dict.fromkeys([*before.keys(), *after.keys()])
    rows = [
        Auditoria(
            id_auditoria=str(uuid4()), tabla=tabla, id_registro=id_registro, accion=accion,
            usuario=usuario, fecha_hora=fecha_hora, campo=field,
            valor_anterior=redact(field, before.get(field), sensitive_record),
            valor_nuevo=redact(field, after.get(field), sensitive_record),
            motivo=motivo, correlation_id=correlation_id,
        )
        for field in fields
        if not (accion == "UPDATE" and before.get(field) == after.get(field))
    ]
    if not rows:
        rows.append(Auditoria(
            id_auditoria=str(uuid4()), tabla=tabla, id_registro=id_registro, accion=accion,
            usuario=usuario, fecha_hora=fecha_hora, campo="*",
            valor_anterior=None, valor_nuevo=None, motivo=motivo, correlation_id=correlation_id,
        ))
    session.add_all(rows)
    return rows
