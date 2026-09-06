from app.models import OpcionPregunta
from app.services.simple_entities import EntityService

opciones_pregunta = EntityService(
    model=OpcionPregunta,
    tabla="opciones_pregunta",
    id_field="id_opcion",
    modulo="FORMULARIOS",
    campos=("id_pregunta", "valor", "etiqueta", "orden", "id_catalogo", "id_opcion_padre"),
)
