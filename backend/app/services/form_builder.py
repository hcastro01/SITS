"""Lectura y guardado transaccional del constructor dinámico de formularios."""

import json
from collections import defaultdict
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import AuthenticatedUser, authorize
from app.core.time import utc_now_iso
from app.models import (
    EnvioFormulario, Formulario, FormularioDestino, FormularioVersion, OpcionPregunta,
    Pregunta, ReglaFormulario, SeccionFormulario,
)
from app.services.audit import log_change
from app.services.records import check_expected_version, creation_metadata, get_active, mark_updated

MODULE = "FORMULARIOS"
DESTINOS_VALIDOS = ("GENERAL", "CASOS", "ATENCIONES", "NOVEDADES", "RECORRIDOS", "PERSONAS")
TIPOS_PREGUNTA = (
    "TEXTO_CORTO", "TEXTO_LARGO", "NUMERO_ENTERO", "NUMERO_DECIMAL", "MONEDA",
    "PORCENTAJE", "EMAIL", "TELEFONO", "DOCUMENTO", "FECHA", "HORA", "FECHA_HORA",
    "SI_NO", "SELECCION_UNICA", "LISTA_DESPLEGABLE", "SELECCION_MULTIPLE", "CASILLAS",
    "ESCALA", "CALIFICACION", "BUSQUEDA", "ARCHIVO", "FOTOGRAFIA", "TITULO", "INFORMATIVO",
    "CUADRICULA_UNICA", "CUADRICULA_MULTIPLE", "NUMERO",
)
TIPOS_CON_OPCIONES = frozenset({
    "SELECCION_UNICA", "LISTA_DESPLEGABLE", "SELECCION_MULTIPLE", "CASILLAS",
    "CUADRICULA_UNICA", "CUADRICULA_MULTIPLE",
})
OPERADORES = frozenset({"EQ", "NE", "CONTAINS", "NOT_CONTAINS", "GT", "GTE", "LT", "LTE", "EMPTY", "NOT_EMPTY", "INCLUDES", "NOT_INCLUDES"})
ACCIONES_REGLA = frozenset({"MOSTRAR", "OCULTAR", "OBLIGATORIA", "OPCIONAL", "MOSTRAR_SECCION", "OCULTAR_SECCION"})


def json_value(value, default):
    if value in (None, ""):
        return default
    if isinstance(value, type(default)):
        return value
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, type(default)) else default
    except (TypeError, ValueError):
        return default


def dump_json(value) -> str | None:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")) if value not in (None, {}, []) else None


def serialize_section(record: SeccionFormulario) -> dict:
    return {"id_seccion": record.id_seccion, "id_formulario": record.id_formulario,
            "titulo": record.titulo, "descripcion": record.descripcion, "orden": record.orden,
            "version": record.version}


def serialize_option(record: OpcionPregunta) -> dict:
    return {"id_opcion": record.id_opcion, "id_pregunta": record.id_pregunta,
            "valor": record.valor, "etiqueta": record.etiqueta, "orden": record.orden,
            "id_catalogo": record.id_catalogo, "id_opcion_padre": record.id_opcion_padre,
            "version": record.version}


def serialize_rule(record: ReglaFormulario) -> dict:
    return {"id_regla": record.id_regla, "id_formulario": record.id_formulario,
            "id_pregunta_origen": record.id_pregunta_origen, "operador": record.operador,
            "valor_comparacion": record.valor_comparacion,
            "id_pregunta_destino": record.id_pregunta_destino,
            "id_seccion_destino": record.id_seccion_destino, "accion": record.accion,
            "grupo": record.grupo or "TODAS", "mensaje": record.mensaje,
            "orden": record.orden, "version": record.version}


