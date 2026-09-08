"""Router de Búsqueda y Exportación."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.permissions import AuthenticatedUser
from app.services.export import export_search_results
from app.services.form_integrations import person_records, response_by_code
from app.services.search import search

router = APIRouter(prefix="/api/v1", tags=["Búsqueda"])


@router.get("/busqueda")
def buscar(
    db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user),
    q: str = "", tablas: str | None = None, pagina: int = Query(1, ge=1), tamano_pagina: int = Query(20, le=100),
):
    lista_tablas = tablas.split(",") if tablas else None
    return search(db, user, tablas=lista_tablas, q=q, pagina=pagina, tamano_pagina=tamano_pagina)


@router.get("/busqueda/personas/{id_persona}/registros")
def registros_persona(
    id_persona: str, modulo: str | None = None, estado: str | None = None,
    pagina: int = Query(1, ge=1), tamano_pagina: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user),
):
    return person_records(
        db, user, id_persona, module=modulo, state=estado,
        page=pagina, page_size=tamano_pagina,
    )


@router.get("/busqueda/codigo/{codigo_respuesta}")
def buscar_codigo(
    codigo_respuesta: str, db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    return response_by_code(db, user, codigo_respuesta)


@router.post("/exportaciones")
def exportar(payload: dict, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    csv_text, truncado = export_search_results(db, user, tablas=payload.get("tablas"), q=payload.get("q", ""))
    return PlainTextResponse(
        csv_text, media_type="text/csv",
        headers={"X-Truncated": str(truncado), "Content-Disposition": "attachment; filename=exportacion.csv"},
    )
