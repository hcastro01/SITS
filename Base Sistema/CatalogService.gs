var TSCatalog = (function () {
  var TYPE_ALIASES = {
    TIPOATENCION: 'TIPO_ATENCION', TIPOCASO: 'TIPO_CASO', SUBTIPOCASO: 'SUBTIPO_CASO',
    NIVELSENSIBILIDAD: 'NIVEL_SENSIBILIDAD', ESTADOCASO: 'ESTADO_CASO', TIPOGESTION: 'TIPO_GESTION',
    TECNICAINSTRUMENTO: 'TECNICA_INSTRUMENTO', TIPONOVEDAD: 'TIPO_NOVEDAD', TIPORECORRIDO: 'TIPO_RECORRIDO',
    TIPOHALLAZGO: 'TIPO_HALLAZGO', CONDICIONLABORAL: 'CONDICION_LABORAL', TIPODERIVACION: 'TIPO_DERIVACION',
    ESTADODERIVACION: 'ESTADO_DERIVACION', ESTADOCOMPROMISO: 'ESTADO_COMPROMISO', MOTIVOCIERRE: 'MOTIVO_CIERRE',
    TIPODOCUMENTO: 'TIPO_DOCUMENTO', ESTADOFORMULARIO: 'ESTADO_FORMULARIO'
  };
  var USAGE = {
    TIPO_ATENCION: [['Atenciones', 'TipoAtencion']], TIPO_CASO: [['Casos', 'TipoCaso']],
    SUBTIPO_CASO: [['Casos', 'SubtipoCaso']], PRIORIDAD: [['Casos', 'Prioridad'], ['Novedades', 'Prioridad'], ['HallazgosRecorrido', 'Prioridad']],
    NIVEL_SENSIBILIDAD: [['Casos', 'NivelSensibilidad']], ESTADO_CASO: [['Casos', 'EstadoCaso']],
    TIPO_GESTION: [['Casos', 'TipoGestion']], TECNICA_INSTRUMENTO: [['Seguimientos', 'Tecnica']],
    TIPO_NOVEDAD: [['Novedades', 'Tipo']], TIPO_HALLAZGO: [['HallazgosRecorrido', 'TipoHallazgo']],
    AREA: [['Personas', 'Area'], ['Casos', 'Area'], ['Novedades', 'Area'], ['Recorridos', 'Area'], ['HallazgosRecorrido', 'Area']],
    TURNO: [['Personas', 'Turno'], ['Casos', 'Turno'], ['Novedades', 'Turno'], ['Recorridos', 'Turno']],
    CONDICION_LABORAL: [['Personas', 'EstadoLaboral'], ['Casos', 'CondicionLaboral']],
    ESTADO_DERIVACION: [['Derivaciones', 'Estado']], ESTADO_COMPROMISO: [['Compromisos', 'Estado']],
    MOTIVO_CIERRE: [['Cierres', 'MotivoCierre'], ['Casos', 'MotivoCierre']], TIPO_DOCUMENTO: [['Documentos', 'CategoriaDocumento']]
  };

  function normalizeType(value) {
    var normalized = TSUtils.normalizeKey(value);
    return TYPE_ALIASES[normalized.replace(/_/g, '')] || normalized;
  }

  function isUsed(item) {
    var mappings = USAGE[normalizeType(item.Tipo)] || [];
    var code = TSUtils.normalizeKey(item.Codigo);
    var label = TSUtils.normalizeKey(item.Valor);
    return mappings.some(function (mapping) {
      return TSData.list(mapping[0], { includeDeleted: true, predicate: function (row) {
        var value = TSUtils.normalizeKey(row[mapping[1]]);
        return value && (value === code || value === label);
      }, limit: 1 }).total > 0;
    });
  }
  function list(options) {
    var user = TSAuth.authorize('CATALOGOS', 'read');
    options = options || {};
    if (options.includeInactive) TSErrors.assert(TSAuth.can(user, 'CATALOGOS', 'edit'), 'FORBIDDEN', 'No tiene permisos para consultar catalogos inactivos.', null, 403);
    var rows = TSData.list('Catalogos', {
      includeDeleted: Boolean(options.includeInactive),
      predicate: function (row) {
        if (options.type && normalizeType(row.Tipo) !== normalizeType(options.type)) return false;
        if (!options.includeInactive && (!TSUtils.toBoolean(row.Activo) || TSUtils.toBoolean(row.Eliminado))) return false;
        return true;
      }, sortBy: 'Orden'
    }).rows;
    var grouped = {};
    rows.forEach(function (row) {
      var key = TSUtils.normalizeKey(row.Tipo);
      if (!grouped[key]) grouped[key] = [];
      grouped[key].push(row);
    });
    return { items: rows, grouped: grouped };
  }

  function save(payload, correlationId) {
    var user = TSAuth.authorize('CATALOGOS', payload && payload.IdCatalogo ? 'edit' : 'create');
    payload = payload || {};
    TSValidation.required(payload, ['Tipo', 'Codigo', 'Valor']);
    var values = TSValidation.record('Catalogos', payload, Boolean(payload.IdCatalogo));
    values.Tipo = normalizeType(values.Tipo);
    values.Codigo = TSUtils.normalizeKey(values.Codigo);
    values.Orden = Number(values.Orden) || 0;
    values.EsSensible = TSUtils.toBoolean(values.EsSensible);
    var duplicate = TSData.list('Catalogos', {
      includeDeleted: true, cache: false,
      predicate: function (row) { return TSUtils.normalizeKey(row.Tipo) === values.Tipo && TSUtils.normalizeKey(row.Codigo) === values.Codigo && String(row.IdCatalogo) !== String(values.IdCatalogo || ''); }, limit: 1
    }).rows[0];
    TSErrors.assert(!duplicate, 'DUPLICATE_CATALOG', 'Ya existe un elemento con ese tipo y codigo.', null, 409);
    if (values.IdCatalogo) {
      var current = TSData.findById('Catalogos', values.IdCatalogo, true);
      TSErrors.assert(current, 'NOT_FOUND', 'Elemento de catalogo no encontrado.', null, 404);
      if (!Object.prototype.hasOwnProperty.call(payload, 'EsSensible')) values.EsSensible = TSUtils.toBoolean(current.EsSensible);
      if (isUsed(current)) {
        var identityChanged = normalizeType(current.Tipo) !== values.Tipo || TSUtils.normalizeKey(current.Codigo) !== values.Codigo || String(current.Valor) !== String(values.Valor);
        var sensitivityReduced = TSUtils.toBoolean(current.EsSensible) && !TSUtils.toBoolean(values.EsSensible);
        TSErrors.assert(!identityChanged && !sensitivityReduced, 'CATALOG_IN_USE', 'No se puede cambiar la identidad o reducir la sensibilidad de un catalogo utilizado. Desactivelo o cree otro elemento.', null, 409);
      }
    }
    return TSUtils.withScriptLock(function () {
      var concurrentDuplicate = TSData.list('Catalogos', {
        includeDeleted: true, cache: false,
        predicate: function (row) { return normalizeType(row.Tipo) === values.Tipo && TSUtils.normalizeKey(row.Codigo) === values.Codigo && String(row.IdCatalogo) !== String(values.IdCatalogo || ''); }, limit: 1
      }).rows[0];
      TSErrors.assert(!concurrentDuplicate, 'DUPLICATE_CATALOG', 'Ya existe un elemento con ese tipo y codigo.', null, 409);
      if (values.IdCatalogo) {
        var updated = TSData.updateUnsafe('Catalogos', values.IdCatalogo, values, user.email, payload.expectedVersion);
        TSAudit.log('UPDATE', 'Catalogos', values.IdCatalogo, updated.before, updated.after, user.email, payload.reason || 'Edicion de catalogo', correlationId);
        return updated.after;
      }
      var created = TSData.insertUnsafe('Catalogos', values, user.email);
      TSAudit.log('CREATE', 'Catalogos', created.IdCatalogo, {}, created, user.email, payload.reason || 'Alta de catalogo', correlationId);
      return created;
    });
  }

  function toggle(id, active, reason, correlationId) {
    var user = TSAuth.authorize('CATALOGOS', 'edit');
    var existing = TSData.findById('Catalogos', id, true);
    TSErrors.assert(existing, 'NOT_FOUND', 'Elemento de catalogo no encontrado.', null, 404);
    return TSUtils.withScriptLock(function () {
      var updated = TSData.updateUnsafe('Catalogos', id, { Activo: TSUtils.toBoolean(active), Eliminado: false }, user.email);
      TSAudit.log('UPDATE', 'Catalogos', id, updated.before, updated.after, user.email, reason || (TSUtils.toBoolean(active) ? 'Activacion' : 'Desactivacion'), correlationId);
      return updated.after;
    });
  }

  function dependent(payload) {
    TSAuth.authorize('CATALOGOS', 'read');
    payload = payload || {};
    TSValidation.required(payload, ['type']);
    return TSData.list('Catalogos', {
      predicate: function (row) {
        if (normalizeType(row.Tipo) !== normalizeType(payload.type)) return false;
        if (payload.parentId && String(row.IdCatalogoPadre) !== String(payload.parentId)) return false;
        if (payload.parentCode && TSUtils.normalizeKey(row.CodigoPadre) !== TSUtils.normalizeKey(payload.parentCode)) return false;
        if (payload.parentType && TSUtils.normalizeKey(row.TipoPadre) !== TSUtils.normalizeKey(payload.parentType)) return false;
        return true;
      }, sortBy: 'Orden'
    }).rows;
  }

  return Object.freeze({ list: list, save: save, toggle: toggle, dependent: dependent, normalizeType: normalizeType });
})();