def serialize_question(record: Pregunta, options: list[OpcionPregunta] | None = None) -> dict:
    return {
        "id_pregunta": record.id_pregunta, "id_formulario": record.id_formulario,
        "id_seccion": record.id_seccion, "etiqueta": record.etiqueta,
        "descripcion": record.descripcion, "tipo": record.tipo or "TEXTO_CORTO",
        "obligatoria": record.obligatoria, "orden": record.orden,
        "categoria": record.categoria, "subcategoria": record.subcategoria,
        "valor_predeterminado": record.valor_predeterminado, "texto_ayuda": record.texto_ayuda,
        "visible": record.visible, "solo_lectura": record.solo_lectura,
        "longitud_maxima": record.longitud_maxima,
        "validacion": json_value(record.validacion, {}), "sensibilidad": record.sensibilidad,
        "condicion_visibilidad": json_value(record.condicion_visibilidad, {}),
        "campo_dependiente": record.campo_dependiente, "valor_dependiente": record.valor_dependiente,
        "configuracion": json_value(record.configuracion, {}), "fuente_datos": record.fuente_datos,
        "mapping": json_value(record.mapping, {}), "version": record.version,
        "opciones": [serialize_option(o) for o in (options or [])],
    }


def serialize_form(record: Formulario, *, destinations: list[str] | None = None,
                   question_count: int = 0, response_count: int = 0) -> dict:
    return {
        "id_formulario": record.id_formulario, "nombre": record.nombre,
        "descripcion": record.descripcion, "proceso": record.proceso,
        "responsable": record.responsable, "estado": record.estado,
        "fecha_publicacion": record.fecha_publicacion,
        "permite_multiples_respuestas": record.permite_multiples_respuestas,
        "version_publicada": record.version_publicada, "version": record.version,
        "activo": record.activo, "eliminado": record.eliminado,
        "fecha_actualizacion": record.fecha_actualizacion or record.fecha_creacion,
        "actualizado_por": record.actualizado_por or record.creado_por,
        "destinos": destinations or [], "total_preguntas": question_count,
        "total_respuestas": response_count,
    }


def get_definition(session: Session, id_formulario: str) -> dict:
    form = session.get(Formulario, id_formulario)
    if form is None or form.eliminado:
        raise AppError("FORM_NOT_FOUND", "Formulario no encontrado.", 404)
    destinations = list(session.scalars(select(FormularioDestino.modulo).where(
        FormularioDestino.id_formulario == id_formulario,
        FormularioDestino.eliminado.is_(False), FormularioDestino.activo.is_(True),
    ).order_by(FormularioDestino.modulo)))
    sections = list(session.scalars(select(SeccionFormulario).where(
        SeccionFormulario.id_formulario == id_formulario,
        SeccionFormulario.eliminado.is_(False),
    ).order_by(SeccionFormulario.orden)))
    questions = list(session.scalars(select(Pregunta).where(
        Pregunta.id_formulario == id_formulario, Pregunta.eliminado.is_(False),
    ).order_by(Pregunta.orden)))
    question_ids = [q.id_pregunta for q in questions]
    options_by_question: dict[str, list[OpcionPregunta]] = defaultdict(list)
    if question_ids:
        for option in session.scalars(select(OpcionPregunta).where(
            OpcionPregunta.id_pregunta.in_(question_ids), OpcionPregunta.eliminado.is_(False),
        ).order_by(OpcionPregunta.orden)):
            options_by_question[option.id_pregunta].append(option)
    rules = list(session.scalars(select(ReglaFormulario).where(
        ReglaFormulario.id_formulario == id_formulario,
        ReglaFormulario.eliminado.is_(False),
    ).order_by(ReglaFormulario.orden)))
    response_count = session.scalar(select(func.count()).select_from(EnvioFormulario).where(
        EnvioFormulario.id_formulario == id_formulario,
        EnvioFormulario.eliminado.is_(False),
    )) or 0
    return {
        **serialize_form(form, destinations=destinations, question_count=len(questions), response_count=response_count),
        "secciones": [serialize_section(s) for s in sections],
        "preguntas": [serialize_question(q, options_by_question[q.id_pregunta]) for q in questions],
        "reglas": [serialize_rule(r) for r in rules],
    }


def list_forms(session: Session) -> list[dict]:
    forms = list(session.scalars(select(Formulario).where(Formulario.eliminado.is_(False)).order_by(
        Formulario.fecha_actualizacion.desc(), Formulario.nombre,
    )))
    return [get_definition(session, form.id_formulario) for form in forms]


