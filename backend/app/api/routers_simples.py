"""Instancia los routers de las entidades que usan la fábrica EntityService."""

from app.api.simple_entity_router import build_router
from app.services.hallazgos_recorrido import hallazgos_recorrido
from app.services.novedades import novedades
from app.services.personas import personas
from app.services.recorridos import recorridos

novedades_router = build_router(novedades, "/api/v1/novedades", "Novedades")
recorridos_router = build_router(recorridos, "/api/v1/recorridos", "Recorridos")
hallazgos_recorrido_router = build_router(hallazgos_recorrido, "/api/v1/hallazgos", "Hallazgos de Recorrido")
personas_router = build_router(personas, "/api/v1/personas", "Personas")
