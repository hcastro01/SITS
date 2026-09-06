from app.models import Recorrido
from app.services.simple_entities import EntityService

recorridos = EntityService(
    model=Recorrido,
    tabla="recorridos",
    id_field="id_recorrido",
    modulo="RECORRIDOS",
    campos=(
        "fecha", "hora_inicio", "hora_fin", "responsable", "planta", "area", "turno",
        "objetivo", "observaciones", "personas_contactadas", "novedades_detectadas",
        "acciones", "evidencias",
    ),
)
