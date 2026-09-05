var TSExport = (function () {
  var OMIT = { _rowNumber: true, DriveFileId: true, Url: true, ArchivoFuente: true, HojaFuente: true, RegistroFuente: true, UsuarioImportacion: true, MotivoEliminacion: true };

  function tabular(result) {
    var headers = ['Tabla'];
    var headerSet = { Tabla: true };
    result.items.forEach(function (item) {
      Object.keys(item.record || {}).forEach(function (field) {
        if (!OMIT[field] && !headerSet[field]) { headerSet[field] = true; headers.push(field); }
      });
    });
    var rows = result.items.map(function (item) {
      return headers.map(function (field) { return field === 'Tabla' ? item.table : (item.record[field] === undefined ? '' : item.record[field]); });
    });
    return { headers: headers, rows: rows };
  }

  function csv(data) {
    return [data.headers].concat(data.rows).map(function (row) { return row.map(TSUtils.csvEscape).join(','); }).join('\r\n');
  }

  function exportResults(payload, correlationId) {
    payload = payload || {};
    var user = TSAuth.authorize('REPORTES', 'export');
    var result = TSSearch.search(payload.filters || payload, { exportMode: true });
    var data = tabular(result);
    var stamp = Utilities.formatDate(new Date(), TSConfig.get().timeZone, 'yyyyMMdd_HHmmss');
    var format = TSUtils.normalizeKey(payload.format || 'CSV');
    if (format === 'CSV') {
      var content = '\uFEFF' + csv(data);
      TSAudit.access('DOWNLOAD_FILE', 'REPORTES', 'EXPORT-' + stamp, user.email, 'Exportacion CSV de ' + result.items.length + ' filas', correlationId);
      return { format: 'CSV', fileName: 'trabajo_social_' + stamp + '.csv', mimeType: 'text/csv;charset=utf-8', content: content, rowCount: result.items.length, truncated: result.truncated };
    }
    TSErrors.assert(format === 'GOOGLE_SHEETS' || format === 'SHEET', 'INVALID_EXPORT_FORMAT', 'Formato de exportacion no valido.', null, 422);
    var book = SpreadsheetApp.create('Export Trabajo Social ' + stamp);
    var sheet = book.getSheets()[0];
    sheet.setName('Resultados');
    if (data.headers.length) {
      sheet.getRange(1, 1, 1, data.headers.length).setValues([data.headers]);
      if (data.rows.length) sheet.getRange(2, 1, data.rows.length, data.headers.length).setValues(data.rows.map(function (row) { return row.map(TSUtils.stringifyCell); }));
      sheet.setFrozenRows(1);
      sheet.getRange(1, 1, 1, data.headers.length).setFontWeight('bold').setBackground('#E8F0FE');
      sheet.autoResizeColumns(1, Math.min(data.headers.length, 30));
    }
    var file = DriveApp.getFileById(book.getId());
    var exportFolderIterator = TSDrive.rootFolder().getFoldersByName('Exportaciones');
    var exportFolder = exportFolderIterator.hasNext() ? exportFolderIterator.next() : TSDrive.rootFolder().createFolder('Exportaciones');
    file.moveTo(exportFolder);
    if (TSConfig.get().shareExportsWithRequester) {
      try { file.addViewer(user.email); } catch (ignore) {}
    }
    TSAudit.access('DOWNLOAD_FILE', 'REPORTES', book.getId(), user.email, 'Exportacion Google Sheets de ' + result.items.length + ' filas', correlationId);
    return { format: 'GOOGLE_SHEETS', fileName: file.getName(), url: book.getUrl(), rowCount: result.items.length, truncated: result.truncated };
  }

  return Object.freeze({ exportResults: exportResults });
})();
