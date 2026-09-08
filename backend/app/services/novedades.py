from app.models import Novedad
from app.services.simple_entities import EntityService

novedades = EntityService(
    model=Novedad,
    tabla="novedades",
    id_field="id_novedad",
    modulo="NOVEDADES",
    campos=(
        "id_persona", "fecha", "hora", "responsable", "fuente", "tipo", "subtipo", "area", "turno", "lugar",
        "descripcion", "impacto", "prioridad", "accion_inmediata", "genera_atencion",
        "genera_caso", "estado", "evidencias",
    ),
)
