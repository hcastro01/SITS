from app.models import HallazgoRecorrido
from app.services.simple_entities import EntityService

# id_recorrido es obligatorio en la BD (FK not null); id_novedad/id_caso son opcionales.
# Pendiente: bloquear el cambio de id_recorrido en update() (PARENT_CHANGE_NOT_ALLOWED en
# el legacy, CaseService.gs:81) — no implementado en este incremento.
hallazgos_recorrido = EntityService(
    model=HallazgoRecorrido,
    tabla="hallazgos_recorrido",
    id_field="id_hallazgo",
    modulo="RECORRIDOS",
    campos=(
        "id_recorrido", "tipo_hallazgo", "categoria", "subcategoria", "area", "descripcion",
        "prioridad", "accion", "genera_novedad", "id_novedad", "genera_caso", "id_caso", "estado",
    ),
)
