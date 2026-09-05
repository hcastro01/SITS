/**
 * Inicializacion idempotente. Puede ejecutarse desde el editor o mediante runSetup().
 * Nunca reemplaza encabezados incompatibles ni borra datos existentes.
 */
function setupApplication(options) {
  options = options || {};
  authorizeSetupCaller_();
  return TSUtils.withScriptLock(function () {
    var config = TSConfig.get();
    if (options.spreadsheetId || options.rootFolderId) config = TSConfig.update({ spreadsheetId: options.spreadsheetId || config.spreadsheetId, rootFolderId: options.rootFolderId || config.rootFolderId });
    var book;
    if (config.spreadsheetId) {
      try { book = SpreadsheetApp.openById(config.spreadsheetId); }
      catch (error) { throw new TSAppError('SETUP_SPREADSHEET_UNAVAILABLE', 'El Spreadsheet ID configurado no es accesible.', null, 400); }
    } else {
      book = SpreadsheetApp.create(config.appName + ' - Base de Datos');
      config = TSConfig.update({ spreadsheetId: book.getId() });
    }
    try { book.setSpreadsheetLocale(config.locale); } catch (ignore) {}
    try { book.setSpreadsheetTimeZone(config.timeZone); } catch (ignore2) {}

    Object.keys(TSConfig.schemas).forEach(function (table) { ensureSetupSheet_(book, table, TSConfig.schema(table)); });

    var root;
    if (config.rootFolderId) {
      try { root = DriveApp.getFolderById(config.rootFolderId); root.getName(); }
      catch (error2) { throw new TSAppError('SETUP_FOLDER_UNAVAILABLE', 'El Folder ID configurado no es accesible.', null, 400); }
    } else {
      root = DriveApp.createFolder(config.folderName);
      config = TSConfig.update({ rootFolderId: root.getId() });
    }
    var importFolderIterator = root.getFoldersByName('Importaciones');
    var importFolder = importFolderIterator.hasNext() ? importFolderIterator.next() : root.createFolder('Importaciones');
    PropertiesService.getScriptProperties().setProperty(TSConfig.properties.importFolderId, importFolder.getId());

    var setupUser = TSAuth.activeEmail() || 'SETUP_LOCAL';
    seedRolesPermissions_(setupUser);
    seedTechnicalCatalogs_(setupUser);
    seedConfiguration_(setupUser);
    if (TSAuth.activeEmail()) {
      var setupExistingUser = TSData.list('Usuarios', { filters: { Correo: TSAuth.activeEmail() }, includeDeleted: true, cache: false, limit: 1 }).rows[0];
      if (!setupExistingUser) TSData.insertUnsafe('Usuarios', { Correo: TSAuth.activeEmail(), Nombre: Session.getActiveUser().getEmail(), RolId: TSConfig.roleIds.ADMIN, Estado: 'ACTIVO', Activo: true, Eliminado: false }, setupUser);
    }
    PropertiesService.getScriptProperties().setProperty(TSConfig.properties.setupVersion, config.setupVersion);
    return {
      application: config.appName, version: config.setupVersion, spreadsheetUrl: book.getUrl(),
      rootFolderUrl: root.getUrl(), importFolderUrl: importFolder.getUrl(), sheets: Object.keys(TSConfig.schemas),
      administratorCreated: Boolean(TSAuth.activeEmail()),
      warning: TSAuth.activeEmail() ? '' : 'No se identifico correo activo. Registre manualmente el primer usuario administrador antes del despliegue.'
    };
  });
}

function authorizeSetupCaller_() {
  var active = '';
  var effective = '';
  try { active = TSUtils.normalizeEmail(Session.getActiveUser().getEmail()); } catch (ignore) {}
  try { effective = TSUtils.normalizeEmail(Session.getEffectiveUser().getEmail()); } catch (ignore2) {}
  TSErrors.assert(active && effective && active === effective, 'SETUP_OWNER_ONLY', 'Solo el propietario que despliega el proyecto puede ejecutar la configuracion.', null, 403);
  var config = TSConfig.get();
  if (!config.spreadsheetId) return true;
  var hasUsers = false;
  try {
    var book = SpreadsheetApp.openById(config.spreadsheetId);
    var users = book.getSheetByName('Usuarios');
    hasUsers = Boolean(users && users.getLastRow() > 1);
  } catch (ignore3) {}
  if (hasUsers) TSAuth.authorize('ADMINISTRACION', 'edit');
  return true;
}

