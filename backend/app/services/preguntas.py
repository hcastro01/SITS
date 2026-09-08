from app.models import Pregunta
from app.services.simple_entities import EntityService

# id_formulario es obligatorio en la BD (FK not null) y va en campos para poder fijarlo en
# create(). Pendiente (como en hallazgos_recorrido.py): bloquear su reasignación en
# update() — equivalente a PARENT_CHANGE_NOT_ALLOWED del legacy para hijos de caso — no
# implementado en este incremento.
preguntas = EntityService(
    model=Pregunta,
    tabla="preguntas",
    id_field="id_pregunta",
    modulo="FORMULARIOS",
    campos=(
        "id_formulario", "id_seccion", "etiqueta", "descripcion", "tipo", "obligatoria", "orden", "categoria",
        "subcategoria", "valor_predeterminado", "texto_ayuda", "visible", "solo_lectura",
        "longitud_maxima", "validacion", "sensibilidad", "condicion_visibilidad",
        "campo_dependiente", "valor_dependiente", "formula", "configuracion", "fuente_datos", "mapping",
    ),
)
