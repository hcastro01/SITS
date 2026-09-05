var TSDrive = (function () {
  function rootFolder() {
    var id = TSConfig.get().rootFolderId;
    TSErrors.assert(id, 'DRIVE_NOT_CONFIGURED', 'La carpeta documental no esta configurada. Ejecute setupApplication().', null, 503);
    try { return DriveApp.getFolderById(id); }
    catch (error) { throw new TSAppError('DRIVE_UNAVAILABLE', 'No fue posible acceder a la carpeta documental.', null, 503); }
  }

  function child(parent, name) {
    var iterator = parent.getFoldersByName(name);
    return iterator.hasNext() ? iterator.next() : parent.createFolder(name);
  }

  function folderFor(table, recordId) {
    var entity = child(rootFolder(), TSUtils.safeFileName(table));
    var record = child(entity, TSUtils.safeFileName(recordId));
    return child(record, 'Documentos');
  }

  function tableFromType(type) {
    var normalized = TSUtils.normalizeKey(type);
    var aliases = {
      CASO: 'Casos', CASOS: 'Casos', ATENCION: 'Atenciones', ATENCIONES: 'Atenciones',
      NOVEDAD: 'Novedades', NOVEDADES: 'Novedades', RECORRIDO: 'Recorridos', RECORRIDOS: 'Recorridos',
      HALLAZGO: 'HallazgosRecorrido', HALLAZGOS_RECORRIDO: 'HallazgosRecorrido',
      SEGUIMIENTO: 'Seguimientos', SEGUIMIENTOS: 'Seguimientos', DERIVACION: 'Derivaciones',
      DERIVACIONES: 'Derivaciones', COMPROMISO: 'Compromisos', COMPROMISOS: 'Compromisos',
      CIERRE: 'Cierres', CIERRES: 'Cierres', PERSONA: 'Personas', PERSONAS: 'Personas',
      RESPUESTA_FORMULARIO: 'RespuestasFormulario'
    };
    var table = aliases[normalized] || type;
    TSValidation.table(table);
    return table;
  }

  function ensureRecordAccess(table, recordId, action) {
    var module = TSConfig.tableModules[table];
    var record;
    if (table === 'RespuestasFormulario') {
      record = TSData.list(table, { filters: { IdRespuesta: recordId }, limit: 1 }).rows[0];
    } else {
      record = TSData.findById(table, recordId, false);
    }
    TSErrors.assert(record, 'NOT_FOUND', 'El registro asociado no existe.', null, 404);
    var sensitive = TSAuth.isSensitiveRecord(table, record);
    var user = TSAuth.authorize(module, action, { sensitive: sensitive });
    if (sensitive && table !== 'Casos') TSAuth.authorize('CASOS', 'read', { user: user, sensitive: true });
    return { user: user, record: record, sensitive: sensitive };
  }

  function signatureMatches(extension, bytes) {
    function starts(sequence) {
      if (bytes.length < sequence.length) return false;
      for (var i = 0; i < sequence.length; i++) if ((bytes[i] & 255) !== sequence[i]) return false;
      return true;
    }
    if (extension === 'jpg' || extension === 'jpeg') return starts([0xFF, 0xD8, 0xFF]);
    if (extension === 'png') return starts([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]);
    if (extension === 'pdf') return starts([0x25, 0x50, 0x44, 0x46, 0x2D]);
    if (extension === 'doc' || extension === 'xls') return starts([0xD0, 0xCF, 0x11, 0xE0, 0xA1, 0xB1, 0x1A, 0xE1]);
    if (extension === 'docx' || extension === 'xlsx') return starts([0x50, 0x4B, 0x03, 0x04]) || starts([0x50, 0x4B, 0x05, 0x06]);
    return false;
  }

  function decodeValidated(file) {
    var validated = TSValidation.file(file);
    var bytes;
    try { bytes = Utilities.base64Decode(validated.base64); }
    catch (error) { throw new TSAppError('INVALID_BASE64', 'El contenido del archivo no es valido.', null, 422); }
    TSErrors.assert(bytes.length <= TSConfig.get().maxFileBytes, 'FILE_TOO_LARGE', 'El archivo supera el tamano permitido.', { maxBytes: TSConfig.get().maxFileBytes }, 422);
    TSErrors.assert(signatureMatches(validated.extension, bytes), 'FILE_SIGNATURE_MISMATCH', 'El contenido del archivo no coincide con su extension.', { extension: validated.extension }, 422);
    validated.bytes = bytes;
    validated.actualBytes = bytes.length;
    return validated;
  }

  function upload(payload, correlationId) {
    payload = payload || {};
    TSValidation.required(payload, ['recordType', 'recordId', 'files']);
    TSErrors.assert(Array.isArray(payload.files) && payload.files.length > 0, 'FILES_REQUIRED', 'Seleccione al menos un archivo.', null, 422);
    var table = tableFromType(payload.recordType);
    var access = ensureRecordAccess(table, payload.recordId, 'edit');
    var validated = payload.files.map(decodeValidated);
    validated.forEach(function (item) {
      if (!item.category || item.sensitivity) return;
      var question = TSData.findById('Preguntas', item.category, false);
      if (question && !TSUtils.isBlank(question.Sensibilidad)) item.sensitivity = 'SENSIBLE';
    });
    var declaredSensitive = access.sensitive || validated.some(function (item) { return !TSUtils.isBlank(item.sensitivity); });
    TSAuth.authorize('DOCUMENTOS', 'create', { user: access.user, sensitive: declaredSensitive });
    var config = TSConfig.get();
    TSErrors.assert(validated.length <= config.maxFilesPerRecord, 'TOO_MANY_FILES', 'Se excedio la cantidad maxima de archivos por registro.', { max: config.maxFilesPerRecord }, 422);

    return TSUtils.withScriptLock(function () {
      var existing = TSData.list('Documentos', { filters: { TipoRegistro: table, IdRegistro: payload.recordId }, cache: false }).total;
      TSErrors.assert(existing + validated.length <= config.maxFilesPerRecord, 'TOO_MANY_FILES', 'Se excedio la cantidad maxima de archivos por registro.', { max: config.maxFilesPerRecord }, 422);
      var folder = folderFor(table, payload.recordId);
      var createdFiles = [];
      try {
        var rows = validated.map(function (item) {
          var blob = Utilities.newBlob(item.bytes, item.mimeType, item.name);
          var file = folder.createFile(blob);
          createdFiles.push(file);
          return {
            IdArchivo: TSUtils.uuid('DOC'), IdRegistro: payload.recordId, TipoRegistro: table,
            NombreArchivo: item.name, MimeType: item.mimeType, Extension: item.extension,
            TamanoBytes: file.getSize(), DriveFileId: file.getId(), Url: file.getUrl(),
            FechaCarga: TSUtils.now(), UsuarioCarga: access.user.email,
            CategoriaDocumento: item.category || payload.category || '',
            Sensibilidad: item.sensitivity || (access.sensitive ? 'SENSIBLE' : '')
          };
        });
        var saved = TSData.insertManyUnsafe('Documentos', rows, access.user.email);
        saved.forEach(function (document) { TSAudit.log('CREATE', 'Documentos', document.IdArchivo, {}, document, access.user.email, 'Carga documental', correlationId); });
        return saved;
      } catch (error) {
        createdFiles.forEach(function (file) { try { file.setTrashed(true); } catch (ignore) {} });
        throw error;
      }
    });
  }

  function listFiles(recordType, recordId) {
    var table = tableFromType(recordType);
    var access = ensureRecordAccess(table, recordId, 'read');
    TSAuth.authorize('DOCUMENTOS', 'read', { user: access.user, sensitive: access.sensitive });
    return TSData.list('Documentos', { filters: { TipoRegistro: table, IdRegistro: recordId }, sortBy: 'FechaCarga', sortDirection: 'desc' }).rows.map(function (row) {
      var copy = TSUtils.clone(row);
      delete copy.DriveFileId;
      delete copy.Url;
      return copy;
    });
  }

  function accessFile(fileId, correlationId) {
    var document = TSData.findById('Documentos', fileId, false);
    TSErrors.assert(document, 'FILE_NOT_FOUND', 'Archivo no encontrado.', null, 404);
    var table = tableFromType(document.TipoRegistro);
    var access = ensureRecordAccess(table, document.IdRegistro, 'read');
    TSAuth.authorize('DOCUMENTOS', 'read', { user: access.user, sensitive: access.sensitive || !TSUtils.isBlank(document.Sensibilidad) });
    var file;
    try { file = DriveApp.getFileById(document.DriveFileId); }
    catch (error) { throw new TSAppError('FILE_UNAVAILABLE', 'El archivo ya no esta disponible en Drive.', null, 404); }
    TSAudit.access('DOWNLOAD_FILE', 'Documentos', document.IdArchivo, access.user.email, 'Acceso documental', correlationId);
    return {
      id: document.IdArchivo, name: document.NombreArchivo, mimeType: document.MimeType,
      viewUrl: file.getUrl(), downloadUrl: 'https://drive.google.com/uc?export=download&id=' + encodeURIComponent(file.getId()),
      note: 'El acceso final tambien esta sujeto a los permisos de la carpeta en Google Drive.'
    };
  }

  return Object.freeze({ rootFolder: rootFolder, folderFor: folderFor, tableFromType: tableFromType, upload: upload, listFiles: listFiles, accessFile: accessFile });
})();
