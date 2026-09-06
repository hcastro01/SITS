"""Sensibilidad compartida entre Búsqueda y Documentos: un registro es sensible si es un
Caso sensible, o si referencia uno mediante `id_caso`. Único punto de esta regla para no
duplicarla (antes vivía solo dentro de app/services/search.py)."""

from sqlalchemy.orm import Session

from app.models import Caso
from app.services.casos import is_sensitive_caso


def is_sensitive_record(session: Session, registro) -> bool:
    if isinstance(registro, Caso):
        return is_sensitive_caso(session, registro.nivel_sensibilidad)
    id_caso = getattr(registro, "id_caso", None)
    if id_caso:
        caso = session.get(Caso, id_caso)
        if caso is not None:
            return is_sensitive_caso(session, caso.nivel_sensibilidad)
    return False
