"""Exportación CSV de resultados de búsqueda. Neutraliza inyección de fórmulas igual que
Base Sistema/Utils.gs:107-111, pero corrige la cobertura que la auditoría encontró
solo-posición-0: aquí se recorta (`strip`) el valor antes de comprobar el primer carácter,
así que un valor con espacio inicial (" =WEBSERVICE(...)") también queda neutralizado.
"""

import csv
import io
import re

from sqlalchemy.orm import Session

from app.core.permissions import AuthenticatedUser, authorize
from app.services.search import search

_FORMULA_PREFIX = re.compile(r"^[=+\-@\t\r]")

HEADERS = ("tabla", "id", "fecha", "sensible", "restringido")


def csv_escape(value) -> str:
    text = "" if value is None else str(value)
    if _FORMULA_PREFIX.match(text.strip()):
        text = "'" + text
    return text


def export_csv(headers: tuple[str, ...], rows: list[list]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(headers)
    for row in rows:
        writer.writerow([csv_escape(valor) for valor in row])
    return buffer.getvalue()


def export_search_results(
    session: Session, user: AuthenticatedUser, *,
    tablas: list[str] | None = None, q: str = "", filtros: dict | None = None,
) -> tuple[str, bool]:
    """Equivalente a Base Sistema/ExportService.gs (exportResults). Devuelve (csv, truncado)."""
    # REPORTES:export se exige aquí y no en search(), que solo pide BUSQUEDA:read —
    # exportar es un permiso distinto de buscar, igual que en el legacy.
    authorize(user, "REPORTES", "export")
    resultado = search(session, user, tablas=tablas, q=q, filtros=filtros, modo_exportacion=True)
    filas = [
        [item["tabla"], item["id"], item["fecha"], item["sensible"], item["restringido"]]
        for item in resultado["items"]
    ]
    return export_csv(HEADERS, filas), resultado["truncado"]
