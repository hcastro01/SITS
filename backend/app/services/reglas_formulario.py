from app.models import ReglaFormulario
from app.services.simple_entities import EntityService

reglas_formulario = EntityService(
    model=ReglaFormulario,
    tabla="reglas_formulario",
    id_field="id_regla",
    modulo="FORMULARIOS",
    campos=(
        "id_formulario", "id_pregunta_origen", "operador", "valor_comparacion",
        "id_pregunta_destino", "id_seccion_destino", "accion", "grupo", "mensaje", "orden",
    ),
)
