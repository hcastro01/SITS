/**
 * Actualiza el formulario de casos con las preguntas y opciones extraidas de
 * PREGUNTAS Y RESPUESTA DEL FORMULARIO.xlsx.
 *
 * La carga conserva los IdPregunta existentes, reutiliza opciones por su Valor
 * exacto, desactiva opciones retiradas sin borrarlas y puede ejecutarse mas de
 * una vez sin generar duplicados.
 */
function cargarPreguntasYOpcionesFormulario() {
  var formUser = TSAuth.authorize('FORMULARIOS', 'edit');
  TSAuth.authorize('CATALOGOS', 'create');
  TSAuth.authorize('CATALOGOS', 'edit');
  var correlationId = 'CARGA-OPCIONES-FORMULARIO-' + Utilities.getUuid();
  var matrix = matrizPreguntasYOpciones_();
  var form = buscarFormularioCasoMatriz_();
  var previousStatus = form ? TSUtils.normalizeKey(form.Estado) : '';

  if (form && previousStatus !== 'BORRADOR') {
    form = TSForms.changeStatus(form.IdFormulario, 'BORRADOR', correlationId);
  }

  var seedResult = cargarParametrosFormularioCaso();
  form = buscarFormularioCasoMatriz_();
  TSErrors.assert(form, 'FORM_TEMPLATE_NOT_FOUND', 'No se encontro la ficha integral de gestion de casos.', null, 404);
  TSErrors.assert(TSUtils.normalizeKey(form.Estado) === 'BORRADOR', 'FORM_TEMPLATE_NOT_DRAFT', 'El formulario debe permanecer en BORRADOR durante la carga.', null, 409);

  var catalogSync = sincronizarCatalogosMatriz_(matrix.Preguntas, formUser, correlationId);
  var definition = TSForms.definition(form.IdFormulario, true);
  var questionIndex = indexarPreguntasMatriz_(definition.questions, matrix.Preguntas);
  var updatedQuestions = 0;
  var unchangedQuestions = 0;

  matrix.Preguntas.forEach(function (config) {
    var key = TSUtils.normalizeKey(config.Etiqueta);
    var question = questionIndex[key];
    TSErrors.assert(question, 'MATRIX_QUESTION_NOT_FOUND', 'No se encontro la pregunta ' + config.Etiqueta + '.', null, 409);
    var options = opcionesPreguntaMatriz_(config, catalogSync.byKey);
    var payload = payloadPreguntaMatriz_(question, config, questionIndex, options);
    if (preguntaMatrizCoincide_(question, payload, options)) {
      unchangedQuestions += 1;
      return;
    }
    definition = TSForms.saveQuestion(payload, correlationId);
    questionIndex = indexarPreguntasMatriz_(definition.questions, matrix.Preguntas);
    updatedQuestions += 1;
  });

  var verification = verificarCargaMatriz_(form.IdFormulario, matrix);
  TSErrors.assert(verification.valid, 'FORM_MATRIX_VERIFICATION_FAILED', 'La carga termino con diferencias que deben revisarse.', { errors: verification.errors }, 409);

  return {
    formId: form.IdFormulario,
    formName: form.Nombre,
    previousStatus: previousStatus || 'NO_EXISTIA',
    currentStatus: 'BORRADOR',
    questionsConfigured: matrix.Preguntas.length,
    choiceQuestions: matrix.Preguntas.filter(function (item) { return item.Opciones.length > 0; }).length,
    activeOptions: verification.activeOptions,
    questionsUpdated: updatedQuestions,
    questionsUnchanged: unchangedQuestions,
    catalogsCreated: catalogSync.created,
    catalogsUpdated: catalogSync.updated,
    catalogsUnchanged: catalogSync.unchanged,
    seedCreatedQuestions: seedResult.createdQuestions,
    ignoredSourceColumns: matrix.ColumnasIgnoradas,
    source: { file: matrix.ArchivoFuente, sheet: matrix.HojaFuente, range: matrix.RangoFuente },
    verification: verification,
    message: 'Carga completada. Revise la vista previa y publique nuevamente el formulario.'
  };
}

