var TSValidation = (function () {
  var QUESTION_TYPES = [
    'TEXTO_CORTO', 'TEXTO_LARGO', 'NUMERO', 'FECHA', 'FECHA_HORA', 'HORA', 'SI_NO',
    'LISTA_DESPLEGABLE', 'SELECCION_UNICA', 'SELECCION_MULTIPLE', 'ESCALA_LIKERT',
    'PERSONA', 'AREA', 'TURNO', 'ARCHIVO', 'FOTOGRAFIA', 'PDF', 'DOCUMENTO',
    'CAMPO_CALCULADO', 'CAMPO_OCULTO', 'SECCION'
  ];

  function required(object, fields, labelMap) {
    var missing = [];
    object = object || {};
    fields.forEach(function (field) {
      if (TSUtils.isBlank(object[field])) missing.push((labelMap && labelMap[field]) || field);
    });
    if (missing.length) throw new TSAppError('VALIDATION_ERROR', 'Complete los campos obligatorios.', { fields: missing }, 422);
  }

  function table(table) {
    TSErrors.assert(Object.prototype.hasOwnProperty.call(TSConfig.schemas, table), 'INVALID_TABLE', 'La entidad solicitada no esta permitida.', { table: table }, 400);
    return table;
  }

  function record(tableName, input, isUpdate) {
    table(tableName);
    TSErrors.assert(input && typeof input === 'object' && !Array.isArray(input), 'INVALID_PAYLOAD', 'Los datos enviados no son validos.', null, 400);
    var idField = TSConfig.idFields[tableName];
    if (isUpdate) required(input, [idField]);
    var sanitized = TSUtils.pick(input, TSConfig.schema(tableName));
    Object.keys(sanitized).forEach(function (key) {
      if (typeof sanitized[key] === 'string') sanitized[key] = TSUtils.cleanText(sanitized[key], 50000);
    });
    return sanitized;
  }

  function question(input) {
    input = input || {};
    required(input, ['IdFormulario', 'Etiqueta', 'Tipo']);
    var type = TSUtils.normalizeKey(input.Tipo);
    TSErrors.assert(QUESTION_TYPES.indexOf(type) !== -1, 'INVALID_QUESTION_TYPE', 'El tipo de pregunta no es valido.', { type: input.Tipo }, 422);
    if (!TSUtils.isBlank(input.LongitudMaxima)) {
      var max = Number(input.LongitudMaxima);
      TSErrors.assert(isFinite(max) && max > 0 && max <= 50000, 'INVALID_MAX_LENGTH', 'La longitud maxima no es valida.', null, 422);
    }
    input.Tipo = type;
    return record('Preguntas', input, Boolean(input.IdPregunta));
  }

  function file(file) {
    file = file || {};
    required(file, ['name', 'mimeType', 'base64']);
    var config = TSConfig.get();
    var name = TSUtils.safeFileName(file.name);
    var extMatch = name.toLowerCase().match(/\.([a-z0-9]+)$/);
    var extension = extMatch ? extMatch[1] : '';
    TSErrors.assert(config.allowedExtensions.indexOf(extension) !== -1, 'FILE_EXTENSION_NOT_ALLOWED', 'El tipo de archivo no esta permitido.', { extension: extension }, 422);
    TSErrors.assert(config.allowedMimeTypes.indexOf(String(file.mimeType).toLowerCase()) !== -1, 'FILE_MIME_NOT_ALLOWED', 'El formato del archivo no esta permitido.', { mimeType: file.mimeType }, 422);
    var raw = String(file.base64 || '').replace(/^data:[^;]+;base64,/, '').replace(/\s/g, '');
    var estimated = Math.floor(raw.length * 3 / 4);
    TSErrors.assert(estimated > 0 && estimated <= config.maxFileBytes, 'FILE_TOO_LARGE', 'El archivo supera el tamano permitido.', { maxBytes: config.maxFileBytes }, 422);
    return { name: name, mimeType: String(file.mimeType).toLowerCase(), extension: extension, base64: raw, estimatedBytes: estimated, category: TSUtils.cleanText(file.category || file.categoriaDocumento || '', 120), sensitivity: TSUtils.cleanText(file.sensitivity || file.sensibilidad || '', 120) };
  }

  function businessRules(tableName, record) {
    record = record || {};
    if (tableName === 'Casos') {
      var closed = TSUtils.normalizeKey(record.EstadoCaso) === 'CERRADO';
      if (closed) required(record, ['FechaCierre', 'MotivoCierre']);
      if (TSUtils.toBoolean(record.Restriccion)) required(record, ['FechaInicioRestriccion']);
    }
    if (tableName === 'Derivaciones') required(record, ['IdCaso', 'AreaDestino', 'Motivo']);
    if (tableName === 'Compromisos') required(record, ['IdCaso', 'Responsable', 'Estado', 'Descripcion']);
    if (tableName === 'Seguimientos' && !TSUtils.isBlank(record.ProximaAccion)) required(record, ['FechaProximaAccion']);
    if (tableName === 'Cierres') required(record, ['IdCaso', 'FechaCierreCaso', 'MotivoCierre']);
    if (tableName === 'HallazgosRecorrido') required(record, ['IdRecorrido', 'Descripcion']);
    return record;
  }

  function pagination(input) {
    input = input || {};
    var config = TSConfig.get();
    var page = Math.max(1, parseInt(input.page, 10) || 1);
    var pageSize = Math.max(1, Math.min(config.maxPageSize, parseInt(input.pageSize, 10) || config.pageSize));
    return { page: page, pageSize: pageSize, offset: (page - 1) * pageSize };
  }

  return Object.freeze({ required: required, table: table, record: record, question: question, file: file, businessRules: businessRules, pagination: pagination, questionTypes: QUESTION_TYPES });
})();