def sync_destinations(session: Session, id_formulario: str, destinations: list[str], user_email: str) -> None:
    normalized = {str(value).strip().upper() for value in destinations}
    invalid = normalized - set(DESTINOS_VALIDOS)
    if invalid:
        raise AppError("INVALID_FORM_DESTINATION", f"Destino no permitido: {', '.join(sorted(invalid))}.", 422)
    existing = {row.modulo: row for row in session.scalars(select(FormularioDestino).where(
        FormularioDestino.id_formulario == id_formulario,
    ))}
    for module, row in existing.items():
        should_be_active = module in normalized
        if row.activo != should_be_active or row.eliminado == should_be_active:
            row.activo = should_be_active
            row.eliminado = not should_be_active
            mark_updated(row, user_email)
    for module in normalized - set(existing):
        session.add(FormularioDestino(id_destino=str(uuid4()), id_formulario=id_formulario,
                                      modulo=module, **creation_metadata(user_email)))


def _upsert(session: Session, model, id_field: str, id_value: str, id_formulario: str,
            user_email: str, fields: dict):
    record = session.get(model, id_value)
    if record is not None and getattr(record, "id_formulario") != id_formulario:
        raise AppError("INVALID_CHILD", "El elemento pertenece a otro formulario.", 422)
    if record is None:
        record = model(**{id_field: id_value, "id_formulario": id_formulario},
                       **creation_metadata(user_email), **fields)
        session.add(record)
    else:
        for key, value in fields.items():
            setattr(record, key, value)
        record.activo = True
        record.eliminado = False
        mark_updated(record, user_email)
    return record


def _retire_omitted(records, keep: set[str], id_field: str, user_email: str) -> None:
    for record in records:
        if getattr(record, id_field) not in keep and not record.eliminado:
            record.activo = False
            record.eliminado = True
            record.fecha_eliminacion = utc_now_iso()
            record.usuario_eliminacion = user_email
            record.motivo_eliminacion = "Retirado desde el constructor"
            mark_updated(record, user_email)


