"""Router de Búsqueda y Exportación."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.permissions import AuthenticatedUser
from app.services.export import export_search_results
from app.services.search import search

router = APIRouter(prefix="/api/v1", tags=["Búsqueda"])


@router.get("/busqueda")
def buscar(
    db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user),
    q: str = "", tablas: str | None = None, pagina: int = Query(1, ge=1), tamano_pagina: int = Query(20, le=100),
):
    lista_tablas = tablas.split(",") if tablas else None
    return search(db, user, tablas=lista_tablas, q=q, pagina=pagina, tamano_pagina=tamano_pagina)


@router.post("/exportaciones")
def exportar(payload: dict, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    csv_text, truncado = export_search_results(db, user, tablas=payload.get("tablas"), q=payload.get("q", ""))
    return PlainTextResponse(
        csv_text, media_type="text/csv",
        headers={"X-Truncated": str(truncado), "Content-Disposition": "attachment; filename=exportacion.csv"},
    )
