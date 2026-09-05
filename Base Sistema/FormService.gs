var TSForms = (function () {
  var FORM_STATES = ['BORRADOR', 'PUBLICADO', 'INACTIVO'];

  function activeRows(table, predicate, includeInactive) {
    return TSData.list(table, {
      includeDeleted: Boolean(includeInactive),
      predicate: function (row) { return (includeInactive || TSData.isVisible(row, false)) && (!predicate || predicate(row)); }
    }).rows;
  }

  function listPublished() {
    TSAuth.authorize('FORMULARIOS', 'read');
    return activeRows('Formularios', function (row) { return TSUtils.normalizeKey(row.Estado) === 'PUBLICADO'; }, false).sort(function (a, b) { return String(a.Nombre).localeCompare(String(b.Nombre)); });
  }

  function listAdmin(options) {
    TSAuth.authorize('FORMULARIOS', 'edit');
    options = options || {};
    return TSData.list('Formularios', {
      includeDeleted: Boolean(options.includeInactive),
      predicate: function (row) {
        if (options.status && TSUtils.normalizeKey(row.Estado) !== TSUtils.normalizeKey(options.status)) return false;
        if (options.process && TSUtils.normalizeKey(row.Proceso) !== TSUtils.normalizeKey(options.process)) return false;
        return true;
      }, sortBy: 'FechaCreacion', sortDirection: 'desc'
    });
  }

  function definition(id, adminMode, authorizedUser) {
    var user = authorizedUser || TSAuth.authorize('FORMULARIOS', 'read');
    if (adminMode) TSErrors.assert(TSAuth.can(user, 'FORMULARIOS', 'edit'), 'FORBIDDEN', 'No tiene permisos para administrar formularios.', null, 403);
    var form = TSData.findById('Formularios', id, Boolean(adminMode));
    TSErrors.assert(form, 'FORM_NOT_FOUND', 'Formulario no encontrado.', null, 404);
    if (TSUtils.normalizeKey(form.Estado) !== 'PUBLICADO') {
      TSErrors.assert(adminMode && TSAuth.can(user, 'FORMULARIOS', 'edit'), 'FORM_NOT_PUBLISHED', 'El formulario no se encuentra publicado.', null, 403);
    }
    var questions = activeRows('Preguntas', function (row) { return String(row.IdFormulario) === String(id); }, Boolean(adminMode));
    questions.sort(function (a, b) { return Number(a.Orden || 0) - Number(b.Orden || 0); });
    var questionIds = {};
    questions.forEach(function (question) { questionIds[String(question.IdPregunta)] = true; });
    var options = activeRows('OpcionesPregunta', function (row) { return questionIds[String(row.IdPregunta)]; }, Boolean(adminMode));
    options.sort(function (a, b) { return Number(a.Orden || 0) - Number(b.Orden || 0); });
    var groupedOptions = {};
    options.forEach(function (option) {
      var key = String(option.IdPregunta);
      if (!groupedOptions[key]) groupedOptions[key] = [];
      groupedOptions[key].push(option);
    });
    questions.forEach(function (question) { question.Opciones = groupedOptions[String(question.IdPregunta)] || []; });
    var rules = activeRows('ReglasFormulario', function (row) { return String(row.IdFormulario) === String(id); }, Boolean(adminMode));
    rules.sort(function (a, b) { return Number(a.Orden || 0) - Number(b.Orden || 0); });
    return { form: form, questions: questions, rules: rules, questionTypes: TSValidation.questionTypes.slice() };
  }

  function saveDefinition(payload, correlationId) {
    var source = payload && payload.form ? payload.form : (payload || {});
    var user = TSAuth.authorize('FORMULARIOS', source.IdFormulario ? 'edit' : 'create');
    TSValidation.required(source, ['Nombre', 'Proceso']);
    var state = TSUtils.normalizeKey(source.Estado || 'BORRADOR');
    TSErrors.assert(FORM_STATES.indexOf(state) !== -1, 'INVALID_FORM_STATUS', 'Estado de formulario invalido.', null, 422);
    var values = TSValidation.record('Formularios', source, Boolean(source.IdFormulario));
    values.Estado = state;
    values.Responsable = values.Responsable || user.email;
    return TSUtils.withScriptLock(function () {
      var form;
      if (values.IdFormulario) {
        var updated = TSData.updateUnsafe('Formularios', values.IdFormulario, values, user.email, source.expectedVersion);
        TSAudit.log('UPDATE', 'Formularios', values.IdFormulario, updated.before, updated.after, user.email, source.reason || 'Edicion de formulario', correlationId);
        form = updated.after;
      } else {
        form = TSData.insertUnsafe('Formularios', values, user.email);
        TSAudit.log('CREATE', 'Formularios', form.IdFormulario, {}, form, user.email, source.reason || 'Creacion de formulario', correlationId);
      }
      if (payload && Array.isArray(payload.rules)) syncRulesUnsafe(form.IdFormulario, payload.rules, user, correlationId);
      return form;
    });
  }

  function syncRulesUnsafe(formId, incoming, user, correlationId) {
    var existing = TSData.list('ReglasFormulario', { includeDeleted: true, cache: false, filters: { IdFormulario: formId } }).rows;
    var validQuestions = {};
    TSData.list('Preguntas', { includeDeleted: true, filters: { IdFormulario: formId } }).rows.forEach(function (question) { validQuestions[String(question.IdPregunta)] = true; });
    var retained = {};
    incoming.forEach(function (rule, index) {
      var values = {
        IdFormulario: formId, IdPreguntaOrigen: rule.IdPreguntaOrigen || rule.sourceQuestionId,
        Operador: TSUtils.normalizeKey(rule.Operador || rule.operator || 'EQ'),
        ValorComparacion: rule.ValorComparacion !== undefined ? rule.ValorComparacion : rule.value,
        IdPreguntaDestino: rule.IdPreguntaDestino || rule.targetQuestionId,
        Accion: TSUtils.normalizeKey(rule.Accion || rule.action || 'MOSTRAR'),
        Mensaje: TSUtils.cleanText(rule.Mensaje || rule.message || '', 1000),
        Orden: Number(rule.Orden !== undefined ? rule.Orden : index + 1), Activo: true, Eliminado: false
      };
      TSValidation.required(values, ['IdPreguntaOrigen', 'IdPreguntaDestino', 'Accion']);
      TSErrors.assert(validQuestions[String(values.IdPreguntaOrigen)] && validQuestions[String(values.IdPreguntaDestino)], 'INVALID_FORM_RULE', 'Las preguntas de la regla deben pertenecer al mismo formulario.', null, 422);
      var found = rule.IdRegla ? existing.filter(function (row) { return String(row.IdRegla) === String(rule.IdRegla); })[0] : null;
      if (found) {
        retained[found.IdRegla] = true;
        var changed = TSData.updateUnsafe('ReglasFormulario', found.IdRegla, values, user.email, rule.expectedVersion);
        TSAudit.log('UPDATE', 'ReglasFormulario', found.IdRegla, changed.before, changed.after, user.email, 'Edicion de regla', correlationId);
      } else {
        var created = TSData.insertUnsafe('ReglasFormulario', values, user.email);
        retained[created.IdRegla] = true;
        TSAudit.log('CREATE', 'ReglasFormulario', created.IdRegla, {}, created, user.email, 'Alta de regla', correlationId);
      }
    });
    existing.forEach(function (rule) {
      if (!retained[rule.IdRegla] && TSData.isVisible(rule, false)) {
        var retired = TSData.updateUnsafe('ReglasFormulario', rule.IdRegla, { Activo: false }, user.email);
        TSAudit.log('UPDATE', 'ReglasFormulario', rule.IdRegla, retired.before, retired.after, user.email, 'Regla retirada', correlationId);
      }
    });
  }

  function nextOrder(formId) {
    var questions = activeRows('Preguntas', function (row) { return String(row.IdFormulario) === String(formId); }, false);
    return questions.reduce(function (max, question) { return Math.max(max, Number(question.Orden) || 0); }, 0) + 1;
  }

  function syncOptionsUnsafe(questionId, incoming, user, correlationId) {
    if (!Array.isArray(incoming)) return;
    var existing = TSData.list('OpcionesPregunta', { includeDeleted: true, cache: false, filters: { IdPregunta: questionId } }).rows;
    var retained = {};
    var incomingValues = {};
    var pendingCreates = [];
    incoming.forEach(function (option, index) {
      var values = {
        IdPregunta: questionId, Valor: TSUtils.cleanText(option.Valor !== undefined ? option.Valor : option.value, 500),
        Etiqueta: TSUtils.cleanText(option.Etiqueta !== undefined ? option.Etiqueta : option.label, 500),
        Orden: Number(option.Orden !== undefined ? option.Orden : index + 1),
        IdCatalogo: option.IdCatalogo || option.catalogId || '', IdOpcionPadre: option.IdOpcionPadre || option.parentOptionId || '',
        Activo: true, Eliminado: false
      };
      TSValidation.required(values, ['Valor']);
      var incomingKey = String(values.Valor);
      TSErrors.assert(!incomingValues[incomingKey], 'DUPLICATE_QUESTION_OPTION', 'La pregunta contiene opciones duplicadas.', { value: values.Valor }, 422);
      incomingValues[incomingKey] = true;
      var found = option.IdOpcion ? existing.filter(function (row) { return String(row.IdOpcion) === String(option.IdOpcion); })[0] : null;
      if (!found) {
        var candidates = existing.filter(function (row) {
          return !retained[row.IdOpcion] && String(row.Valor) === String(values.Valor);
        }).sort(function (a, b) {
          return (TSData.isVisible(a, false) ? 0 : 1) - (TSData.isVisible(b, false) ? 0 : 1);
        });
        found = candidates[0] || null;
      }
      if (found) {
        retained[found.IdOpcion] = true;
        var changed = ['Valor', 'Etiqueta', 'Orden', 'IdCatalogo', 'IdOpcionPadre', 'Activo', 'Eliminado'].some(function (field) {
          return !TSUtils.valuesEqual(found[field], values[field]);
        });
        if (changed) {
          var updated = TSData.updateUnsafe('OpcionesPregunta', found.IdOpcion, values, user.email, option.expectedVersion);
          TSAudit.log('UPDATE', 'OpcionesPregunta', found.IdOpcion, updated.before, updated.after, user.email, 'Edicion de opcion', correlationId);
        }
      } else {
        pendingCreates.push(values);
      }
    });
    var created = TSData.insertManyUnsafe('OpcionesPregunta', pendingCreates, user.email);
    created.forEach(function (row) { retained[row.IdOpcion] = true; });
    if (created.length) TSAudit.batchActionUnsafe('CREATE', 'OpcionesPregunta', created, user.email, 'Carga masiva de opciones de pregunta', correlationId);
    existing.forEach(function (row) {
      if (!retained[row.IdOpcion] && TSData.isVisible(row, false)) {
        var deactivated = TSData.updateUnsafe('OpcionesPregunta', row.IdOpcion, { Activo: false }, user.email);
        TSAudit.log('UPDATE', 'OpcionesPregunta', row.IdOpcion, deactivated.before, deactivated.after, user.email, 'Opcion retirada de la pregunta', correlationId);
      }
    });
  }

  function saveQuestion(payload, correlationId) {
    payload = payload || {};
    var user = TSAuth.authorize('FORMULARIOS', payload.IdPregunta ? 'edit' : 'create');
    var values = TSValidation.question(payload);
    TSErrors.assert(TSData.findById('Formularios', values.IdFormulario, false), 'FORM_NOT_FOUND', 'Formulario no encontrado.', null, 404);
    values.Obligatoria = TSUtils.toBoolean(values.Obligatoria);
    values.Visible = values.Visible === '' || values.Visible === undefined ? true : TSUtils.toBoolean(values.Visible);
    values.SoloLectura = TSUtils.toBoolean(values.SoloLectura);
    values.Sensibilidad = TSUtils.cleanText(values.Sensibilidad || '', 120);
    return TSUtils.withScriptLock(function () {
      var question;
      if (values.IdPregunta) {
        var updated = TSData.updateUnsafe('Preguntas', values.IdPregunta, values, user.email, payload.expectedVersion);
        TSAudit.log('UPDATE', 'Preguntas', values.IdPregunta, updated.before, updated.after, user.email, payload.reason || 'Edicion de pregunta', correlationId);
        question = updated.after;
      } else {
        if (!Number(values.Orden)) values.Orden = nextOrder(values.IdFormulario);
        question = TSData.insertUnsafe('Preguntas', values, user.email);
        TSAudit.log('CREATE', 'Preguntas', question.IdPregunta, {}, question, user.email, payload.reason || 'Creacion de pregunta', correlationId);
      }
      syncOptionsUnsafe(question.IdPregunta, payload.options || payload.Opciones, user, correlationId);
      return definition(question.IdFormulario, true, user);
    });
  }

  function duplicateQuestion(id, correlationId) {
    var user = TSAuth.authorize('FORMULARIOS', 'create');
    var source = TSData.findById('Preguntas', id, false);
    TSErrors.assert(source, 'QUESTION_NOT_FOUND', 'Pregunta no encontrada.', null, 404);
    return TSUtils.withScriptLock(function () {
      var values = TSUtils.pick(source, TSConfig.schema('Preguntas'));
      delete values.IdPregunta;
      values.Etiqueta = TSUtils.cleanText(source.Etiqueta + ' (copia)', 1000);
      values.Orden = nextOrder(source.IdFormulario);
      var created = TSData.insertUnsafe('Preguntas', values, user.email);
      TSAudit.log('CREATE', 'Preguntas', created.IdPregunta, {}, created, user.email, 'Duplicacion de pregunta ' + id, correlationId);
      var options = TSData.list('OpcionesPregunta', { filters: { IdPregunta: id } }).rows.map(function (option) {
        return { Valor: option.Valor, Etiqueta: option.Etiqueta, Orden: option.Orden, IdCatalogo: option.IdCatalogo, IdOpcionPadre: option.IdOpcionPadre };
      });
      syncOptionsUnsafe(created.IdPregunta, options, user, correlationId);
      return definition(source.IdFormulario, true, user);
    });
  }

  function reorder(payload, correlationId) {
    var user = TSAuth.authorize('FORMULARIOS', 'edit');
    payload = payload || {};
    TSValidation.required(payload, ['formId']);
    var questions = activeRows('Preguntas', function (row) { return String(row.IdFormulario) === String(payload.formId); }, false);
    questions.sort(function (a, b) { return Number(a.Orden || 0) - Number(b.Orden || 0); });
    var ids = Array.isArray(payload.questionIds) ? payload.questionIds.map(String) : questions.map(function (q) { return String(q.IdPregunta); });
    if (!payload.questionIds && payload.questionId && payload.direction) {
      var index = ids.indexOf(String(payload.questionId));
      var swap = TSUtils.normalizeKey(payload.direction) === 'UP' ? index - 1 : index + 1;
      if (index >= 0 && swap >= 0 && swap < ids.length) { var temp = ids[index]; ids[index] = ids[swap]; ids[swap] = temp; }
    }
    var expected = questions.map(function (q) { return String(q.IdPregunta); }).sort();
    TSErrors.assert(JSON.stringify(ids.slice().sort()) === JSON.stringify(expected), 'INVALID_ORDER', 'La lista de preguntas no coincide con el formulario.', null, 422);
    return TSUtils.withScriptLock(function () {
      ids.forEach(function (id, index) {
        var current = questions.filter(function (q) { return String(q.IdPregunta) === id; })[0];
        if (Number(current.Orden) !== index + 1) {
          var updated = TSData.updateUnsafe('Preguntas', id, { Orden: index + 1 }, user.email);
          TSAudit.log('UPDATE', 'Preguntas', id, updated.before, updated.after, user.email, 'Reordenamiento', correlationId);
        }
      });
      return definition(payload.formId, true, user);
    });
  }

  function deactivate(id, reason, correlationId) {
    var user = TSAuth.authorize('FORMULARIOS', 'edit');
    var source = TSData.findById('Preguntas', id, false);
    TSErrors.assert(source, 'QUESTION_NOT_FOUND', 'Pregunta no encontrada.', null, 404);
    return TSUtils.withScriptLock(function () {
      var updated = TSData.updateUnsafe('Preguntas', id, { Activo: false }, user.email);
      TSAudit.log('UPDATE', 'Preguntas', id, updated.before, updated.after, user.email, reason || 'Pregunta desactivada', correlationId);
      return definition(source.IdFormulario, true, user);
    });
  }

  function changeStatus(id, status, correlationId) {
    var user = TSAuth.authorize('FORMULARIOS', 'edit');
    var normalized = TSUtils.normalizeKey(status);
    TSErrors.assert(FORM_STATES.indexOf(normalized) !== -1, 'INVALID_FORM_STATUS', 'Estado de formulario invalido.', null, 422);
    return TSUtils.withScriptLock(function () {
      if (normalized === 'PUBLICADO') {
        var count = activeRows('Preguntas', function (row) { return String(row.IdFormulario) === String(id); }, false).length;
        TSErrors.assert(count > 0, 'FORM_WITHOUT_QUESTIONS', 'Agregue al menos una pregunta antes de publicar.', null, 422);
      }
      var updated = TSData.updateUnsafe('Formularios', id, { Estado: normalized, FechaPublicacion: normalized === 'PUBLICADO' ? TSUtils.now() : '' }, user.email);
      TSAudit.log('UPDATE', 'Formularios', id, updated.before, updated.after, user.email, 'Cambio de estado a ' + normalized, correlationId);
      return updated.after;
    });
  }

  function answerMap(input) {
    if (Array.isArray(input)) {
      var mapped = {};
      input.forEach(function (answer) { mapped[String(answer.IdPregunta || answer.questionId)] = answer.value !== undefined ? answer.value : answer.Valor; });
      return mapped;
    }
    return input && typeof input === 'object' ? input : {};
  }

  function compare(value, operator, expected) {
    operator = TSUtils.normalizeKey(operator || 'EQ');
    if (operator === 'EQ' || operator === 'IGUAL') return String(value) === String(expected);
    if (operator === 'NE' || operator === 'DISTINTO') return String(value) !== String(expected);
    if (operator === 'CONTAINS' || operator === 'CONTIENE') return String(value || '').toLowerCase().indexOf(String(expected || '').toLowerCase()) !== -1;
    if (operator === 'IN') return (Array.isArray(expected) ? expected : String(expected || '').split('|')).map(String).indexOf(String(value)) !== -1;
    if (operator === 'NOT_EMPTY') return !TSUtils.isBlank(value);
    if (operator === 'EMPTY') return TSUtils.isBlank(value);
    return false;
  }

  function isVisible(question, answers) {
    if (TSUtils.normalizeKey(question.Tipo) === 'CAMPO_OCULTO') return true;
    if (!TSUtils.toBoolean(question.Visible)) return false;
    if (TSUtils.isBlank(question.CampoDependiente)) return true;
    var condition = TSUtils.parseJson(question.CondicionVisibilidad, {});
    var expected = condition.value !== undefined ? condition.value : question.ValorDependiente;
    return compare(answers[String(question.CampoDependiente)], condition.operator || 'EQ', expected);
  }

  function ruleState(question, answers, rules) {
    var state = { visible: isVisible(question, answers), required: TSUtils.toBoolean(question.Obligatoria) };
    (rules || []).filter(function (rule) { return String(rule.IdPreguntaDestino) === String(question.IdPregunta); }).forEach(function (rule) {
      var applies = compare(answers[String(rule.IdPreguntaOrigen)], rule.Operador, rule.ValorComparacion);
      var action = TSUtils.normalizeKey(rule.Accion);
      if (action === 'MOSTRAR' || action === 'SHOW') state.visible = applies;
      else if ((action === 'OCULTAR' || action === 'HIDE') && applies) state.visible = false;
      else if ((action === 'REQUERIR' || action === 'REQUIRE') && applies) state.required = true;
    });
    return state;
  }

  function calculated(question, answers) {
    var formula = String(question.Formula || '').trim();
    var match = formula.match(/^SUM\(([^)]+)\)$/i);
    if (match) return match[1].split(',').reduce(function (sum, id) { return sum + (Number(answers[id.trim()]) || 0); }, 0);
    match = formula.match(/^CONCAT\(([^)]+)\)$/i);
    if (match) return match[1].split(',').map(function (id) { return String(answers[id.trim()] || ''); }).join(' ');
    if (/^TODAY\(\)$/i.test(formula)) return Utilities.formatDate(new Date(), TSConfig.get().timeZone, 'yyyy-MM-dd');
    return question.ValorPredeterminado || '';
  }

  function validateConfiguredAnswer(question, value) {
    if (TSUtils.isBlank(value)) return;
    var type = TSUtils.normalizeKey(question.Tipo);
    var values = Array.isArray(value) ? value : [value];
    if (type !== 'SELECCION_MULTIPLE') TSErrors.assert(values.length === 1, 'INVALID_ANSWER', 'La pregunta admite una sola respuesta.', { questionId: question.IdPregunta }, 422);
    if (['LISTA_DESPLEGABLE', 'SELECCION_UNICA', 'SELECCION_MULTIPLE', 'ESCALA_LIKERT'].indexOf(type) !== -1 && question.Opciones && question.Opciones.length) {
      var allowed = {};
      question.Opciones.forEach(function (option) { allowed[String(option.Valor)] = true; allowed[String(option.IdOpcion)] = true; });
      values.forEach(function (item) { TSErrors.assert(allowed[String(item)], 'INVALID_OPTION', 'La opcion seleccionada no pertenece a la pregunta.', { questionId: question.IdPregunta }, 422); });
    }
    if (type === 'PERSONA') TSErrors.assert(TSData.findById('Personas', values[0], false), 'PERSON_NOT_FOUND', 'La persona seleccionada no existe.', { questionId: question.IdPregunta }, 422);
    if ((type === 'AREA' || type === 'TURNO') && (!question.Opciones || !question.Opciones.length)) {
      var catalog = TSData.list('Catalogos', { predicate: function (row) {
        if (TSCatalog.normalizeType(row.Tipo) !== type) return false;
        return String(row.IdCatalogo) === String(values[0]) || TSUtils.normalizeKey(row.Codigo) === TSUtils.normalizeKey(values[0]) || TSUtils.normalizeKey(row.Valor) === TSUtils.normalizeKey(values[0]);
      }, limit: 1 }).rows[0];
      TSErrors.assert(catalog, 'INVALID_OPTION', 'El valor seleccionado no existe en el catalogo.', { questionId: question.IdPregunta }, 422);
    }
    var validation = TSUtils.parseJson(question.Validacion, {});
    var rawValidation = String(question.Validacion || '').trim();
    var validationCode = rawValidation && rawValidation.charAt(0) !== '{' ? TSUtils.normalizeKey(rawValidation) : '';
    var textValue = String(values[0] === null || values[0] === undefined ? '' : values[0]);
    if (validationCode === 'EMAIL') TSErrors.assert(/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(textValue), 'INVALID_EMAIL', 'Ingrese un correo electronico valido.', { questionId: question.IdPregunta }, 422);
    else if (validationCode === 'PHONE') TSErrors.assert(/^\+?[0-9 ()-]{7,25}$/.test(textValue), 'INVALID_PHONE', 'Ingrese un telefono valido.', { questionId: question.IdPregunta }, 422);
    else if (validationCode === 'ID') TSErrors.assert(/^[A-Za-z0-9._-]{3,50}$/.test(textValue), 'INVALID_IDENTIFIER', 'Ingrese un identificador valido.', { questionId: question.IdPregunta }, 422);
    else if (validationCode === 'POSITIVE') TSErrors.assert(isFinite(Number(textValue)) && Number(textValue) > 0, 'INVALID_POSITIVE_NUMBER', 'Ingrese un numero mayor que cero.', { questionId: question.IdPregunta }, 422);
    else if (rawValidation && !validationCode.match(/^(EMAIL|PHONE|ID|POSITIVE)$/) && rawValidation.charAt(0) !== '{') {
      TSErrors.assert(rawValidation.length <= 200 && textValue.length <= 5000 && !/\\[1-9]|\(\?[<!=]|\([^)]*[+*][^)]*\)[+*]/.test(rawValidation), 'UNSAFE_VALIDATION_PATTERN', 'El patron de validacion no es seguro.', { questionId: question.IdPregunta }, 422);
      var expression;
      try { expression = new RegExp(rawValidation); } catch (error) { throw new TSAppError('INVALID_VALIDATION_PATTERN', 'El patron de validacion no es valido.', { questionId: question.IdPregunta }, 422); }
      TSErrors.assert(expression.test(textValue), 'ANSWER_PATTERN_MISMATCH', 'La respuesta no cumple el formato requerido.', { questionId: question.IdPregunta }, 422);
    }
    if (type === 'NUMERO' || type === 'ESCALA_LIKERT') {
      var numeric = Number(values[0]);
      if (validation.min !== undefined) TSErrors.assert(numeric >= Number(validation.min), 'ANSWER_BELOW_MIN', 'El valor es inferior al minimo permitido.', { questionId: question.IdPregunta }, 422);
      if (validation.max !== undefined) TSErrors.assert(numeric <= Number(validation.max), 'ANSWER_ABOVE_MAX', 'El valor supera el maximo permitido.', { questionId: question.IdPregunta }, 422);
    }
  }

  function answerRows(question, value, base) {
    var type = TSUtils.normalizeKey(question.Tipo);
    if (type === 'CAMPO_CALCULADO') value = calculated(question, base._answers);
    if (TSUtils.isBlank(value) && !TSUtils.isBlank(question.ValorPredeterminado)) value = question.ValorPredeterminado;
    var values = type === 'SELECCION_MULTIPLE' && Array.isArray(value) ? value : [value];
    if (!values.length) values = [''];
    return values.map(function (single) {
      var row = {
        IdDetalleRespuesta: TSUtils.uuid('ANS'), IdRespuesta: base.IdRespuesta,
        IdEnvioCliente: base.IdEnvioCliente, IdFormulario: base.IdFormulario,
        IdPregunta: question.IdPregunta, IdRegistroProceso: base.IdRegistroProceso,
        EstadoRespuesta: base.EstadoRespuesta, FechaRespuesta: TSUtils.now(), UsuarioRespuesta: base.UsuarioRespuesta
      };
      if (type === 'NUMERO' || type === 'ESCALA_LIKERT') {
        if (!TSUtils.isBlank(single)) {
          var number = Number(single);
          TSErrors.assert(isFinite(number), 'INVALID_ANSWER', 'Ingrese un numero valido.', { questionId: question.IdPregunta }, 422);
          row.ValorNumero = number;
        }
      } else if (type === 'FECHA' || type === 'FECHA_HORA') {
        if (!TSUtils.isBlank(single)) row.ValorFecha = TSUtils.asDate(single, question.Etiqueta);
      } else if (type === 'SI_NO') row.ValorBooleano = TSUtils.isBlank(single) ? '' : TSUtils.toBoolean(single);
      else if (['LISTA_DESPLEGABLE', 'SELECCION_UNICA', 'SELECCION_MULTIPLE', 'PERSONA', 'AREA', 'TURNO'].indexOf(type) !== -1) row.ValorOpcion = TSUtils.cleanText(single, 5000);
      else {
        var maxLength = Number(question.LongitudMaxima) || 50000;
        TSErrors.assert(String(single === null || single === undefined ? '' : single).length <= maxLength, 'ANSWER_TOO_LONG', 'La respuesta supera la longitud maxima.', { questionId: question.IdPregunta, maxLength: maxLength }, 422);
        row.ValorTexto = TSUtils.cleanText(single, maxLength);
      }
      return row;
    });
  }

  function saveResponse(payload, draft, correlationId) {
    payload = payload || {};
    var formId = payload.formId || payload.IdFormulario;
    TSValidation.required({ formId: formId }, ['formId']);
    var user = TSAuth.authorize('RESPUESTAS', 'create');
    var def = definition(formId, false);
    var answers = answerMap(payload.answers || payload.respuestas);
    var responseId = payload.responseId || payload.IdRespuesta || TSUtils.uuid('RESP');
    var clientId = TSUtils.cleanText(payload.clientSubmissionId || payload.IdEnvioCliente || '', 200);
    var states = {};
    def.questions.forEach(function (question) { states[String(question.IdPregunta)] = ruleState(question, answers, def.rules); });
    var visibleQuestions = def.questions.filter(function (question) { return states[String(question.IdPregunta)].visible; });
    if (!draft) {
      var missing = visibleQuestions.filter(function (question) {
        var type = TSUtils.normalizeKey(question.Tipo);
        return states[String(question.IdPregunta)].required && ['SECCION', 'CAMPO_CALCULADO'].indexOf(type) === -1 && TSUtils.isBlank(answers[String(question.IdPregunta)]) && TSUtils.isBlank(question.ValorPredeterminado);
      }).map(function (question) { return question.Etiqueta; });
      if (missing.length) throw new TSAppError('REQUIRED_ANSWERS', 'Complete las preguntas obligatorias.', { fields: missing }, 422);
    }
    var base = { IdRespuesta: responseId, IdEnvioCliente: clientId, IdFormulario: formId, IdRegistroProceso: payload.recordId || payload.IdRegistroProceso || '', EstadoRespuesta: draft ? 'BORRADOR' : 'REGISTRADO', UsuarioRespuesta: user.email, _answers: answers };
    var rows = [];
    visibleQuestions.forEach(function (question) {
      if (TSUtils.normalizeKey(question.Tipo) !== 'SECCION') {
        validateConfiguredAnswer(question, answers[String(question.IdPregunta)]);
        rows = rows.concat(answerRows(question, answers[String(question.IdPregunta)], base));
      }
    });
    TSErrors.assert(rows.length > 0, 'EMPTY_RESPONSE', 'El formulario no contiene respuestas para guardar.', null, 422);
    return TSUtils.withScriptLock(function () {
      if (clientId) {
        var duplicate = TSData.list('RespuestasFormulario', { filters: { IdEnvioCliente: clientId }, limit: 1, cache: false }).rows[0];
        if (duplicate && (String(duplicate.IdRespuesta) !== String(responseId) || (!draft && TSUtils.normalizeKey(duplicate.EstadoRespuesta) === 'REGISTRADO'))) {
          return { id: duplicate.IdRespuesta, status: duplicate.EstadoRespuesta, duplicate: true };
        }
      }
      var existing = TSData.list('RespuestasFormulario', { filters: { IdRespuesta: responseId }, includeDeleted: true, cache: false }).rows;
      if (existing.length) {
        var owns = TSUtils.normalizeEmail(existing[0].UsuarioRespuesta) === user.email;
        TSErrors.assert(owns || TSAuth.can(user, 'FORMULARIOS', 'edit'), 'FORBIDDEN', 'No puede modificar esta respuesta.', null, 403);
      }
      existing.forEach(function (row) {
        if (TSData.isVisible(row, false)) {
          var retired = TSData.updateUnsafe('RespuestasFormulario', row.IdDetalleRespuesta, { Activo: false }, user.email);
          TSAudit.log('UPDATE', 'RespuestasFormulario', row.IdDetalleRespuesta, retired.before, retired.after, user.email, 'Nueva version de respuesta', correlationId);
        }
      });
      var saved = TSData.insertManyUnsafe('RespuestasFormulario', rows, user.email);
      saved.forEach(function (row) { TSAudit.log('CREATE', 'RespuestasFormulario', row.IdDetalleRespuesta, {}, row, user.email, draft ? 'Borrador' : 'Respuesta registrada', correlationId); });
      return { id: responseId, status: base.EstadoRespuesta, answerCount: saved.length, duplicate: false };
    });
  }

  return Object.freeze({
    listPublished: listPublished, listAdmin: listAdmin, definition: definition,
    saveDefinition: saveDefinition, saveQuestion: saveQuestion, duplicateQuestion: duplicateQuestion,
    reorder: reorder, deactivate: deactivate, changeStatus: changeStatus,
    saveResponse: saveResponse, states: FORM_STATES
  });
})();
