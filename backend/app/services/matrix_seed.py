"""Siembra la matriz institucional real: catálogos, el formulario "Ficha integral de
gestión de casos" y sus preguntas/opciones.

Fuente: exportación real de producción ("Sistema Integral de Gestion de Trabajo Social -
Base de Datos.xlsx", provista por el usuario), preservando los IDs originales
(MIGRACION_FASE_1.md §8: "preservar IDs"). La extracción (ver historial de esta sesión)
excluyó explícitamente, con evidencia de los propios datos y no por inferencia:

- 2 preguntas huérfanas ("Como esta" / "Como esta (copia)") cuyo IdFormulario no
  corresponde a ningún formulario existente en la hoja Formularios.
- Todas las filas de Preguntas/OpcionesPregunta/Catalogos con Activo=False o
  Eliminado=True (duplicados y versiones reemplazadas).
- 21.803 filas de OpcionesPregunta ligadas a una pregunta desactivada ("Seleccioné los
  apellidos y nombres del colaborador"): un intento abandonado de modelar la selección
  de colaborador como una lista desplegable gigante en vez de un lookup real.

Ambigüedad NO resuelta unilateralmente: dos preguntas activas comparten `orden=9`
("Coloqué el número de cédula del colaborador" y "Apellidos y nombres del colaborador").
Se preserva tal cual viene en el origen; no se renumeró.

NIVEL_SENSIBILIDAD sigue sin sembrarse (hallazgo H2): no existe como tipo de catálogo en
esta exportación real tampoco, confirmando que nunca se usó en producción.
"""

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Catalogo, Formulario, OpcionPregunta, Pregunta

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "matriz_institucional.json"


def _cargar_datos() -> dict:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def seed_institutional_matrix(session: Session) -> None:
    datos = _cargar_datos()

    existentes_catalogo = set(session.scalars(select(Catalogo.id_catalogo)))
    for fila in datos["catalogos"]:
        if fila["id_catalogo"] not in existentes_catalogo:
            session.add(Catalogo(**fila))
    session.flush()

    if session.get(Formulario, datos["formulario"]["id_formulario"]) is None:
        session.add(Formulario(**datos["formulario"]))
    session.flush()

    existentes_pregunta = set(session.scalars(select(Pregunta.id_pregunta)))
    for fila in datos["preguntas"]:
        if fila["id_pregunta"] not in existentes_pregunta:
            session.add(Pregunta(**fila))
    session.flush()

    existentes_opcion = set(session.scalars(select(OpcionPregunta.id_opcion)))
    for fila in datos["opciones"]:
        if fila["id_opcion"] not in existentes_opcion:
            session.add(OpcionPregunta(**fila))