function buscarFormularioCasoMatriz_() {
  var name = 'Ficha integral de gestion de casos';
  var form = TSData.list('Formularios', {
    includeDeleted: true,
    cache: false,
    predicate: function (row) {
      return TSUtils.normalizeKey(row.Nombre) === TSUtils.normalizeKey(name) &&
        TSUtils.normalizeKey(row.Proceso) === 'CASO';
    },
    limit: 1
  }).rows[0];
  if (!form) return null;
  TSErrors.assert(TSData.isVisible(form, false), 'FORM_TEMPLATE_INACTIVE', 'La ficha integral existe, pero esta inactiva.', { formId: form.IdFormulario }, 409);
  return form;
}

function indexarPreguntasMatriz_(questions, configs) {
  var managedKeys = {};
  configs.forEach(function (config) { managedKeys[TSUtils.normalizeKey(config.Etiqueta)] = true; });
  var grouped = {};
  (questions || []).forEach(function (question) {
    var key = TSUtils.normalizeKey(question.Etiqueta);
    if (!managedKeys[key]) return;
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(question);
  });
  var result = {};
  Object.keys(grouped).forEach(function (key) {
    var active = grouped[key].filter(function (question) { return TSData.isVisible(question, false); });
    TSErrors.assert(active.length <= 1 && grouped[key].length === 1, 'DUPLICATE_FORM_QUESTION', 'Existen preguntas duplicadas para ' + key + '.', { ids: grouped[key].map(function (item) { return item.IdPregunta; }) }, 409);
    result[key] = active[0] || grouped[key][0];
  });
  return result;
}

function sincronizarCatalogosMatriz_(configs, user, correlationId) {
  var desired = [];
  var desiredKeys = {};
  configs.forEach(function (config) {
    if (!config.Catalogo) return;
    var type = TSCatalog.normalizeType(config.Catalogo);
    config.Opciones.forEach(function (label, index) {
      var code = TSUtils.normalizeKey(label);
      var key = type + '|' + code;
      TSErrors.assert(!desiredKeys[key], 'DUPLICATE_MATRIX_CATALOG', 'La matriz contiene un valor de catalogo duplicado.', { type: type, value: label }, 422);
      desiredKeys[key] = true;
      desired.push({ key: key, type: type, code: code, label: label, order: index + 1 });
    });
  });

  var existingRows = TSData.list('Catalogos', { includeDeleted: true, cache: false }).rows;
  var existingByKey = {};
  existingRows.forEach(function (row) {
    var key = TSCatalog.normalizeType(row.Tipo) + '|' + TSUtils.normalizeKey(row.Codigo);
    if (!desiredKeys[key]) return;
    TSErrors.assert(!existingByKey[key], 'DUPLICATE_CATALOG', 'Existen catalogos duplicados para ' + key + '.', null, 409);
    existingByKey[key] = row;
  });

  var byKey = {};
  var pendingCreates = [];
  var created = 0;
  var updated = 0;
  var unchanged = 0;

  desired.forEach(function (item) {
    var existing = existingByKey[item.key];
    if (existing) {
      byKey[item.key] = existing;
      return;
    }
    var row = {
      IdCatalogo: TSUtils.uuid('CAT'), Tipo: item.type, Codigo: item.code,
      Valor: item.label, Descripcion: 'Importado desde PREGUNTAS Y RESPUESTA DEL FORMULARIO.xlsx',
      Orden: item.order, EsSensible: false, Activo: true, Eliminado: false
    };
    pendingCreates.push(row);
    byKey[item.key] = row;
  });

  TSUtils.withScriptLock(function () {
    desired.forEach(function (item) {
      var existing = existingByKey[item.key];
      if (!existing) return;
      var needsUpdate = Number(existing.Orden || 0) !== Number(item.order) ||
        !TSUtils.toBoolean(existing.Activo) || TSUtils.toBoolean(existing.Eliminado);
      if (!needsUpdate) {
        unchanged += 1;
        return;
      }
      var changed = TSData.updateUnsafe('Catalogos', existing.IdCatalogo, {
        Orden: item.order, Activo: true, Eliminado: false
      }, user.email, existing.Version);
      TSAudit.log('UPDATE', 'Catalogos', existing.IdCatalogo, changed.before, changed.after, user.email, 'Sincronizacion desde matriz de formulario', correlationId);
      byKey[item.key] = changed.after;
      updated += 1;
    });
    var inserted = TSData.insertManyUnsafe('Catalogos', pendingCreates, user.email);
    if (inserted.length) TSAudit.batchActionUnsafe('CREATE', 'Catalogos', inserted, user.email, 'Carga desde matriz de formulario', correlationId);
    inserted.forEach(function (row) {
      var key = TSCatalog.normalizeType(row.Tipo) + '|' + TSUtils.normalizeKey(row.Codigo);
      byKey[key] = row;
    });
    created = inserted.length;
  });

  return { byKey: byKey, created: created, updated: updated, unchanged: unchanged };
}

