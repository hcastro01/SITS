var TSProcesses = (function () {
  var REQUIRED = {
    Personas: ['Nombre'],
    Atenciones: ['Fecha', 'Responsable', 'Motivo'],
    Casos: ['FechaApertura', 'Responsable', 'EstadoCaso'],
    Novedades: ['Fecha', 'Responsable', 'Descripcion', 'Estado'],
    Recorridos: ['Fecha', 'Responsable', 'Objetivo'],
    HallazgosRecorrido: ['IdRecorrido', 'Descripcion'],
    Seguimientos: ['IdCaso', 'Fecha', 'Responsable', 'Descripcion'],
    Derivaciones: ['IdCaso', 'Fecha', 'AreaDestino', 'Motivo'],
    Compromisos: ['IdCaso', 'Responsable', 'Descripcion', 'Estado'],
    Cierres: ['IdCaso', 'FechaCierreCaso', 'Responsable', 'MotivoCierre']
  };

  function resolveTable(value) {
    var normalized = TSUtils.normalizeKey(value);
    var aliases = {
      PERSONA: 'Personas', PERSONAS: 'Personas', ATENCION: 'Atenciones', ATENCIONES: 'Atenciones',
      CASO: 'Casos', CASOS: 'Casos', NOVEDAD: 'Novedades', NOVEDADES: 'Novedades',
      RECORRIDO: 'Recorridos', RECORRIDOS: 'Recorridos', HALLAZGO: 'HallazgosRecorrido',
      HALLAZGOS_RECORRIDO: 'HallazgosRecorrido', SEGUIMIENTO: 'Seguimientos', SEGUIMIENTOS: 'Seguimientos',
      DERIVACION: 'Derivaciones', DERIVACIONES: 'Derivaciones', COMPROMISO: 'Compromisos',
      COMPROMISOS: 'Compromisos', CIERRE: 'Cierres', CIERRES: 'Cierres'
    };
    var table = aliases[normalized] || value;
    TSErrors.assert(TSConfig.processTables.indexOf(table) !== -1, 'INVALID_ENTITY', 'La entidad solicitada no admite esta operacion.', { entity: value }, 400);
    return table;
  }

  function payloadParts(payload) {
    payload = payload || {};
    var table = resolveTable(payload.table || payload.entity || payload.type || payload.TipoRegistro);
    var record = payload.record || payload.data || payload;
    return { table: table, record: record };
  }

  function coerceDates(record) {
    Object.keys(record).forEach(function (field) {
      if (/^Fecha/.test(field) && !TSUtils.isBlank(record[field])) record[field] = TSUtils.asDate(record[field], field);
    });
    return record;
  }

  function enforceReferences(table, record) {
    if (record.IdPersona) TSErrors.assert(TSData.findById('Personas', record.IdPersona, false), 'PERSON_NOT_FOUND', 'La persona seleccionada no existe.', null, 422);
    if (record.IdCaso) TSErrors.assert(TSData.findById('Casos', record.IdCaso, false), 'CASE_NOT_FOUND', 'El caso relacionado no existe.', null, 422);
    if (record.IdRecorrido) TSErrors.assert(TSData.findById('Recorridos', record.IdRecorrido, false), 'TOUR_NOT_FOUND', 'El recorrido relacionado no existe.', null, 422);
    if (record.IdSeguimiento) TSErrors.assert(TSData.findById('Seguimientos', record.IdSeguimiento, false), 'FOLLOW_UP_NOT_FOUND', 'El seguimiento relacionado no existe.', null, 422);
  }

  function save(payload, correlationId) {
    var parts = payloadParts(payload);
    if (parts.table === 'Casos') return TSCases.save(parts.record, correlationId);
    if (parts.table === 'Seguimientos') return TSCases.followUp(parts.record, correlationId);
    if (parts.table === 'Derivaciones') return TSCases.referral(parts.record, correlationId);
    if (parts.table === 'Compromisos') return TSCases.commitment(parts.record, correlationId);
    if (parts.table === 'Cierres') return TSCases.close(parts.record, correlationId);
    var idField = TSConfig.idFields[parts.table];
    var isUpdate = !TSUtils.isBlank(parts.record[idField]);
    var existingRecord = isUpdate ? TSData.findById(parts.table, parts.record[idField], false) : null;
    if (isUpdate) TSErrors.assert(existingRecord, 'NOT_FOUND', 'Registro activo no encontrado.', null, 404);
    var user = TSAuth.authorize(TSConfig.tableModules[parts.table], isUpdate ? 'edit' : 'create');
    var values = TSValidation.record(parts.table, parts.record, isUpdate);
    coerceDates(values);
    TSValidation.required(values, REQUIRED[parts.table] || []);
    TSValidation.businessRules(parts.table, values);
    enforceReferences(parts.table, values);
    if (existingRecord) {
      var originalSensitive = sensitivityAccess(parts.table, existingRecord, user, 'edit');
      if (originalSensitive) TSAuth.authorize(TSConfig.tableModules[parts.table], 'edit', { user: user, sensitive: true });
    }
    var sensitivityProbe = {};
    Object.keys(existingRecord || {}).forEach(function (key) { sensitivityProbe[key] = existingRecord[key]; });
    Object.keys(values).forEach(function (key) { sensitivityProbe[key] = values[key]; });
    var parentSensitive = sensitivityAccess(parts.table, sensitivityProbe, user, 'edit');
    if (parentSensitive) TSAuth.authorize(TSConfig.tableModules[parts.table], isUpdate ? 'edit' : 'create', { user: user, sensitive: true });
    if (parts.table === 'Compromisos' && TSUtils.isBlank(values.FechaCreacionCompromiso)) values.FechaCreacionCompromiso = TSUtils.now();
    return TSUtils.withScriptLock(function () {
      if (isUpdate) {
        var updated = TSData.updateUnsafe(parts.table, values[idField], values, user.email, parts.record.expectedVersion);
        TSAudit.log('UPDATE', parts.table, values[idField], updated.before, updated.after, user.email, parts.record.reason || 'Edicion de registro', correlationId);
        return updated.after;
      }
      var created = TSData.insertUnsafe(parts.table, values, user.email);
      TSAudit.log('CREATE', parts.table, created[idField], {}, created, user.email, parts.record.reason || 'Creacion de registro', correlationId);
      return created;
    });
  }

  function sensitivityAccess(table, record, user, action) {
    var sensitive = TSAuth.isSensitiveRecord(table, record);
    if (sensitive) TSAuth.authorize('CASOS', action === 'read' ? 'read' : 'edit', { user: user, sensitive: true });
    return sensitive;
  }

  function get(payload, correlationId) {
    payload = payload || {};
    var table = resolveTable(payload.table || payload.entity || payload.type);
    var id = payload.id || payload[TSConfig.idFields[table]];
    TSValidation.required({ id: id }, ['id']);
    var user = TSAuth.authorize(TSConfig.tableModules[table], 'read');
    var canReadDeleted = TSAuth.can(user, 'ADMINISTRACION', 'read') || TSAuth.can(user, TSConfig.tableModules[table], 'delete');
    var record = TSData.findById(table, id, Boolean(payload.includeDeleted) && canReadDeleted);
    TSErrors.assert(record, 'NOT_FOUND', 'Registro no encontrado.', null, 404);
    var sensitive = sensitivityAccess(table, record, user, 'read');
    if (sensitive) TSAuth.authorize(TSConfig.tableModules[table], 'read', { user: user, sensitive: true });
    if (sensitive) TSAudit.access('VIEW_SENSITIVE', table, id, user.email, 'Consulta de detalle', correlationId);
    var result = { table: table, record: record, related: {} };
    if (table === 'Casos') {
      if (TSAuth.can(user, 'SEGUIMIENTOS', 'read') && (!sensitive || TSAuth.can(user, 'SEGUIMIENTOS', 'sensitive'))) result.related.followUps = TSData.list('Seguimientos', { filters: { IdCaso: id }, sortBy: 'Fecha', sortDirection: 'desc' }).rows;
      if (TSAuth.can(user, 'DERIVACIONES', 'read') && (!sensitive || TSAuth.can(user, 'DERIVACIONES', 'sensitive'))) result.related.referrals = TSData.list('Derivaciones', { filters: { IdCaso: id }, sortBy: 'Fecha', sortDirection: 'desc' }).rows;
      if (TSAuth.can(user, 'COMPROMISOS', 'read') && (!sensitive || TSAuth.can(user, 'COMPROMISOS', 'sensitive'))) result.related.commitments = TSData.list('Compromisos', { filters: { IdCaso: id }, sortBy: 'FechaLimite' }).rows;
      if (TSAuth.can(user, 'CASOS', 'read') && (!sensitive || TSAuth.can(user, 'CASOS', 'sensitive'))) result.related.closures = TSData.list('Cierres', { filters: { IdCaso: id }, sortBy: 'FechaCierreCaso', sortDirection: 'desc' }).rows;
      if (sensitive && TSAuth.can(user, 'CASOS', 'sensitive')) result.sensitiveDetail = TSData.list('DetalleCasosSensibles', { filters: { IdCaso: id }, limit: 1 }).rows[0] || null;
    }
    return result;
  }

  function remove(payload, correlationId) {
    payload = payload || {};
    var table = resolveTable(payload.table || payload.entity || payload.type);
    var id = payload.id || payload[TSConfig.idFields[table]];
    var existing = TSData.findById(table, id, false);
    TSErrors.assert(existing, 'NOT_FOUND', 'Registro no encontrado.', null, 404);
    var user = TSAuth.authorize(TSConfig.tableModules[table], 'delete');
    var sensitive = sensitivityAccess(table, existing, user, 'edit');
    if (sensitive) TSAuth.authorize(TSConfig.tableModules[table], 'delete', { user: user, sensitive: true });
    return TSUtils.withScriptLock(function () {
      var changed = TSData.softDeleteUnsafe(table, id, user.email, payload.reason || payload.motivo);
      TSAudit.log('DELETE', table, id, changed.before, changed.after, user.email, payload.reason || payload.motivo, correlationId);
      return changed.after;
    });
  }

  function restore(payload, correlationId) {
    payload = payload || {};
    var table = resolveTable(payload.table || payload.entity || payload.type);
    var id = payload.id || payload[TSConfig.idFields[table]];
    var existing = TSData.findById(table, id, true);
    TSErrors.assert(existing && TSUtils.toBoolean(existing.Eliminado), 'NOT_FOUND', 'Registro eliminado no encontrado.', null, 404);
    var user = TSAuth.authorize(TSConfig.tableModules[table], 'delete');
    var sensitive = sensitivityAccess(table, existing, user, 'edit');
    if (sensitive) TSAuth.authorize(TSConfig.tableModules[table], 'delete', { user: user, sensitive: true });
    return TSUtils.withScriptLock(function () {
      var changed = TSData.restoreUnsafe(table, id, user.email);
      TSAudit.log('RESTORE', table, id, changed.before, changed.after, user.email, payload.reason || 'Restauracion', correlationId);
      return changed.after;
    });
  }

  function history(payload) {
    payload = payload || {};
    var table = resolveTable(payload.table || payload.entity || payload.type);
    var id = payload.id || payload[TSConfig.idFields[table]];
    var record = TSData.findById(table, id, true);
    TSErrors.assert(record, 'NOT_FOUND', 'Registro no encontrado.', null, 404);
    var user = TSAuth.authorize(TSConfig.tableModules[table], 'read');
    if (TSUtils.toBoolean(record.Eliminado)) TSErrors.assert(TSAuth.can(user, 'ADMINISTRACION', 'read') || TSAuth.can(user, TSConfig.tableModules[table], 'delete'), 'FORBIDDEN', 'No tiene permisos para consultar historiales eliminados.', null, 403);
    var sensitive = sensitivityAccess(table, record, user, 'read');
    if (sensitive) TSAuth.authorize(TSConfig.tableModules[table], 'read', { user: user, sensitive: true });
    return TSAudit.history(table, id);
  }

  function dependencyCount(table, id) {
    var checks = {
      Personas: [['Atenciones', 'IdPersona'], ['Casos', 'IdPersona']],
      Casos: [['DetalleCasosSensibles', 'IdCaso'], ['Seguimientos', 'IdCaso'], ['Derivaciones', 'IdCaso'], ['Compromisos', 'IdCaso'], ['Cierres', 'IdCaso'], ['HallazgosRecorrido', 'IdCaso']],
      Recorridos: [['HallazgosRecorrido', 'IdRecorrido']],
      Seguimientos: [['Compromisos', 'IdSeguimiento']],
      Novedades: [['HallazgosRecorrido', 'IdNovedad']]
    };
    var count = 0;
    (checks[table] || []).forEach(function (check) { count += TSData.list(check[0], { includeDeleted: true, filters: (function () { var f = {}; f[check[1]] = id; return f; })() }).total; });
    count += TSData.list('Documentos', { includeDeleted: true, filters: { TipoRegistro: table, IdRegistro: id } }).total;
    return count;
  }

  function hardRemove(payload, correlationId) {
    payload = payload || {};
    TSErrors.assert(TSConfig.get().allowHardDelete, 'HARD_DELETE_DISABLED', 'La eliminacion definitiva no esta habilitada.', null, 403);
    var table = resolveTable(payload.table || payload.entity || payload.type);
    var id = payload.id || payload[TSConfig.idFields[table]];
    TSValidation.required({ id: id, reason: payload.reason, confirmation: payload.confirmation }, ['id', 'reason', 'confirmation']);
    TSErrors.assert(String(payload.confirmation) === 'BORRAR:' + String(id), 'HARD_DELETE_CONFIRMATION', 'La confirmacion de eliminacion definitiva no coincide.', null, 422);
    var user = TSAuth.authorize('ADMINISTRACION', 'edit');
    TSAuth.authorize(TSConfig.tableModules[table], 'delete', { user: user });
    var existing = TSData.findById(table, id, true);
    TSErrors.assert(existing && TSUtils.toBoolean(existing.Eliminado), 'HARD_DELETE_REQUIRES_SOFT_DELETE', 'El registro debe estar eliminado logicamente antes de su eliminacion definitiva.', null, 409);
    var sensitive = sensitivityAccess(table, existing, user, 'edit');
    if (sensitive) TSAuth.authorize(TSConfig.tableModules[table], 'delete', { user: user, sensitive: true });
    TSErrors.assert(dependencyCount(table, id) === 0, 'RECORD_HAS_DEPENDENCIES', 'No se puede eliminar definitivamente porque existen registros o documentos relacionados.', null, 409);
    return TSUtils.withScriptLock(function () {
      TSErrors.assert(dependencyCount(table, id) === 0, 'RECORD_HAS_DEPENDENCIES', 'El registro adquirio dependencias; la eliminacion fue cancelada.', null, 409);
      TSAudit.log('DELETE', table, id, existing, {}, user.email, 'BORRADO DEFINITIVO AUTORIZADO: ' + TSUtils.cleanText(payload.reason, 1500), correlationId);
      TSData.hardDeleteUnsafe(table, id);
      return { id: id, table: table, permanentlyDeleted: true };
    });
  }

  return Object.freeze({ resolveTable: resolveTable, save: save, get: get, remove: remove, restore: restore, history: history, hardRemove: hardRemove, coerceDates: coerceDates, enforceReferences: enforceReferences });
})();