def save_definition(session: Session, user: AuthenticatedUser, id_formulario: str,
                    payload: dict, *, correlation_id: str) -> dict:
    authorize(user, MODULE, "edit")
    form = get_active(session, Formulario, id_formulario, Formulario.id_formulario)
    check_expected_version(form, payload.get("expected_version"))
    before = serialize_form(form)
    for field in ("nombre", "descripcion", "responsable", "permite_multiples_respuestas"):
        if field in payload:
            setattr(form, field, payload[field])
    if not str(form.nombre or "").strip():
        raise AppError("FORM_NAME_REQUIRED", "El nombre del formulario es obligatorio.", 422)
    sync_destinations(session, id_formulario, payload.get("destinos", []), user.correo)

    section_payloads = payload.get("secciones", [])
    question_payloads = payload.get("preguntas", [])
    rule_payloads = payload.get("reglas", [])
    if len(section_payloads) > 50 or len(question_payloads) > 300 or len(rule_payloads) > 500:
        raise AppError("FORM_TOO_LARGE", "El formulario supera los límites permitidos.", 422)

    current_sections = list(session.scalars(select(SeccionFormulario).where(SeccionFormulario.id_formulario == id_formulario)))
    section_ids: set[str] = set()
    for index, data in enumerate(section_payloads):
        section_id = str(data.get("id_seccion") or uuid4())
        title = str(data.get("titulo") or "").strip()
        if not title:
            raise AppError("SECTION_TITLE_REQUIRED", "Cada sección debe tener título.", 422)
        _upsert(session, SeccionFormulario, "id_seccion", section_id, id_formulario, user.correo,
                {"titulo": title, "descripcion": data.get("descripcion"), "orden": index})
        section_ids.add(section_id)
    _retire_omitted(current_sections, section_ids, "id_seccion", user.correo)
    session.flush()

    current_questions = list(session.scalars(select(Pregunta).where(Pregunta.id_formulario == id_formulario)))
    question_ids: set[str] = set()
    keep_options: set[str] = set()
    for index, data in enumerate(question_payloads):
        question_id = str(data.get("id_pregunta") or uuid4())
        question_type = str(data.get("tipo") or "TEXTO_CORTO").strip().upper()
        if question_type not in TIPOS_PREGUNTA:
            raise AppError("INVALID_QUESTION_TYPE", f"Tipo de pregunta no permitido: {question_type}.", 422)
        label = str(data.get("etiqueta") or "").strip()
        if not label:
            raise AppError("QUESTION_LABEL_REQUIRED", "Cada pregunta debe tener título.", 422)
        section_id = data.get("id_seccion") or None
        if section_id and section_id not in section_ids:
            raise AppError("INVALID_SECTION", "La sección de una pregunta no pertenece al formulario.", 422)
        fields = {
            "id_seccion": section_id, "etiqueta": label, "descripcion": data.get("descripcion"),
            "tipo": question_type, "obligatoria": bool(data.get("obligatoria", False)),
            "orden": index, "categoria": data.get("categoria"), "subcategoria": data.get("subcategoria"),
            "valor_predeterminado": data.get("valor_predeterminado"), "texto_ayuda": data.get("texto_ayuda"),
            "visible": bool(data.get("visible", True)), "solo_lectura": bool(data.get("solo_lectura", False)),
            "longitud_maxima": data.get("longitud_maxima"), "validacion": dump_json(data.get("validacion", {})),
            "sensibilidad": data.get("sensibilidad"), "condicion_visibilidad": dump_json(data.get("condicion_visibilidad", {})),
            "campo_dependiente": None, "valor_dependiente": None, "formula": None,
            "configuracion": dump_json(data.get("configuracion", {})), "fuente_datos": data.get("fuente_datos"),
            "mapping": dump_json(data.get("mapping", {})),
        }
        _upsert(session, Pregunta, "id_pregunta", question_id, id_formulario, user.correo, fields)
        question_ids.add(question_id)
        session.flush()
        options = data.get("opciones", [])
        if question_type in TIPOS_CON_OPCIONES and not options:
            raise AppError("QUESTION_OPTIONS_REQUIRED", f"La pregunta «{label}» necesita opciones.", 422)
        for option_index, option_data in enumerate(options):
            option_id = str(option_data.get("id_opcion") or uuid4())
            option = session.get(OpcionPregunta, option_id)
            if option is not None and option.id_pregunta != question_id:
                raise AppError("INVALID_OPTION", "La opción pertenece a otra pregunta.", 422)
            value = str(option_data.get("valor") or option_data.get("etiqueta") or "").strip()
            option_label = str(option_data.get("etiqueta") or value).strip()
            if not value or not option_label:
                raise AppError("INVALID_OPTION", "Las opciones no pueden estar vacías.", 422)
            option_fields = {"id_pregunta": question_id, "valor": value, "etiqueta": option_label,
                             "orden": option_index, "id_catalogo": option_data.get("id_catalogo"),
                             "id_opcion_padre": option_data.get("id_opcion_padre")}
            if option is None:
                option = OpcionPregunta(id_opcion=option_id, **creation_metadata(user.correo), **option_fields)
                session.add(option)
            else:
                for key, value in option_fields.items(): setattr(option, key, value)
                option.activo = True
                option.eliminado = False
                mark_updated(option, user.correo)
            keep_options.add(option_id)
    _retire_omitted(current_questions, question_ids, "id_pregunta", user.correo)
    current_options = list(session.scalars(select(OpcionPregunta).join(
        Pregunta, OpcionPregunta.id_pregunta == Pregunta.id_pregunta,
    ).where(Pregunta.id_formulario == id_formulario)))
    _retire_omitted(current_options, keep_options, "id_opcion", user.correo)
    session.flush()

    current_rules = list(session.scalars(select(ReglaFormulario).where(ReglaFormulario.id_formulario == id_formulario)))
    rule_ids: set[str] = set()
    for index, data in enumerate(rule_payloads):
        rule_id = str(data.get("id_regla") or uuid4())
        origin = data.get("id_pregunta_origen")
        target = data.get("id_pregunta_destino")
        target_section = data.get("id_seccion_destino")
        operator = str(data.get("operador") or "EQ").upper()
        action = str(data.get("accion") or "MOSTRAR").upper()
        group = str(data.get("grupo") or "TODAS").upper()
        if origin not in question_ids or (target and target not in question_ids) or (target_section and target_section not in section_ids):
            raise AppError("INVALID_RULE_REFERENCE", "La regla contiene referencias ajenas al formulario.", 422)
        if operator not in OPERADORES or action not in ACCIONES_REGLA or group not in {"TODAS", "CUALQUIERA"}:
            raise AppError("INVALID_RULE", "La condición contiene un operador, acción o agrupación inválida.", 422)
        _upsert(session, ReglaFormulario, "id_regla", rule_id, id_formulario, user.correo, {
            "id_pregunta_origen": origin, "operador": operator,
            "valor_comparacion": data.get("valor_comparacion"), "id_pregunta_destino": target,
            "id_seccion_destino": target_section, "accion": action, "grupo": group,
            "mensaje": data.get("mensaje"), "orden": index,
        })
        rule_ids.add(rule_id)
    _retire_omitted(current_rules, rule_ids, "id_regla", user.correo)

    if form.estado == "PUBLICADO":
        form.estado = "BORRADOR"
        form.fecha_publicacion = None
    mark_updated(form, user.correo)
    log_change(session, "formularios", id_formulario, "UPDATE", before,
               {**serialize_form(form), "preguntas": len(question_ids), "secciones": len(section_ids), "reglas": len(rule_ids)},
               user.correo, "Actualización desde constructor visual", correlation_id)
    session.flush()
    return get_definition(session, id_formulario)