function opcionesPreguntaMatriz_(config, catalogByKey) {
  var type = config.Catalogo ? TSCatalog.normalizeType(config.Catalogo) : '';
  return config.Opciones.map(function (label, index) {
    var catalog = type ? catalogByKey[type + '|' + TSUtils.normalizeKey(label)] : null;
    if (type) TSErrors.assert(catalog, 'MATRIX_CATALOG_NOT_FOUND', 'No se encontro el catalogo para ' + label + '.', { type: type }, 409);
    return {
      Valor: label, Etiqueta: label, Orden: index + 1,
      IdCatalogo: catalog ? catalog.IdCatalogo : '', IdOpcionPadre: ''
    };
  });
}

function payloadPreguntaMatriz_(question, config, questionIndex, options) {
  var hasDefault = Object.prototype.hasOwnProperty.call(config, 'ValorPredeterminado');
  var payload = {
    IdPregunta: question.IdPregunta,
    IdFormulario: question.IdFormulario,
    Etiqueta: config.Etiqueta,
    Descripcion: question.Descripcion || '',
    Tipo: config.Tipo,
    Obligatoria: TSUtils.toBoolean(config.Obligatoria),
    Orden: config.Orden,
    Categoria: config.Categoria,
    Subcategoria: question.Subcategoria || '',
    ValorPredeterminado: hasDefault ? config.ValorPredeterminado : '',
    TextoAyuda: config.TextoAyuda !== undefined ? config.TextoAyuda : (config.Opciones.length ? 'Seleccione una opcion.' : (question.TextoAyuda || '')),
    Visible: true,
    SoloLectura: TSUtils.toBoolean(config.SoloLectura),
    LongitudMaxima: config.LongitudMaxima !== undefined ? config.LongitudMaxima : '',
    Validacion: config.Tipo === 'PERSONA' ? '' : (question.Validacion || ''),
    Sensibilidad: config.Sensibilidad !== undefined ? config.Sensibilidad : (question.Sensibilidad || ''),
    CondicionVisibilidad: question.CondicionVisibilidad || '',
    CampoDependiente: question.CampoDependiente || '',
    ValorDependiente: question.ValorDependiente || '',
    Formula: '',
    Activo: true,
    Eliminado: false,
    expectedVersion: question.Version,
    reason: 'Configuracion importada desde matriz de preguntas y respuestas',
    options: options
  };

  if (config.DependeDe) {
    var source = questionIndex[TSUtils.normalizeKey(config.DependeDe)];
    TSErrors.assert(source, 'FORM_DEPENDENCY_MISSING', 'No se encontro la pregunta dependiente ' + config.DependeDe + '.', null, 409);
    var expected = (config.ValoresDependencia || []).join('|');
    payload.CampoDependiente = source.IdPregunta;
    payload.ValorDependiente = expected;
    payload.CondicionVisibilidad = JSON.stringify({ operator: config.OperadorDependencia || 'IN', value: expected });
  }
  if (TSUtils.normalizeKey(config.Etiqueta) === 'CODIGOCASO') {
    payload.Descripcion = 'Codigo unico generado automaticamente por el servidor al crear el caso.';
    payload.CampoDependiente = '';
    payload.ValorDependiente = '';
    payload.CondicionVisibilidad = '';
  }
  return payload;
}