function ensureSetupSheet_(book, table, headers) {
  var target = book.getSheetByName(table);
  if (!target) target = book.insertSheet(table);
  var lastColumn = target.getLastColumn();
  var lastRow = target.getLastRow();
  if (lastRow === 0 || lastColumn === 0 || TSUtils.isBlank(target.getRange(1, 1).getDisplayValue())) {
    target.getRange(1, 1, 1, headers.length).setValues([headers]);
  } else {
    var checkLength = Math.min(lastColumn, headers.length);
    var actual = target.getRange(1, 1, 1, checkLength).getDisplayValues()[0];
    for (var i = 0; i < checkLength; i++) {
      if (actual[i] !== headers[i]) throw new TSAppError('SETUP_SCHEMA_CONFLICT', 'La hoja ' + table + ' tiene encabezados incompatibles y no fue modificada.', { column: i + 1, expected: headers[i], actual: actual[i] }, 409);
    }
    if (lastColumn < headers.length) {
      target.insertColumnsAfter(Math.max(1, lastColumn), headers.length - lastColumn);
      target.getRange(1, lastColumn + 1, 1, headers.length - lastColumn).setValues([headers.slice(lastColumn)]);
    }
  }
  target.setFrozenRows(1);
  target.getRange(1, 1, 1, headers.length).setFontWeight('bold').setFontColor('#FFFFFF').setBackground('#355C7D').setWrap(true);
  target.setRowHeight(1, 34);
  headers.forEach(function (header, index) {
    if (/^Fecha/.test(header) && target.getMaxRows() > 1) target.getRange(2, index + 1, target.getMaxRows() - 1, 1).setNumberFormat('yyyy-mm-dd hh:mm:ss');
  });
  TSData.invalidate(table);
}

function seedRolesPermissions_(userEmail) {
  var roles = [
    { IdRol: TSConfig.roleIds.ADMIN, Nombre: 'Administrador', Descripcion: 'Acceso integral y administracion de seguridad.' },
    { IdRol: TSConfig.roleIds.COORDINATOR, Nombre: 'Coordinador / Relaciones Laborales', Descripcion: 'Supervision consolidada de procesos.' },
    { IdRol: TSConfig.roleIds.SOCIAL_WORKER, Nombre: 'Trabajador Social', Descripcion: 'Captura y gestion operativa autorizada.' },
    { IdRol: TSConfig.roleIds.READ_ONLY, Nombre: 'Consulta', Descripcion: 'Consulta sin modificacion segun permisos.' },
    { IdRol: TSConfig.roleIds.MANAGEMENT, Nombre: 'Gerencia', Descripcion: 'Indicadores y consulta agregada sin detalle sensible.' }
  ];
  roles.forEach(function (role) {
    if (!TSData.findById('Roles', role.IdRol, true)) TSData.insertUnsafe('Roles', { IdRol: role.IdRol, Nombre: role.Nombre, Descripcion: role.Descripcion, Activo: true, Eliminado: false }, userEmail);
  });
  roles.forEach(function (role) {
    TSConfig.modules.forEach(function (module) {
      var rights = setupRights_(role.IdRol, module);
      var permissionId = 'PERM-' + role.IdRol + '-' + module;
      if (!TSData.findById('Permisos', permissionId, true)) TSData.insertUnsafe('Permisos', {
        IdPermiso: permissionId,
        RolId: role.IdRol, Modulo: module, PuedeCrear: rights.create, PuedeLeer: rights.read,
        PuedeEditar: rights.edit, PuedeEliminar: rights.delete, PuedeSensible: rights.sensitive,
        PuedeExportar: rights.export, Activo: true, Eliminado: false
      }, userEmail);
    });
  });
}

