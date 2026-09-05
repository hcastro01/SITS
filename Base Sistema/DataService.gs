/** Persistencia generica sobre hojas normalizadas. */
var TSData = (function () {
  function spreadsheet() {
    var id = TSConfig.get().spreadsheetId;
    TSErrors.assert(id, 'NOT_CONFIGURED', 'La aplicacion no esta configurada. Ejecute setupApplication().', null, 503);
    try { return SpreadsheetApp.openById(id); }
    catch (error) { throw new TSAppError('SPREADSHEET_UNAVAILABLE', 'No fue posible acceder a la base de datos configurada.', null, 503); }
  }

  function sheet(table) {
    TSValidation.table(table);
    var value = spreadsheet().getSheetByName(table);
    TSErrors.assert(value, 'TABLE_NOT_FOUND', 'La tabla ' + table + ' no existe. Ejecute setupApplication().', { table: table }, 503);
    verifyHeaders(value, table);
    return value;
  }

  function verifyHeaders(target, table) {
    var expected = TSConfig.schema(table);
    if (target.getLastColumn() < expected.length) throw new TSAppError('SCHEMA_MISMATCH', 'La estructura de ' + table + ' esta incompleta.', null, 500);
    var actual = target.getRange(1, 1, 1, expected.length).getDisplayValues()[0];
    for (var i = 0; i < expected.length; i++) {
      if (actual[i] !== expected[i]) throw new TSAppError('SCHEMA_MISMATCH', 'La estructura de ' + table + ' no coincide con la version esperada.', { column: i + 1, expected: expected[i], actual: actual[i] }, 500);
    }
  }

  function versionKey(table) { return 'TS_TABLE_VERSION_' + table; }

  function tableVersion(table) {
    return PropertiesService.getScriptProperties().getProperty(versionKey(table)) || '0';
  }

  function invalidate(table) {
    var props = PropertiesService.getScriptProperties();
    var next = String((parseInt(props.getProperty(versionKey(table)), 10) || 0) + 1);
    props.setProperty(versionKey(table), next);
  }

  function rowObject(headers, values, rowNumber) {
    var object = { _rowNumber: rowNumber };
    for (var i = 0; i < headers.length; i++) object[headers[i]] = values[i];
    return object;
  }

  function all(table, options) {
    options = options || {};
    TSValidation.table(table);
    var cacheKey = 'rows:' + table + ':' + tableVersion(table);
    var cached;
    if (options.cache !== false) {
      try { cached = CacheService.getScriptCache().get(cacheKey); } catch (ignore) {}
      if (cached) return JSON.parse(cached);
    }
    var target = sheet(table);
    var headers = TSConfig.schema(table);
    var lastRow = target.getLastRow();
    if (lastRow < 2) return [];
    var values = target.getRange(2, 1, lastRow - 1, headers.length).getValues();
    var rows = values.map(function (row, index) { return rowObject(headers, row, index + 2); });
    if (options.cache !== false) {
      try { CacheService.getScriptCache().put(cacheKey, JSON.stringify(TSUtils.toSerializable(rows)), TSConfig.get().cacheSeconds); } catch (ignore2) {}
    }
    return rows;
  }

  function isVisible(row, includeDeleted) {
    if (includeDeleted) return true;
    if (Object.prototype.hasOwnProperty.call(row, 'Eliminado') && TSUtils.toBoolean(row.Eliminado)) return false;
    if (Object.prototype.hasOwnProperty.call(row, 'Activo') && row.Activo !== '' && !TSUtils.toBoolean(row.Activo)) return false;
    return true;
  }

  function list(table, options) {
    options = options || {};
    var rows = all(table, options).filter(function (row) { return isVisible(row, Boolean(options.includeDeleted)); });
    if (options.filters) {
      Object.keys(options.filters).forEach(function (field) {
        var expected = options.filters[field];
        if (expected === null || expected === undefined || expected === '') return;
        rows = rows.filter(function (row) {
          if (Array.isArray(expected)) return expected.map(String).indexOf(String(row[field])) !== -1;
          return String(row[field]).toLowerCase() === String(expected).toLowerCase();
        });
      });
    }
    if (typeof options.predicate === 'function') rows = rows.filter(options.predicate);
    if (options.sortBy) {
      var direction = String(options.sortDirection || 'asc').toLowerCase() === 'desc' ? -1 : 1;
      var sortField = options.sortBy;
      rows.sort(function (a, b) {
        var av = a[sortField] instanceof Date ? a[sortField].getTime() : String(a[sortField] || '').toLowerCase();
        var bv = b[sortField] instanceof Date ? b[sortField].getTime() : String(b[sortField] || '').toLowerCase();
        return av < bv ? -direction : av > bv ? direction : 0;
      });
    }
    var total = rows.length;
    var offset = Math.max(0, parseInt(options.offset, 10) || 0);
    var limit = options.limit === undefined ? total : Math.max(0, parseInt(options.limit, 10) || 0);
    if (options.limit !== undefined) rows = rows.slice(offset, offset + limit);
    return { rows: rows, total: total, offset: offset, limit: limit };
  }

  function findById(table, id, includeDeleted) {
    var idField = TSConfig.idFields[table];
    TSErrors.assert(idField, 'INVALID_TABLE', 'La entidad no tiene identificador.', null, 400);
    if (TSUtils.isBlank(id)) return null;
    var target = sheet(table);
    var headers = TSConfig.schema(table);
    var idColumn = headers.indexOf(idField) + 1;
    var lastRow = target.getLastRow();
    if (lastRow < 2) return null;
    var ids = target.getRange(2, idColumn, lastRow - 1, 1).getDisplayValues();
    var wanted = String(id);
    for (var i = 0; i < ids.length; i++) {
      if (String(ids[i][0]) === wanted) {
        var row = rowObject(headers, target.getRange(i + 2, 1, 1, headers.length).getValues()[0], i + 2);
        return isVisible(row, Boolean(includeDeleted)) ? row : null;
      }
    }
    return null;
  }

  function prepare(table, input, userEmail, existing) {
    var headers = TSConfig.schema(table);
    var idField = TSConfig.idFields[table];
    var now = TSUtils.now();
    var record = TSUtils.pick(input || {}, headers);
    if (!existing) {
      if (TSUtils.isBlank(record[idField])) record[idField] = TSUtils.uuid(idField.replace(/^Id/, '').substring(0, 8));
      if (headers.indexOf('Activo') !== -1 && TSUtils.isBlank(record.Activo)) record.Activo = true;
      if (headers.indexOf('Eliminado') !== -1 && TSUtils.isBlank(record.Eliminado)) record.Eliminado = false;
      if (headers.indexOf('FechaCreacion') !== -1 && TSUtils.isBlank(record.FechaCreacion)) record.FechaCreacion = now;
      if (headers.indexOf('CreadoPor') !== -1 && TSUtils.isBlank(record.CreadoPor)) record.CreadoPor = userEmail || '';
      if (headers.indexOf('Version') !== -1) record.Version = 1;
    } else {
      if (headers.indexOf('FechaActualizacion') !== -1) record.FechaActualizacion = now;
      if (headers.indexOf('ActualizadoPor') !== -1) record.ActualizadoPor = userEmail || '';
      if (headers.indexOf('Version') !== -1) record.Version = (parseInt(existing.Version, 10) || 0) + 1;
    }
    return record;
  }

  function valuesFor(headers, record, existing) {
    return headers.map(function (header) {
      var value = Object.prototype.hasOwnProperty.call(record, header) ? record[header] : (existing ? existing[header] : '');
      return TSUtils.stringifyCell(value);
    });
  }

  function ensureWriteCapacity(target, additionalRows, requiredColumns) {
    additionalRows = Math.max(0, Number(additionalRows) || 0);
    requiredColumns = Math.max(1, Number(requiredColumns) || 1);
    var requiredRows = target.getLastRow() + additionalRows;
    if (target.getMaxRows() < requiredRows) {
      target.insertRowsAfter(target.getMaxRows(), requiredRows - target.getMaxRows());
    }
    if (target.getMaxColumns() < requiredColumns) {
      target.insertColumnsAfter(target.getMaxColumns(), requiredColumns - target.getMaxColumns());
    }
  }

  function insertUnsafe(table, input, userEmail) {
    var target = sheet(table);
    var idField = TSConfig.idFields[table];
    var record = prepare(table, input, userEmail, null);
    TSErrors.assert(!findById(table, record[idField], true), 'DUPLICATE_ID', 'Ya existe un registro con el mismo identificador.', { id: record[idField] }, 409);
    var headers = TSConfig.schema(table);
    ensureWriteCapacity(target, 1, headers.length);
    target.getRange(target.getLastRow() + 1, 1, 1, headers.length).setValues([valuesFor(headers, record)]);
    invalidate(table);
    return findById(table, record[idField], true);
  }

  function insert(table, input, userEmail) {
    return TSUtils.withScriptLock(function () { return insertUnsafe(table, input, userEmail); });
  }

  function insertManyUnsafe(table, inputs, userEmail) {
    if (!inputs || !inputs.length) return [];
    var target = sheet(table);
    var headers = TSConfig.schema(table);
    var idField = TSConfig.idFields[table];
    var seen = {};
    all(table, { cache: false }).forEach(function (row) { seen[String(row[idField])] = true; });
    var prepared = inputs.map(function (input) {
      var record = prepare(table, input, userEmail, null);
      var key = String(record[idField]);
      TSErrors.assert(!seen[key], 'DUPLICATE_ID', 'Se detecto un identificador duplicado.', { id: key }, 409);
      seen[key] = true;
      return record;
    });
    ensureWriteCapacity(target, prepared.length, headers.length);
    target.getRange(target.getLastRow() + 1, 1, prepared.length, headers.length).setValues(prepared.map(function (record) { return valuesFor(headers, record); }));
    invalidate(table);
    return prepared;
  }

  function insertMany(table, inputs, userEmail) {
    return TSUtils.withScriptLock(function () { return insertManyUnsafe(table, inputs, userEmail); });
  }

  function updateUnsafe(table, id, patch, userEmail, expectedVersion) {
    var existing = findById(table, id, true);
    TSErrors.assert(existing, 'NOT_FOUND', 'Registro no encontrado.', { table: table, id: id }, 404);
    if (expectedVersion !== undefined && expectedVersion !== null && Number(expectedVersion) !== Number(existing.Version)) {
      throw new TSAppError('VERSION_CONFLICT', 'El registro fue modificado por otro usuario. Recargue la informacion.', { currentVersion: existing.Version }, 409);
    }
    var idField = TSConfig.idFields[table];
    var safePatch = TSUtils.pick(patch || {}, TSConfig.schema(table));
    delete safePatch[idField];
    var prepared = prepare(table, safePatch, userEmail, existing);
    var merged = {};
    TSConfig.schema(table).forEach(function (key) { merged[key] = Object.prototype.hasOwnProperty.call(prepared, key) ? prepared[key] : existing[key]; });
    sheet(table).getRange(existing._rowNumber, 1, 1, TSConfig.schema(table).length).setValues([valuesFor(TSConfig.schema(table), merged)]);
    invalidate(table);
    return { before: existing, after: findById(table, id, true) };
  }

  function update(table, id, patch, userEmail, expectedVersion) {
    return TSUtils.withScriptLock(function () { return updateUnsafe(table, id, patch, userEmail, expectedVersion); });
  }

  function upsertUnsafe(table, keyField, keyValue, values, userEmail) {
    var found = list(table, { includeDeleted: true, cache: false, predicate: function (row) { return String(row[keyField]) === String(keyValue); }, limit: 1 }).rows[0];
    if (found) return updateUnsafe(table, found[TSConfig.idFields[table]], values, userEmail).after;
    values[keyField] = keyValue;
    return insertUnsafe(table, values, userEmail);
  }

  function softDeleteUnsafe(table, id, userEmail, reason) {
    TSErrors.assert(TSConfig.schema(table).indexOf('Eliminado') !== -1, 'DELETE_NOT_SUPPORTED', 'La entidad no admite eliminacion logica.', null, 400);
    TSErrors.assert(!TSUtils.isBlank(reason), 'DELETE_REASON_REQUIRED', 'Debe indicar el motivo de eliminacion.', null, 422);
    return updateUnsafe(table, id, { Activo: false, Eliminado: true, FechaEliminacion: TSUtils.now(), UsuarioEliminacion: userEmail, MotivoEliminacion: TSUtils.cleanText(reason, 1000) }, userEmail);
  }

  function restoreUnsafe(table, id, userEmail) {
    return updateUnsafe(table, id, { Activo: true, Eliminado: false, FechaEliminacion: '', UsuarioEliminacion: '', MotivoEliminacion: '' }, userEmail);
  }

  function hardDeleteUnsafe(table, id) {
    var existing = findById(table, id, true);
    TSErrors.assert(existing, 'NOT_FOUND', 'Registro no encontrado.', null, 404);
    sheet(table).deleteRow(existing._rowNumber);
    invalidate(table);
    return existing;
  }

  return Object.freeze({
    spreadsheet: spreadsheet, sheet: sheet, verifyHeaders: verifyHeaders, all: all, list: list,
    findById: findById, insert: insert, insertUnsafe: insertUnsafe, insertMany: insertMany,
    insertManyUnsafe: insertManyUnsafe, update: update, updateUnsafe: updateUnsafe,
    upsertUnsafe: upsertUnsafe, softDeleteUnsafe: softDeleteUnsafe,
    restoreUnsafe: restoreUnsafe, hardDeleteUnsafe: hardDeleteUnsafe, invalidate: invalidate,
    isVisible: isVisible
  });
})();
