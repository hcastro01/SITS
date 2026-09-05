var TSSearch = (function () {
  var SEARCH_FIELDS = {
    Personas: ['CodigoEmpleado', 'Cedula', 'Nombre', 'Cargo', 'Area', 'Departamento', 'Centro', 'SubCentro', 'Turno', 'EstadoLaboral'],
    Atenciones: ['IdAtencion', 'Colaborador', 'Responsable', 'TipoAtencion', 'Motivo', 'Canal', 'Gestion', 'Resultado', 'Observaciones', 'Estado'],
    Casos: ['IdCaso', 'CodigoCaso', 'Colaborador', 'Responsable', 'TipoCaso', 'SubtipoCaso', 'Prioridad', 'EstadoCaso', 'TipoGestion', 'TipoEvento', 'Area', 'Turno', 'Resultado'],
    Novedades: ['IdNovedad', 'Responsable', 'Fuente', 'Tipo', 'Subtipo', 'Area', 'Turno', 'Lugar', 'Descripcion', 'Impacto', 'Prioridad', 'AccionInmediata', 'Estado'],
    Recorridos: ['IdRecorrido', 'Responsable', 'Planta', 'Area', 'Turno', 'Objetivo', 'Observaciones', 'Acciones'],
    HallazgosRecorrido: ['IdHallazgo', 'IdRecorrido', 'TipoHallazgo', 'Categoria', 'Subcategoria', 'Area', 'Descripcion', 'Prioridad', 'Accion', 'Estado'],
    Seguimientos: ['IdSeguimiento', 'IdCaso', 'Responsable', 'TipoSeguimiento', 'Canal', 'Tecnica', 'Descripcion', 'Resultado', 'ProximaAccion', 'Estado'],
    Derivaciones: ['IdDerivacion', 'IdCaso', 'AreaDestino', 'ResponsableDestino', 'Motivo', 'Estado', 'Resultado', 'Observaciones'],
    Compromisos: ['IdCompromiso', 'IdCaso', 'IdSeguimiento', 'Responsable', 'Descripcion', 'Estado', 'Observacion'],
    Cierres: ['IdCierre', 'IdCaso', 'Responsable', 'MotivoCierre', 'ResultadoFinal', 'Observacion'],
    Documentos: ['IdArchivo', 'IdRegistro', 'TipoRegistro', 'NombreArchivo', 'MimeType', 'Extension', 'CategoriaDocumento', 'Sensibilidad', 'UsuarioCarga']
  };

  var DATE_FIELDS = {
    Personas: 'FechaCreacion', Atenciones: 'Fecha', Casos: 'FechaApertura', Novedades: 'Fecha',
    Recorridos: 'Fecha', HallazgosRecorrido: 'FechaCreacion', Seguimientos: 'Fecha',
    Derivaciones: 'Fecha', Compromisos: 'FechaLimite', Cierres: 'FechaCierreCaso', Documentos: 'FechaCarga'
  };

  function requestedTables(filters) {
    var raw = filters.tables || filters.table || filters.entity;
    var values = Array.isArray(raw) ? raw : raw ? [raw] : ['Casos', 'Atenciones', 'Novedades', 'Recorridos', 'Seguimientos', 'Derivaciones', 'Compromisos'];
    var unique = {};
    values.forEach(function (value) {
      if (TSUtils.normalizeKey(value) === 'DOCUMENTOS' || TSUtils.normalizeKey(value) === 'DOCUMENTO') unique.Documentos = true;
      else try { unique[TSProcesses.resolveTable(value)] = true; } catch (ignore) {}
    });
    return Object.keys(unique);
  }

  function personIndex(user) {
    var index = {};
    if (!TSAuth.can(user, 'PERSONAS', 'read')) return index;
    TSData.list('Personas', {}).rows.forEach(function (person) { index[String(person.IdPersona)] = person; });
    return index;
  }

  function dateValue(value) {
    if (TSUtils.isBlank(value)) return null;
    try { return TSUtils.asDate(value).getTime(); } catch (ignore) { return null; }
  }

  function matches(table, row, filters, people) {
    var q = TSUtils.cleanText(filters.q || filters.query || filters.text || '', 500).toLowerCase();
    if (q) {
      var haystack = (SEARCH_FIELDS[table] || []).map(function (field) { return String(row[field] || ''); });
      if (row.IdPersona && people[String(row.IdPersona)]) {
        var person = people[String(row.IdPersona)];
        haystack.push(person.Cedula || '', person.CodigoEmpleado || '', person.Nombre || '');
      }
      if (haystack.join(' ').toLowerCase().indexOf(q) === -1) return false;
    }
    var mappings = {
      responsible: ['Responsable', 'ResponsableDestino'], responsable: ['Responsable', 'ResponsableDestino'],
      area: ['Area', 'AreaDestino'], status: ['Estado', 'EstadoCaso'], estado: ['Estado', 'EstadoCaso'],
      type: ['Tipo', 'TipoCaso', 'TipoAtencion', 'TipoHallazgo'], tipo: ['Tipo', 'TipoCaso', 'TipoAtencion', 'TipoHallazgo'],
      priority: ['Prioridad'], prioridad: ['Prioridad'], sensitivity: ['NivelSensibilidad'], sensibilidad: ['NivelSensibilidad'],
      collaborator: ['Colaborador'], colaborador: ['Colaborador'], code: ['CodigoCaso'], codigo: ['CodigoCaso']
    };
    var passed = Object.keys(mappings).every(function (filterKey) {
      var expected = filters[filterKey];
      if (TSUtils.isBlank(expected)) return true;
      return mappings[filterKey].some(function (field) { return !TSUtils.isBlank(row[field]) && String(row[field]).toLowerCase() === String(expected).toLowerCase(); });
    });
    if (!passed) return false;
    var from = dateValue(filters.dateFrom || filters.fechaDesde);
    var to = dateValue(filters.dateTo || filters.fechaHasta);
    var rowDate = dateValue(row[DATE_FIELDS[table]]);
    if (from !== null && (rowDate === null || rowDate < from)) return false;
    if (to !== null) {
      var inclusiveTo = to + 24 * 60 * 60 * 1000 - 1;
      if (rowDate === null || rowDate > inclusiveTo) return false;
    }
    return true;
  }

  function parentSensitive(table, row, cases) {
    if (table === 'Casos') return TSAuth.isSensitiveCase(row);
    if (['Seguimientos', 'Derivaciones', 'Compromisos', 'Cierres'].indexOf(table) !== -1 && row.IdCaso) {
      var parent = cases[String(row.IdCaso)];
      return parent ? TSAuth.isSensitiveCase(parent) : false;
    }
    if (table === 'Documentos') {
      if (!TSUtils.isBlank(row.Sensibilidad)) return true;
      if (TSUtils.normalizeKey(row.TipoRegistro) === 'CASOS' && cases[String(row.IdRegistro)]) return TSAuth.isSensitiveCase(cases[String(row.IdRegistro)]);
      return TSAuth.isSensitiveRecord(table, row);
    }
    return false;
  }

  function actionsFor(user, table, sensitive) {
    var module = TSConfig.tableModules[table];
    var allowedSensitive = !sensitive || TSAuth.can(user, module, 'sensitive') || (module !== 'CASOS' && TSAuth.can(user, 'CASOS', 'sensitive'));
    return {
      view: TSAuth.can(user, module, 'read') && allowedSensitive,
      edit: TSAuth.can(user, module, 'edit') && allowedSensitive,
      delete: TSAuth.can(user, module, 'delete') && allowedSensitive,
      followUp: table === 'Casos' && TSAuth.can(user, 'SEGUIMIENTOS', 'create') && allowedSensitive,
      attach: table !== 'Documentos' && TSAuth.can(user, module, 'edit') && TSAuth.can(user, 'DOCUMENTOS', 'create') && allowedSensitive,
      history: TSAuth.can(user, module, 'read') && allowedSensitive,
      close: table === 'Casos' && TSAuth.can(user, 'CASOS', 'edit') && allowedSensitive
    };
  }

  function search(filters, options) {
    filters = filters || {};
    options = options || {};
    var user = TSAuth.authorize('BUSQUEDA', 'read');
    var tables = requestedTables(filters);
    var people = personIndex(user);
    var cases = {};
    var maySeeAnyDeleted = TSAuth.can(user, 'ADMINISTRACION', 'read');
    TSData.list('Casos', { includeDeleted: true }).rows.forEach(function (row) { cases[String(row.IdCaso)] = row; });
    var items = [];
    tables.forEach(function (table) {
      var module = TSConfig.tableModules[table];
      if (!TSAuth.can(user, module, 'read')) return;
      var includeDeleted = Boolean(filters.includeDeleted) && (maySeeAnyDeleted || TSAuth.can(user, module, 'delete'));
      TSData.list(table, { includeDeleted: includeDeleted }).rows.forEach(function (row) {
        var sensitive = parentSensitive(table, row, cases);
        var canSensitive = !sensitive || TSAuth.can(user, module, 'sensitive') || TSAuth.can(user, 'CASOS', 'sensitive');
        var candidate = canSensitive ? row : TSAuth.maskSensitive(row);
        if (!matches(table, candidate, filters, canSensitive ? people : {})) return;
        var record = TSUtils.clone(candidate);
        if (table === 'Documentos') { delete record.DriveFileId; delete record.Url; }
        var idField = TSConfig.idFields[table];
        items.push({ table: table, id: row[idField], date: row[DATE_FIELDS[table]] || row.FechaCreacion || '', sensitive: sensitive, restricted: sensitive && !canSensitive, record: record, actions: actionsFor(user, table, sensitive) });
      });
    });
    items.sort(function (a, b) { return (dateValue(b.date) || 0) - (dateValue(a.date) || 0); });
    var total = items.length;
    if (options.exportMode) {
      var max = TSConfig.get().maxExportRows;
      return { items: items.slice(0, max), total: total, truncated: total > max, page: 1, pageSize: Math.min(total, max), totalPages: 1 };
    }
    var paging = TSValidation.pagination(filters);
    var paged = items.slice(paging.offset, paging.offset + paging.pageSize);
    return { items: paged, total: total, page: paging.page, pageSize: paging.pageSize, totalPages: Math.ceil(total / paging.pageSize), truncated: false };
  }

  function dashboard() {
    TSAuth.authorize('DASHBOARD', 'read');
    var now = new Date().getTime();
    var cases = TSData.list('Casos', {}).rows;
    var followUps = TSData.list('Seguimientos', {}).rows;
    var commitments = TSData.list('Compromisos', {}).rows;
    var news = TSData.list('Novedades', {}).rows;
    var tours = TSData.list('Recorridos', {}).rows;
    function status(value) { return TSUtils.normalizeKey(value); }
    return {
      casesOpen: cases.filter(function (row) { return ['CERRADO', 'INACTIVO'].indexOf(status(row.EstadoCaso)) === -1; }).length,
      casesClosed: cases.filter(function (row) { return status(row.EstadoCaso) === 'CERRADO'; }).length,
      casesPending: cases.filter(function (row) { return ['BORRADOR', 'PENDIENTE', 'REGISTRADO'].indexOf(status(row.EstadoCaso)) !== -1; }).length,
      upcomingFollowUps: followUps.filter(function (row) { var date = dateValue(row.FechaProximaAccion); return date !== null && date >= now && status(row.Estado) !== 'CERRADO'; }).length,
      overdueCommitments: commitments.filter(function (row) { var date = dateValue(row.FechaLimite); return date !== null && date < now && ['CUMPLIDO', 'CERRADO', 'CANCELADO'].indexOf(status(row.Estado)) === -1; }).length,
      pendingNews: news.filter(function (row) { return ['CERRADO', 'RESUELTO'].indexOf(status(row.Estado)) === -1; }).length,
      toursCompleted: tours.length,
      generatedAt: new Date()
    };
  }

  return Object.freeze({ search: search, dashboard: dashboard, searchFields: SEARCH_FIELDS });
})();
