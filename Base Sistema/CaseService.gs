var TSCases = (function () {
  function caseCode() {
    var year = Utilities.formatDate(new Date(), TSConfig.get().timeZone, 'yyyy');
    return 'CAS-' + year + '-' + Utilities.getUuid().replace(/-/g, '').substring(0, 10).toUpperCase();
  }

  function saveSensitiveUnsafe(caseId, detail, user, correlationId) {
    if (!detail || typeof detail !== 'object') return null;
    TSErrors.assert(TSAuth.can(user, 'CASOS', 'sensitive'), 'SENSITIVE_FORBIDDEN', 'No tiene permisos para registrar detalle sensible.', null, 403);
    var values = TSValidation.record('DetalleCasosSensibles', detail, Boolean(detail.IdDetalleSensible));
    values.IdCaso = caseId;
    var existing = TSData.list('DetalleCasosSensibles', { filters: { IdCaso: caseId }, includeDeleted: true, cache: false, limit: 1 }).rows[0];
    if (existing) {
      var updated = TSData.updateUnsafe('DetalleCasosSensibles', existing.IdDetalleSensible, values, user.email, detail.expectedVersion);
      TSAudit.log('UPDATE', 'DetalleCasosSensibles', existing.IdDetalleSensible, updated.before, updated.after, user.email, detail.reason || 'Actualizacion de detalle protegido', correlationId);
      return updated.after;
    }
    var created = TSData.insertUnsafe('DetalleCasosSensibles', values, user.email);
    TSAudit.log('CREATE', 'DetalleCasosSensibles', created.IdDetalleSensible, {}, created, user.email, detail.reason || 'Creacion de detalle protegido', correlationId);
    return created;
  }

  function save(payload, correlationId) {
    payload = payload || {};
    var isUpdate = !TSUtils.isBlank(payload.IdCaso);
    var existing = isUpdate ? TSData.findById('Casos', payload.IdCaso, false) : null;
    if (isUpdate) TSErrors.assert(existing, 'CASE_NOT_FOUND', 'Caso no encontrado.', null, 404);
    var values = TSValidation.record('Casos', payload, isUpdate);
    TSProcesses.coerceDates(values);
    values.EstadoCaso = values.EstadoCaso || (existing ? existing.EstadoCaso : 'BORRADOR');
    TSValidation.required(values, ['FechaApertura', 'Responsable', 'EstadoCaso']);
    TSValidation.businessRules('Casos', values);
    TSProcesses.enforceReferences('Casos', values);
    if (!isUpdate) values.CodigoCaso = caseCode();
    else values.CodigoCaso = existing.CodigoCaso;
    var sensitivityProbe = {};
    Object.keys(existing || {}).forEach(function (key) { sensitivityProbe[key] = existing[key]; });
    Object.keys(values).forEach(function (key) { sensitivityProbe[key] = values[key]; });
    var configuredSensitive = TSAuth.isSensitiveCase(sensitivityProbe);
    var hasSensitiveDetail = Boolean(payload.detalleSensible || payload.DetalleSensible);
    if (hasSensitiveDetail) TSErrors.assert(configuredSensitive, 'SENSITIVITY_LEVEL_REQUIRED', 'Seleccione un nivel de sensibilidad configurado como sensible antes de guardar detalle protegido.', null, 422);
    if (existing && TSAuth.isSensitiveCase(existing) && !configuredSensitive) {
      var protectedDetail = TSData.list('DetalleCasosSensibles', { filters: { IdCaso: existing.IdCaso }, includeDeleted: true, limit: 1 }).rows[0];
      TSErrors.assert(!protectedDetail, 'SENSITIVITY_DOWNGRADE_BLOCKED', 'No se puede reducir la sensibilidad mientras exista detalle protegido.', null, 409);
    }
    var sensitive = configuredSensitive;
    var user = TSAuth.authorize('CASOS', isUpdate ? 'edit' : 'create', { sensitive: sensitive });
    var duplicate = TSData.list('Casos', { includeDeleted: true, cache: false, predicate: function (row) { return String(row.CodigoCaso) === String(values.CodigoCaso) && String(row.IdCaso) !== String(payload.IdCaso || ''); }, limit: 1 }).rows[0];
    TSErrors.assert(!duplicate, 'DUPLICATE_CASE_CODE', 'El codigo de caso ya existe.', null, 409);
    return TSUtils.withScriptLock(function () {
      var concurrentDuplicate = TSData.list('Casos', { includeDeleted: true, cache: false, predicate: function (row) { return String(row.CodigoCaso) === String(values.CodigoCaso) && String(row.IdCaso) !== String(payload.IdCaso || ''); }, limit: 1 }).rows[0];
      TSErrors.assert(!concurrentDuplicate, 'DUPLICATE_CASE_CODE', 'El codigo de caso ya existe.', null, 409);
      var record;
      if (isUpdate) {
        var updated = TSData.updateUnsafe('Casos', payload.IdCaso, values, user.email, payload.expectedVersion);
        TSAudit.log('UPDATE', 'Casos', payload.IdCaso, updated.before, updated.after, user.email, payload.reason || 'Edicion de caso', correlationId);
        record = updated.after;
      } else {
        record = TSData.insertUnsafe('Casos', values, user.email);
        TSAudit.log('CREATE', 'Casos', record.IdCaso, {}, record, user.email, payload.reason || 'Apertura de caso', correlationId);
      }
      var detail = saveSensitiveUnsafe(record.IdCaso, payload.detalleSensible || payload.DetalleSensible, user, correlationId);
      return { record: record, sensitiveDetail: detail };
    });
  }

  function ensureCase(caseId, action) {
    var record = TSData.findById('Casos', caseId, false);
    TSErrors.assert(record, 'CASE_NOT_FOUND', 'Caso no encontrado.', null, 404);
    var user = TSAuth.authorize('CASOS', action, { sensitive: TSAuth.isSensitiveCase(record) });
    return { record: record, user: user };
  }

  function saveChild(table, payload, correlationId, updateCasePatch) {
    payload = payload || {};
    TSValidation.required(payload, ['IdCaso']);
    var isUpdate = !TSUtils.isBlank(payload[TSConfig.idFields[table]]);
    var original = isUpdate ? TSData.findById(table, payload[TSConfig.idFields[table]], false) : null;
    if (isUpdate) {
      TSErrors.assert(original, 'NOT_FOUND', 'Registro relacionado no encontrado.', null, 404);
      TSErrors.assert(String(original.IdCaso) === String(payload.IdCaso), 'PARENT_CHANGE_NOT_ALLOWED', 'No se puede cambiar el caso padre de un registro existente.', null, 409);
    }
    var access = ensureCase(payload.IdCaso, 'edit');
    if (original) ensureCase(original.IdCaso, 'edit');
    TSAuth.authorize(TSConfig.tableModules[table], isUpdate ? 'edit' : 'create', { user: access.user, sensitive: TSAuth.isSensitiveCase(access.record) });
    var values = TSValidation.record(table, payload, isUpdate);
    TSProcesses.coerceDates(values);
    TSValidation.required(values, (function () {
      if (table === 'Seguimientos') return ['IdCaso', 'Fecha', 'Responsable', 'Descripcion'];
      if (table === 'Derivaciones') return ['IdCaso', 'Fecha', 'AreaDestino', 'Motivo'];
      if (table === 'Compromisos') return ['IdCaso', 'Responsable', 'Descripcion', 'Estado'];
      return ['IdCaso'];
    })());
    TSValidation.businessRules(table, values);
    if (table === 'Compromisos' && TSUtils.isBlank(values.FechaCreacionCompromiso)) values.FechaCreacionCompromiso = TSUtils.now();
    return TSUtils.withScriptLock(function () {
      var record;
      if (isUpdate) {
        var updated = TSData.updateUnsafe(table, values[TSConfig.idFields[table]], values, access.user.email, payload.expectedVersion);
        TSAudit.log('UPDATE', table, values[TSConfig.idFields[table]], updated.before, updated.after, access.user.email, payload.reason || 'Edicion', correlationId);
        record = updated.after;
      } else {
        record = TSData.insertUnsafe(table, values, access.user.email);
        TSAudit.log('CREATE', table, record[TSConfig.idFields[table]], {}, record, access.user.email, payload.reason || 'Creacion', correlationId);
      }
      if (updateCasePatch) {
        var caseUpdate = TSData.updateUnsafe('Casos', payload.IdCaso, updateCasePatch(record), access.user.email);
        TSAudit.log('UPDATE', 'Casos', payload.IdCaso, caseUpdate.before, caseUpdate.after, access.user.email, 'Actualizacion por ' + table, correlationId);
      }
      return record;
    });
  }

  function followUp(payload, correlationId) {
    return saveChild('Seguimientos', payload, correlationId, function (row) { return { UltimoSeguimiento: row.Fecha }; });
  }

  function referral(payload, correlationId) {
    return saveChild('Derivaciones', payload, correlationId, function () { return { Derivacion: true }; });
  }

  function commitment(payload, correlationId) { return saveChild('Compromisos', payload, correlationId, null); }

  function close(payload, correlationId) {
    payload = payload || {};
    TSValidation.required(payload, ['IdCaso', 'FechaCierreCaso', 'Responsable', 'MotivoCierre']);
    var access = ensureCase(payload.IdCaso, 'edit');
    TSAuth.authorize('CASOS', 'edit', { user: access.user });
    var values = TSValidation.record('Cierres', payload, Boolean(payload.IdCierre));
    if (values.IdCierre) {
      var existingClosure = TSData.findById('Cierres', values.IdCierre, false);
      TSErrors.assert(existingClosure, 'NOT_FOUND', 'Cierre no encontrado.', null, 404);
      TSErrors.assert(String(existingClosure.IdCaso) === String(payload.IdCaso), 'PARENT_CHANGE_NOT_ALLOWED', 'No se puede cambiar el caso padre del cierre.', null, 409);
    }
    TSProcesses.coerceDates(values);
    TSValidation.businessRules('Cierres', values);
    return TSUtils.withScriptLock(function () {
      var currentCase = TSData.findById('Casos', payload.IdCaso, false);
      TSErrors.assert(currentCase, 'CASE_NOT_FOUND', 'Caso no encontrado.', null, 404);
      if (!values.IdCierre) TSErrors.assert(TSUtils.normalizeKey(currentCase.EstadoCaso) !== 'CERRADO', 'CASE_ALREADY_CLOSED', 'El caso ya se encuentra cerrado.', null, 409);
      var closure;
      if (values.IdCierre) {
        var updated = TSData.updateUnsafe('Cierres', values.IdCierre, values, access.user.email, payload.expectedVersion);
        TSAudit.log('UPDATE', 'Cierres', values.IdCierre, updated.before, updated.after, access.user.email, payload.reason || 'Edicion de cierre', correlationId);
        closure = updated.after;
      } else {
        closure = TSData.insertUnsafe('Cierres', values, access.user.email);
        TSAudit.log('CREATE', 'Cierres', closure.IdCierre, {}, closure, access.user.email, payload.reason || 'Cierre de caso', correlationId);
      }
      var caseChange = TSData.updateUnsafe('Casos', payload.IdCaso, { EstadoCaso: 'CERRADO', FechaCierre: values.FechaCierreCaso, MotivoCierre: values.MotivoCierre, Resultado: values.ResultadoFinal || access.record.Resultado }, access.user.email, payload.caseExpectedVersion);
      TSAudit.log('UPDATE', 'Casos', payload.IdCaso, caseChange.before, caseChange.after, access.user.email, payload.reason || 'Cierre de caso', correlationId);
      return { closure: closure, caseRecord: caseChange.after };
    });
  }

  return Object.freeze({ save: save, followUp: followUp, referral: referral, commitment: commitment, close: close });
})();
