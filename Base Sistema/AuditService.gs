var TSAudit = (function () {
  var ACTIONS = ['CREATE', 'UPDATE', 'DELETE', 'RESTORE', 'VIEW_SENSITIVE', 'DOWNLOAD_FILE', 'IMPORT', 'LOGIN'];
  var SENSITIVE_FIELDS = /cedula|sensible|diagnostico|antecedente|notaprivada|descripcionSensible/i;
  var CASE_PRIVATE_FIELDS = { IdPersona: true, Colaborador: true, Motivo: true, Resultado: true, Observaciones: true, Evidencias: true };
  var SENSITIVE_ALLOWED_FIELDS = /^(Id[A-Za-z]+|CodigoCaso|Estado|EstadoCaso|Prioridad|NivelSensibilidad|Fecha[A-Za-z]*|Activo|Eliminado|Version)$/;

  function safeValue(table, field, value, sensitiveRecord) {
    var protectedResponse = table === 'RespuestasFormulario' && /^Valor/.test(field || '');
    var protectedDocument = table === 'Documentos' && ['DriveFileId', 'Url', 'NombreArchivo'].indexOf(field) !== -1;
    var protectedSensitiveRecord = sensitiveRecord && !SENSITIVE_ALLOWED_FIELDS.test(field || '');
    if (table === 'DetalleCasosSensibles' || SENSITIVE_FIELDS.test(field || '') || (table === 'Casos' && CASE_PRIVATE_FIELDS[field]) || protectedResponse || protectedDocument || protectedSensitiveRecord) return TSUtils.isBlank(value) ? '' : '[VALOR SENSIBLE MODIFICADO]';
    var serialized = TSUtils.toSerializable(value);
    if (serialized && typeof serialized === 'object') serialized = JSON.stringify(serialized);
    return TSUtils.cleanText(serialized, 45000);
  }

  function appendRows(rows) {
    if (!rows.length) return [];
    return TSData.insertManyUnsafe('Auditoria', rows, '');
  }

  function log(action, table, id, before, after, userEmail, reason, correlationId) {
    action = TSUtils.normalizeKey(action);
    TSErrors.assert(ACTIONS.indexOf(action) !== -1, 'INVALID_AUDIT_ACTION', 'Accion de auditoria invalida.', null, 400);
    before = before || {};
    after = after || {};
    var sensitivityProbe = Object.keys(after).length ? after : before;
    var sensitiveRecord = false;
    try { sensitiveRecord = TSAuth.isSensitiveRecord(table, sensitivityProbe); } catch (ignore) {}
    var fields = {};
    Object.keys(before).concat(Object.keys(after)).forEach(function (field) {
      if (field !== '_rowNumber') fields[field] = true;
    });
    var rows = [];
    Object.keys(fields).forEach(function (field) {
      if (action === 'UPDATE' && TSUtils.valuesEqual(before[field], after[field])) return;
      rows.push({
        IdAuditoria: TSUtils.uuid('AUD'), Tabla: table, IdRegistro: id, Accion: action,
        Usuario: userEmail || '', FechaHora: TSUtils.now(), Campo: field,
        ValorAnterior: safeValue(table, field, before[field], sensitiveRecord), ValorNuevo: safeValue(table, field, after[field], sensitiveRecord),
        Motivo: TSUtils.cleanText(reason || '', 2000), CorrelationId: correlationId || ''
      });
    });
    if (!rows.length) {
      rows.push({ IdAuditoria: TSUtils.uuid('AUD'), Tabla: table, IdRegistro: id, Accion: action, Usuario: userEmail || '', FechaHora: TSUtils.now(), Campo: '*', ValorAnterior: '', ValorNuevo: '', Motivo: TSUtils.cleanText(reason || '', 2000), CorrelationId: correlationId || '' });
    }
    return appendRows(rows);
  }

  function access(action, table, id, userEmail, reason, correlationId) {
    return TSUtils.withScriptLock(function () { return log(action, table, id, {}, {}, userEmail, reason, correlationId); });
  }

  function history(table, id) {
    return TSData.list('Auditoria', {
      cache: false,
      predicate: function (row) { return String(row.Tabla) === String(table) && String(row.IdRegistro) === String(id); },
      sortBy: 'FechaHora', sortDirection: 'desc'
    }).rows;
  }

  function batchActionUnsafe(action, table, records, userEmail, reason, correlationId) {
    action = TSUtils.normalizeKey(action);
    TSErrors.assert(ACTIONS.indexOf(action) !== -1, 'INVALID_AUDIT_ACTION', 'Accion de auditoria invalida.', null, 400);
    var idField = TSConfig.idFields[table];
    return appendRows((records || []).map(function (record) {
      return {
        IdAuditoria: TSUtils.uuid('AUD'), Tabla: table, IdRegistro: record[idField], Accion: action,
        Usuario: userEmail || '', FechaHora: TSUtils.now(), Campo: '*', ValorAnterior: '',
        ValorNuevo: action === 'IMPORT' ? '[REGISTRO IMPORTADO]' : '',
        Motivo: TSUtils.cleanText(reason || '', 2000), CorrelationId: correlationId || ''
      };
    }));
  }

  return Object.freeze({ log: log, access: access, history: history, batchActionUnsafe: batchActionUnsafe, actions: ACTIONS });
})();