function preguntaMatrizCoincide_(question, payload, desiredOptions) {
  var scalarMatches =
    String(question.Etiqueta || '') === String(payload.Etiqueta || '') &&
    TSUtils.normalizeKey(question.Tipo) === TSUtils.normalizeKey(payload.Tipo) &&
    TSUtils.toBoolean(question.Obligatoria) === TSUtils.toBoolean(payload.Obligatoria) &&
    Number(question.Orden || 0) === Number(payload.Orden || 0) &&
    String(question.Categoria || '') === String(payload.Categoria || '') &&
    String(question.ValorPredeterminado || '') === String(payload.ValorPredeterminado || '') &&
    String(question.TextoAyuda || '') === String(payload.TextoAyuda || '') &&
    TSUtils.toBoolean(question.Visible) === TSUtils.toBoolean(payload.Visible) &&
    TSUtils.toBoolean(question.SoloLectura) === TSUtils.toBoolean(payload.SoloLectura) &&
    String(question.LongitudMaxima || '') === String(payload.LongitudMaxima || '') &&
    String(question.Sensibilidad || '') === String(payload.Sensibilidad || '') &&
    String(question.CampoDependiente || '') === String(payload.CampoDependiente || '') &&
    String(question.ValorDependiente || '') === String(payload.ValorDependiente || '') &&
    JSON.stringify(TSUtils.parseJson(question.CondicionVisibilidad, {})) === JSON.stringify(TSUtils.parseJson(payload.CondicionVisibilidad, {})) &&
    TSData.isVisible(question, false);
  if (!scalarMatches) return false;

  var current = (question.Opciones || []).filter(function (option) {
    return TSData.isVisible(option, false);
  }).sort(function (a, b) { return Number(a.Orden || 0) - Number(b.Orden || 0); });
  if (current.length !== desiredOptions.length) return false;
  return desiredOptions.every(function (desired, index) {
    var actual = current[index];
    return actual && String(actual.Valor) === String(desired.Valor) &&
      String(actual.Etiqueta) === String(desired.Etiqueta) &&
      Number(actual.Orden || 0) === Number(desired.Orden || 0) &&
      String(actual.IdCatalogo || '') === String(desired.IdCatalogo || '');
  });
}

function verificarCargaMatriz_(formId, matrix) {
  var definition = TSForms.definition(formId, true);
  var errors = [];
  var activeOptions = 0;
  var index;
  try {
    index = indexarPreguntasMatriz_(definition.questions, matrix.Preguntas);
  } catch (error) {
    return { valid: false, errors: [error.message || String(error)], activeQuestions: 0, activeOptions: 0 };
  }
  matrix.Preguntas.forEach(function (config) {
    var question = index[TSUtils.normalizeKey(config.Etiqueta)];
    if (!question || !TSData.isVisible(question, false)) {
      errors.push('Pregunta ausente o inactiva: ' + config.Etiqueta);
      return;
    }
    if (TSUtils.normalizeKey(question.Tipo) !== TSUtils.normalizeKey(config.Tipo)) errors.push('Tipo incorrecto: ' + config.Etiqueta);
    var active = (question.Opciones || []).filter(function (option) { return TSData.isVisible(option, false); })
      .sort(function (a, b) { return Number(a.Orden || 0) - Number(b.Orden || 0); });
    activeOptions += active.length;
    if (active.length !== config.Opciones.length) {
      errors.push('Cantidad de opciones incorrecta: ' + config.Etiqueta);
      return;
    }
    config.Opciones.forEach(function (label, optionIndex) {
      if (!active[optionIndex] || String(active[optionIndex].Valor) !== String(label) || String(active[optionIndex].Etiqueta) !== String(label)) {
        errors.push('Opcion diferente en ' + config.Etiqueta + ': ' + label);
      }
    });
  });
  return {
    valid: errors.length === 0,
    errors: errors,
    activeQuestions: matrix.Preguntas.length,
    activeOptions: activeOptions,
    ignoredSourceColumns: matrix.ColumnasIgnoradas
  };
}