def create_version(session: Session, form: Formulario, user: AuthenticatedUser) -> FormularioVersion:
    number = (form.version_publicada or 0) + 1
    now = utc_now_iso()
    # La definición inmutable debe reflejar el número que acaba de publicarse.
    form.version_publicada = number
    definition = get_definition(session, form.id_formulario)
    version = FormularioVersion(
        id_version_formulario=str(uuid4()), id_formulario=form.id_formulario,
        numero_version=number, definicion_json=json.dumps(definition, ensure_ascii=False),
        fecha_publicacion_version=now, publicado_por=user.correo,
        **creation_metadata(user.correo),
    )
    session.add(version)
    return version


def ensure_published_version(session: Session, form: Formulario, user: AuthenticatedUser) -> FormularioVersion:
    version = session.scalar(select(FormularioVersion).where(
        FormularioVersion.id_formulario == form.id_formulario,
        FormularioVersion.numero_version == form.version_publicada,
    )) if form.version_publicada else None
    return version or create_version(session, form, user)


def duplicate_form(session: Session, user: AuthenticatedUser, id_formulario: str,
                   *, correlation_id: str) -> Formulario:
    from app.services.formularios import create_formulario
    authorize(user, MODULE, "create")
    source = get_definition(session, id_formulario)
    new_form = create_formulario(
        session, user, motivo_auditoria="Duplicación de formulario", correlation_id=correlation_id,
        nombre=f"{source['nombre']} (copia)", descripcion=source.get("descripcion"),
        responsable=user.correo, permite_multiples_respuestas=source.get("permite_multiples_respuestas", False),
    )
    section_map = {s["id_seccion"]: str(uuid4()) for s in source["secciones"]}
    question_map = {q["id_pregunta"]: str(uuid4()) for q in source["preguntas"]}
    payload = {
        "expected_version": new_form.version, "destinos": source["destinos"],
        "secciones": [{**s, "id_seccion": section_map[s["id_seccion"]]} for s in source["secciones"]],
        "preguntas": [{**q, "id_pregunta": question_map[q["id_pregunta"]],
                       "id_seccion": section_map.get(q.get("id_seccion")),
                       "mapping": {field: question_map[target_id]
                                   for field, target_id in q.get("mapping", {}).items()
                                   if target_id in question_map},
                       "opciones": [{**o, "id_opcion": str(uuid4())} for o in q.get("opciones", [])]}
                      for q in source["preguntas"]],
        "reglas": [{**r, "id_regla": str(uuid4()),
                    "id_pregunta_origen": question_map[r["id_pregunta_origen"]],
                    "id_pregunta_destino": question_map.get(r.get("id_pregunta_destino")),
                    "id_seccion_destino": section_map.get(r.get("id_seccion_destino"))}
                   for r in source["reglas"]],
    }
    save_definition(session, user, new_form.id_formulario, payload, correlation_id=correlation_id)
    return new_form
