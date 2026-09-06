from app.models import Persona
from app.services.simple_entities import EntityService

personas = EntityService(
    model=Persona,
    tabla="personas",
    id_field="id_persona",
    modulo="PERSONAS",
    campos=(
        "codigo_empleado", "cedula", "nombre", "cargo", "area", "departamento", "centro",
        "sub_centro", "turno", "estado_laboral",
    ),
)
