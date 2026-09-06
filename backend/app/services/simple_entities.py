"""Fábrica de servicios CRUD para entidades de proceso sin hijos ni transacciones
adicionales (Novedades, Recorridos, HallazgosRecorrido, Personas): allowlist de campos
(H1), authorize(), expected_version obligatorio y soft delete con motivo — la misma forma
que Base Sistema/ProcessService.gs aplicaba de forma genérica.

Casos y Atenciones no usan esta fábrica: Casos tiene hijos y cierre transaccional propios
(app/services/casos.py); Atenciones fue el primer servicio escrito, antes de extraer este
patrón, y se conserva explícito como referencia legible de la forma que la fábrica repite.
"""

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, authorize
from app.services.audit import log_change
from app.services.records import (
    apply_restore, apply_soft_delete, check_expected_version, creation_metadata, get_active, mark_updated,
)


@dataclass(frozen=True)
class EntityService:
    model: type
    tabla: str
    id_field: str
    modulo: str
    campos: tuple[str, ...]

    def _id_column(self):
        return getattr(self.model, self.id_field)

    def _snapshot(self, record) -> dict[str, Any]:
        return {campo: getattr(record, campo) for campo in self.campos}

    def _rechazar_desconocidos(self, campos: dict) -> None:
        desconocidos = set(campos) - set(self.campos)
        if desconocidos:
            raise AppError("INVALID_FIELD", f"Campos no admitidos: {', '.join(sorted(desconocidos))}.", 422)

    def create(self, session: Session, user: AuthenticatedUser, *, motivo_auditoria: str,
               correlation_id: str, **campos):
        self._rechazar_desconocidos(campos)
        authorize(user, self.modulo, "create")
        record = self.model(**{self.id_field: str(uuid4())}, **creation_metadata(user.correo), **campos)
        session.add(record)
        session.flush()
        log_change(session, self.tabla, getattr(record, self.id_field), "CREATE", {}, self._snapshot(record),
                   user.correo, motivo_auditoria, correlation_id)
        return record

    def update(self, session: Session, user: AuthenticatedUser, id_value: str, *,
               expected_version: int | None, motivo_auditoria: str, correlation_id: str, **campos):
        self._rechazar_desconocidos(campos)
        authorize(user, self.modulo, "edit")
        record = get_active(session, self.model, id_value, self._id_column())
        check_expected_version(record, expected_version)
        before = self._snapshot(record)
        for campo, valor in campos.items():
            setattr(record, campo, valor)
        mark_updated(record, user.correo)
        log_change(session, self.tabla, id_value, "UPDATE", before, self._snapshot(record),
                   user.correo, motivo_auditoria, correlation_id)
        return record

    def soft_delete(self, session: Session, user: AuthenticatedUser, id_value: str, *,
                     expected_version: int | None, motivo: str, correlation_id: str):
        authorize(user, self.modulo, "delete")
        record = get_active(session, self.model, id_value, self._id_column())
        check_expected_version(record, expected_version)
        before = self._snapshot(record)
        apply_soft_delete(record, user.correo, motivo)  # valida el motivo antes de tocar version
        mark_updated(record, user.correo)
        log_change(session, self.tabla, id_value, "DELETE", before, self._snapshot(record),
                   user.correo, motivo, correlation_id)
        return record

    def restore(self, session: Session, user: AuthenticatedUser, id_value: str, *, correlation_id: str):
        authorize(user, self.modulo, "delete")
        record = get_active(session, self.model, id_value, self._id_column(), include_deleted=True)
        if not record.eliminado:
            raise AppError("NOT_FOUND", "Registro eliminado no encontrado.", 404)
        before = self._snapshot(record)
        apply_restore(record)
        record.version += 1
        log_change(session, self.tabla, id_value, "RESTORE", before, self._snapshot(record),
                   user.correo, "Restauración", correlation_id)
        return record