function setupRights_(roleId, module) {
  if (roleId === TSConfig.roleIds.ADMIN) return { create: true, read: true, edit: true, delete: true, sensitive: true, export: true };
  var operational = ['ATENCIONES', 'CASOS', 'NOVEDADES', 'RECORRIDOS', 'SEGUIMIENTOS', 'DERIVACIONES', 'COMPROMISOS'];
  var baseRead = ['DASHBOARD', 'ATENCIONES', 'CASOS', 'NOVEDADES', 'RECORRIDOS', 'SEGUIMIENTOS', 'DERIVACIONES', 'COMPROMISOS', 'PERSONAS', 'FORMULARIOS', 'RESPUESTAS', 'CATALOGOS', 'DOCUMENTOS', 'BUSQUEDA', 'REPORTES'];
  if (roleId === TSConfig.roleIds.COORDINATOR) {
    return { create: operational.concat(['RESPUESTAS', 'DOCUMENTOS']).indexOf(module) !== -1, read: baseRead.concat(['AUDITORIA']).indexOf(module) !== -1, edit: operational.concat(['DOCUMENTOS']).indexOf(module) !== -1, delete: false, sensitive: false, export: module === 'REPORTES' || module === 'BUSQUEDA' };
  }
  if (roleId === TSConfig.roleIds.SOCIAL_WORKER) {
    return { create: operational.concat(['PERSONAS', 'RESPUESTAS', 'DOCUMENTOS']).indexOf(module) !== -1, read: baseRead.indexOf(module) !== -1, edit: operational.concat(['PERSONAS', 'RESPUESTAS', 'DOCUMENTOS']).indexOf(module) !== -1, delete: false, sensitive: false, export: module === 'REPORTES' };
  }
  if (roleId === TSConfig.roleIds.READ_ONLY) {
    return { create: false, read: baseRead.filter(function (name) { return ['RESPUESTAS', 'REPORTES'].indexOf(name) === -1; }).indexOf(module) !== -1, edit: false, delete: false, sensitive: false, export: false };
  }
  if (roleId === TSConfig.roleIds.MANAGEMENT) {
    return { create: false, read: ['DASHBOARD', 'CASOS', 'ATENCIONES', 'NOVEDADES', 'RECORRIDOS', 'SEGUIMIENTOS', 'DERIVACIONES', 'COMPROMISOS', 'BUSQUEDA', 'REPORTES', 'CATALOGOS'].indexOf(module) !== -1, edit: false, delete: false, sensitive: false, export: module === 'REPORTES' };
  }
  return { create: false, read: false, edit: false, delete: false, sensitive: false, export: false };
}

function seedTechnicalCatalogs_(userEmail) {
  var catalogs = [
    ['CAT-ESTFORM-BORRADOR', 'ESTADO_FORMULARIO', 'BORRADOR', 'Borrador', 10],
    ['CAT-ESTFORM-PUBLICADO', 'ESTADO_FORMULARIO', 'PUBLICADO', 'Publicado', 20],
    ['CAT-ESTFORM-INACTIVO', 'ESTADO_FORMULARIO', 'INACTIVO', 'Inactivo', 30],
    ['CAT-ESTCASO-BORRADOR', 'ESTADO_CASO', 'BORRADOR', 'Borrador', 10],
    ['CAT-ESTCASO-REGISTRADO', 'ESTADO_CASO', 'REGISTRADO', 'Registrado', 20],
    ['CAT-ESTCASO-GESTION', 'ESTADO_CASO', 'EN_GESTION', 'En Gestion', 30],
    ['CAT-ESTCASO-CERRADO', 'ESTADO_CASO', 'CERRADO', 'Cerrado', 40]
  ];
  catalogs.forEach(function (item) {
    if (!TSData.findById('Catalogos', item[0], true)) TSData.insertUnsafe('Catalogos', { IdCatalogo: item[0], Tipo: item[1], Codigo: item[2], Valor: item[3], Orden: item[4], EsSensible: false, Activo: true, Eliminado: false }, userEmail);
  });
}

function seedConfiguration_(userEmail) {
  var config = TSConfig.get();
  var values = [
    ['APP_NAME', config.appName, 'Nombre visible de la aplicacion', 'TEXTO', false],
    ['PAGE_SIZE', config.pageSize, 'Filas por pagina', 'NUMERO', true],
    ['MAX_FILE_BYTES', config.maxFileBytes, 'Tamano maximo por archivo', 'NUMERO', true],
    ['MAX_FILES_PER_RECORD', config.maxFilesPerRecord, 'Cantidad maxima de archivos por registro', 'NUMERO', true],
    ['ALLOW_HARD_DELETE', config.allowHardDelete, 'Habilitacion explicita para una futura operacion administrativa de borrado fisico', 'BOOLEANO', true],
    ['SETUP_VERSION', config.setupVersion, 'Version de estructura instalada', 'TEXTO', false]
  ];
  values.forEach(function (item) {
    TSData.upsertUnsafe('Configuracion', 'Clave', item[0], { Valor: item[1], Descripcion: item[2], Tipo: item[3], Editable: item[4], FechaActualizacion: TSUtils.now(), ActualizadoPor: userEmail }, userEmail);
  });
}
