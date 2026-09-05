var TSImport = (function () {
  function allowedTables() { return TSConfig.processTables.concat(['DetalleCasosSensibles']); }
  var MINIMUM_HEADERS = {
    Personas: ['Nombre'], Atenciones: ['Fecha', 'Responsable', 'Motivo'],
    Casos: ['FechaApertura', 'Responsable', 'EstadoCaso'],
    DetalleCasosSensibles: ['IdCaso'], Novedades: ['Fecha', 'Responsable', 'Descripcion', 'Estado'],
    Recorridos: ['Fecha', 'Responsable', 'Objetivo'], HallazgosRecorrido: ['IdRecorrido', 'Descripcion'],
    Seguimientos: ['IdCaso', 'Fecha', 'Responsable', 'Descripcion'],
    Derivaciones: ['IdCaso', 'Fecha', 'AreaDestino', 'Motivo'],
    Compromisos: ['IdCaso', 'Responsable', 'Descripcion', 'Estado'],
    Cierres: ['IdCaso', 'FechaCierreCaso', 'Responsable', 'MotivoCierre']
  };

  function source(payload) {
    payload = payload || {};
    if (payload.spreadsheetId) {
      var sourceFile;
      try { sourceFile = DriveApp.getFileById(String(payload.spreadsheetId)); }
      catch (driveError) { throw new TSAppError('IMPORT_SOURCE_UNAVAILABLE', 'No fue posible acceder al archivo de origen.', null, 404); }
      var stagingId = PropertiesService.getScriptProperties().getProperty(TSConfig.properties.importFolderId) || '';
      if (!stagingId) {
        var stagingIterator = TSDrive.rootFolder().getFoldersByName('Importaciones');
        if (stagingIterator.hasNext()) stagingId = stagingIterator.next().getId();
      }
      TSErrors.assert(stagingId, 'IMPORT_STAGING_NOT_CONFIGURED', 'La carpeta segura de importaciones no esta configurada. Ejecute setupApplication().', null, 503);
      var approvedParent = false;
      var parents = sourceFile.getParents();
      while (parents.hasNext()) { if (parents.next().getId() === stagingId) { approvedParent = true; break; } }
      TSErrors.assert(approvedParent, 'IMPORT_SOURCE_OUTSIDE_STAGING', 'El archivo debe estar dentro de la carpeta segura TrabajoSocial/Importaciones.', null, 403);
      TSErrors.assert(sourceFile.getMimeType() === MimeType.GOOGLE_SHEETS, 'IMPORT_SOURCE_TYPE', 'El archivo de origen debe ser una hoja de calculo de Google.', null, 422);
      var book;
      try { book = SpreadsheetApp.openById(String(payload.spreadsheetId)); }
      catch (error) { throw new TSAppError('IMPORT_SOURCE_UNAVAILABLE', 'No fue posible abrir la hoja de origen.', null, 404); }
      var sheet = payload.sheetName ? book.getSheetByName(String(payload.sheetName)) : book.getSheets()[0];
      TSErrors.assert(sheet, 'IMPORT_SHEET_NOT_FOUND', 'La hoja de origen no existe.', null, 404);
      var lastRow = sheet.getLastRow();
      var lastColumn = sheet.getLastColumn();
      TSErrors.assert(lastRow >= 1 && lastColumn >= 1, 'IMPORT_EMPTY', 'La hoja de origen esta vacia.', null, 422);
      var headers = sheet.getRange(1, 1, 1, lastColumn).getDisplayValues()[0].map(function (header) { return TSUtils.cleanText(header, 200); });
      var rows = lastRow > 1 ? sheet.getRange(2, 1, lastRow - 1, lastColumn).getValues() : [];
      var fileName = '';
      try { fileName = sourceFile.getName(); } catch (ignore) { fileName = book.getName(); }
      return { headers: headers, rows: rows, fileName: TSUtils.cleanText(payload.origin ? payload.origin + ' | ' + fileName : fileName, 500), sheetName: sheet.getName(), spreadsheetId: book.getId() };
    }
    TSErrors.assert(Array.isArray(payload.headers) && Array.isArray(payload.rows), 'IMPORT_SOURCE_REQUIRED', 'Indique una hoja de origen o datos tabulares.', null, 422);
    var directName = TSUtils.cleanText(payload.fileName || 'Carga directa', 350);
    return { headers: payload.headers.map(function (header) { return TSUtils.cleanText(header, 200); }), rows: payload.rows, fileName: TSUtils.cleanText(payload.origin ? payload.origin + ' | ' + directName : directName, 500), sheetName: TSUtils.cleanText(payload.sheetName || 'Datos', 200), spreadsheetId: '' };
  }

  function rowObject(headers, row) {
    if (!Array.isArray(row) && row && typeof row === 'object') return row;
    var object = {};
    headers.forEach(function (header, index) { object[header] = row[index]; });
    return object;
  }

  function validate(payload) {
    payload = payload || {};
    var requested = payload.table || payload.targetTable || payload.entity;
    var table = TSUtils.normalizeKey(requested) === 'DETALLE_CASOS_SENSIBLES' ? 'DetalleCasosSensibles' : TSProcesses.resolveTable(requested);
    TSErrors.assert(allowedTables().indexOf(table) !== -1, 'IMPORT_TABLE_NOT_ALLOWED', 'La tabla indicada no admite importacion.', null, 422);
    var user = TSAuth.authorize('IMPORTACION', 'create');
    TSAuth.authorize(TSConfig.tableModules[table], 'create', { user: user, sensitive: table === 'DetalleCasosSensibles' });
    var data = source(payload);
    TSErrors.assert(data.rows.length <= TSConfig.get().maxImportRows, 'IMPORT_TOO_LARGE', 'La importacion excede el maximo de filas permitido por ejecucion.', { maxRows: TSConfig.get().maxImportRows }, 422);
    var schema = TSConfig.schema(table);
    var unknown = data.headers.filter(function (header) { return schema.indexOf(header) === -1; });
    var missingHeaders = (MINIMUM_HEADERS[table] || []).filter(function (header) { return data.headers.indexOf(header) === -1; });
    var errors = [];
    if (unknown.length) errors.push({ row: 1, code: 'UNKNOWN_HEADERS', message: 'Existen columnas no reconocidas.', fields: unknown });
    if (missingHeaders.length) errors.push({ row: 1, code: 'MISSING_HEADERS', message: 'Faltan columnas obligatorias.', fields: missingHeaders });
    var idField = TSConfig.idFields[table];
    var existingIds = {};
    var existingSources = {};
    TSData.all(table, { cache: false }).forEach(function (record) {
      existingIds[String(record[idField])] = true;
      if (!TSUtils.isBlank(record.ArchivoFuente) && !TSUtils.isBlank(record.RegistroFuente)) existingSources[String(record.ArchivoFuente) + '|' + String(record.HojaFuente) + '|' + String(record.RegistroFuente)] = true;
    });
    var batchIds = {};
    var caseCodes = {};
    if (table === 'Casos') TSData.all('Casos', { cache: false }).forEach(function (record) { if (record.CodigoCaso) caseCodes[String(record.CodigoCaso).toUpperCase()] = true; });
    var prepared = [];
    data.rows.forEach(function (raw, index) {
      var sourceRow = index + 2;
      var object = rowObject(data.headers, raw);
      var blank = data.headers.every(function (header) { return TSUtils.isBlank(object[header]); });
      if (blank) return;
      var clean;
      try {
        clean = TSValidation.record(table, object, false);
        (MINIMUM_HEADERS[table] || []).forEach(function (field) {
          if (TSUtils.isBlank(clean[field])) throw new TSAppError('REQUIRED_FIELD', 'Campo obligatorio vacio: ' + field, { field: field }, 422);
        });
        TSProcesses.coerceDates(clean);
        TSValidation.businessRules(table, clean);
        var suppliedId = clean[idField];
        if (TSUtils.isBlank(suppliedId)) clean[idField] = TSUtils.uuid(idField.replace(/^Id/, '').substring(0, 8));
        var idKey = String(clean[idField]);
        if (existingIds[idKey] || batchIds[idKey]) throw new TSAppError('DUPLICATE_ID', 'Identificador duplicado: ' + idKey, { field: idField }, 409);
        batchIds[idKey] = true;
        var sourceKey = data.fileName + '|' + data.sheetName + '|' + sourceRow;
        if (existingSources[sourceKey]) throw new TSAppError('SOURCE_ROW_ALREADY_IMPORTED', 'La fila de origen ya fue importada anteriormente.', { sourceRow: sourceRow }, 409);
        existingSources[sourceKey] = true;
        if (table === 'Casos') {
          clean.CodigoCaso = clean.CodigoCaso || ('CAS-' + Utilities.formatDate(new Date(), TSConfig.get().timeZone, 'yyyy') + '-' + Utilities.getUuid().replace(/-/g, '').substring(0, 10).toUpperCase());
          var code = String(clean.CodigoCaso).toUpperCase();
          if (caseCodes[code]) throw new TSAppError('DUPLICATE_CASE_CODE', 'Codigo de caso duplicado: ' + clean.CodigoCaso, { field: 'CodigoCaso' }, 409);
          caseCodes[code] = true;
          if (TSAuth.isSensitiveCase(clean)) TSAuth.authorize('CASOS', 'create', { user: user, sensitive: true });
        }
        TSProcesses.enforceReferences(table, clean);
        if (table === 'DetalleCasosSensibles') {
          var parentCase = TSData.findById('Casos', clean.IdCaso, false);
          TSErrors.assert(parentCase && TSAuth.isSensitiveCase(parentCase), 'SENSITIVITY_LEVEL_REQUIRED', 'El caso relacionado no esta configurado como sensible.', { caseId: clean.IdCaso }, 422);
        }
        clean.ArchivoFuente = data.fileName;
        clean.HojaFuente = data.sheetName;
        clean.RegistroFuente = sourceRow;
        clean.FechaImportacion = TSUtils.now();
        clean.UsuarioImportacion = user.email;
        prepared.push(clean);
      } catch (error) {
        errors.push({ row: sourceRow, code: error.code || 'ROW_ERROR', message: error instanceof TSAppError ? error.message : 'Fila invalida.', details: error.details || null });
      }
    });
    if (!prepared.length && !errors.length) errors.push({ row: 0, code: 'NO_DATA', message: 'No existen filas con datos para importar.' });
    return {
      valid: errors.length === 0, table: table, source: { fileName: data.fileName, sheetName: data.sheetName, spreadsheetId: data.spreadsheetId },
      totalRows: data.rows.length, validRows: prepared.length, errorCount: errors.length,
      errors: errors.slice(0, 200), errorsTruncated: errors.length > 200,
      preview: prepared.slice(0, 10), _prepared: prepared
    };
  }

  function execute(payload, correlationId) {
    var validation = validate(payload);
    TSErrors.assert(validation.valid, 'IMPORT_VALIDATION_FAILED', 'La importacion contiene errores. No se guardo ninguna fila.', { errors: validation.errors, errorsTruncated: validation.errorsTruncated }, 422);
    var user = TSAuth.current();
    return TSUtils.withScriptLock(function () {
      var job = TSData.insertUnsafe('Importaciones', {
        TablaDestino: validation.table, ArchivoFuente: validation.source.fileName,
        HojaFuente: validation.source.sheetName, TotalFilas: validation.validRows,
        FilasImportadas: 0, FilasError: 0, Estado: 'PROCESANDO', Errores: '',
        FechaInicio: TSUtils.now(), UsuarioImportacion: user.email
      }, user.email);
      try {
        var concurrentSources = {};
        TSData.all(validation.table, { cache: false }).forEach(function (row) {
          if (!TSUtils.isBlank(row.ArchivoFuente) && !TSUtils.isBlank(row.RegistroFuente)) concurrentSources[String(row.ArchivoFuente) + '|' + String(row.HojaFuente) + '|' + String(row.RegistroFuente)] = true;
        });
        validation._prepared.forEach(function (row) {
          var sourceKey = String(row.ArchivoFuente) + '|' + String(row.HojaFuente) + '|' + String(row.RegistroFuente);
          TSErrors.assert(!concurrentSources[sourceKey], 'SOURCE_ROW_ALREADY_IMPORTED', 'La fuente fue importada por otra operacion concurrente.', { sourceRow: row.RegistroFuente }, 409);
          concurrentSources[sourceKey] = true;
        });
        if (validation.table === 'Casos') {
          var concurrentCodes = {};
          TSData.all('Casos', { cache: false }).forEach(function (row) { if (row.CodigoCaso) concurrentCodes[String(row.CodigoCaso).toUpperCase()] = true; });
          validation._prepared.forEach(function (row) {
            var code = String(row.CodigoCaso || '').toUpperCase();
            TSErrors.assert(code && !concurrentCodes[code], 'DUPLICATE_CASE_CODE', 'El codigo de caso ya existe.', { code: row.CodigoCaso }, 409);
            concurrentCodes[code] = true;
          });
        }
        var saved = TSData.insertManyUnsafe(validation.table, validation._prepared, user.email);
        var completed = TSData.updateUnsafe('Importaciones', job.IdImportacion, { FilasImportadas: saved.length, FilasError: 0, Estado: 'COMPLETADA', FechaFin: TSUtils.now() }, user.email).after;
        TSAudit.batchActionUnsafe('IMPORT', validation.table, saved, user.email, 'Importacion ' + job.IdImportacion, correlationId);
        return { importId: job.IdImportacion, status: completed.Estado, importedRows: saved.length, table: validation.table };
      } catch (error) {
        try { TSData.updateUnsafe('Importaciones', job.IdImportacion, { FilasError: validation.validRows, Estado: 'ERROR', Errores: TSUtils.cleanText(error.message, 45000), FechaFin: TSUtils.now() }, user.email); } catch (ignore) {}
        throw error;
      }
    });
  }

  function status(payload) {
    var user = TSAuth.authorize('IMPORTACION', 'read');
    payload = payload || {};
    if (payload.importId || payload.id) {
      var job = TSData.findById('Importaciones', payload.importId || payload.id, false);
      TSErrors.assert(job, 'IMPORT_NOT_FOUND', 'Importacion no encontrada.', null, 404);
      var canAdmin = TSAuth.can(user, 'ADMINISTRACION', 'read');
      TSErrors.assert(canAdmin || TSUtils.normalizeEmail(job.UsuarioImportacion) === user.email, 'FORBIDDEN', 'No puede consultar esta importacion.', null, 403);
      return job;
    }
    return TSData.list('Importaciones', {
      predicate: function (row) { return TSAuth.can(user, 'ADMINISTRACION', 'read') || TSUtils.normalizeEmail(row.UsuarioImportacion) === user.email; },
      sortBy: 'FechaInicio', sortDirection: 'desc', limit: 50
    });
  }

  return Object.freeze({ validate: validate, execute: execute, status: status });
})();
