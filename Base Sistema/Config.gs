/**
 * Configuracion central y modelo fisico de datos.
 * Los IDs nunca se envian al cliente. Se guardan en Script Properties.
 */
var TSConfig = (function () {
  var PROP_SPREADSHEET_ID = 'TS_SPREADSHEET_ID';
  var PROP_ROOT_FOLDER_ID = 'TS_ROOT_FOLDER_ID';
  var PROP_CONFIG_JSON = 'TS_CONFIG_JSON';
  var PROP_SETUP_VERSION = 'TS_SETUP_VERSION';
  var PROP_IMPORT_FOLDER_ID = 'TS_IMPORT_FOLDER_ID';

  var DEFAULTS = Object.freeze({
    appName: 'Sistema Integral de Gestion de Trabajo Social',
    locale: 'es_EC',
    timeZone: 'America/Guayaquil',
    pageSize: 20,
    maxPageSize: 100,
    maxExportRows: 5000,
    maxImportRows: 5000,
    maxFileBytes: 10 * 1024 * 1024,
    maxFilesPerRecord: 10,
    allowedExtensions: ['jpg', 'jpeg', 'png', 'pdf', 'doc', 'docx', 'xls', 'xlsx'],
    allowedMimeTypes: [
      'image/jpeg', 'image/png', 'application/pdf', 'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    ],
    cacheSeconds: 300,
    lockTimeoutMs: 30000,
    setupVersion: '1.0.0',
    folderName: 'TrabajoSocial',
    allowTestIdentity: false,
    shareExportsWithRequester: true,
    allowHardDelete: false,
    sensitiveMask: '[RESTRINGIDO]'
  });

  var META = [
    'Activo', 'Eliminado', 'FechaCreacion', 'CreadoPor', 'FechaActualizacion',
    'ActualizadoPor', 'FechaEliminacion', 'UsuarioEliminacion', 'MotivoEliminacion',
    'Version', 'ArchivoFuente', 'HojaFuente', 'RegistroFuente', 'FechaImportacion',
    'UsuarioImportacion'
  ];

  var SCHEMAS = {
    Usuarios: ['IdUsuario', 'Correo', 'Nombre', 'RolId', 'Estado', 'UltimoAcceso'].concat(META),
    Roles: ['IdRol', 'Nombre', 'Descripcion'].concat(META),
    Permisos: ['IdPermiso', 'RolId', 'Modulo', 'PuedeCrear', 'PuedeLeer', 'PuedeEditar', 'PuedeEliminar', 'PuedeSensible', 'PuedeExportar'].concat(META),
    Personas: ['IdPersona', 'CodigoEmpleado', 'Cedula', 'Nombre', 'Cargo', 'Area', 'Departamento', 'Centro', 'SubCentro', 'Turno', 'EstadoLaboral'].concat(META),
    Formularios: ['IdFormulario', 'Nombre', 'Descripcion', 'Proceso', 'Estado', 'Responsable', 'FechaPublicacion'].concat(META),
    Preguntas: ['IdPregunta', 'IdFormulario', 'Etiqueta', 'Descripcion', 'Tipo', 'Obligatoria', 'Orden', 'Categoria', 'Subcategoria', 'ValorPredeterminado', 'TextoAyuda', 'Visible', 'SoloLectura', 'LongitudMaxima', 'Validacion', 'Sensibilidad', 'CondicionVisibilidad', 'CampoDependiente', 'ValorDependiente', 'Formula'].concat(META),
    OpcionesPregunta: ['IdOpcion', 'IdPregunta', 'Valor', 'Etiqueta', 'Orden', 'IdCatalogo', 'IdOpcionPadre'].concat(META),
    ReglasFormulario: ['IdRegla', 'IdFormulario', 'IdPreguntaOrigen', 'Operador', 'ValorComparacion', 'IdPreguntaDestino', 'Accion', 'Mensaje', 'Orden'].concat(META),
    RespuestasFormulario: ['IdDetalleRespuesta', 'IdRespuesta', 'IdEnvioCliente', 'IdFormulario', 'IdPregunta', 'IdRegistroProceso', 'EstadoRespuesta', 'ValorTexto', 'ValorNumero', 'ValorFecha', 'ValorBooleano', 'ValorOpcion', 'FechaRespuesta', 'UsuarioRespuesta'].concat(META),
    Atenciones: ['IdAtencion', 'Fecha', 'Hora', 'IdPersona', 'Colaborador', 'Responsable', 'TipoAtencion', 'Motivo', 'Canal', 'Gestion', 'Resultado', 'RequiereSeguimiento', 'GeneraCaso', 'Observaciones', 'Evidencias', 'Estado'].concat(META),
    Casos: ['IdCaso', 'CodigoCaso', 'FechaApertura', 'IdPersona', 'Colaborador', 'Responsable', 'TipoCaso', 'SubtipoCaso', 'Prioridad', 'NivelSensibilidad', 'EstadoCaso', 'TipoGestion', 'TipoEvento', 'Area', 'Turno', 'CondicionLaboral', 'Restriccion', 'FechaInicioRestriccion', 'Derivacion', 'UltimoSeguimiento', 'FechaCierre', 'MotivoCierre', 'Resultado', 'Evidencias'].concat(META),
    DetalleCasosSensibles: ['IdDetalleSensible', 'IdCaso', 'DescripcionSensible', 'Antecedentes', 'DiagnosticoSocial', 'Intervencion', 'NotasPrivadas'].concat(META),
    Novedades: ['IdNovedad', 'Fecha', 'Hora', 'Responsable', 'Fuente', 'Tipo', 'Subtipo', 'Area', 'Turno', 'Lugar', 'Descripcion', 'Impacto', 'Prioridad', 'AccionInmediata', 'GeneraAtencion', 'GeneraCaso', 'Estado', 'Evidencias'].concat(META),
    Recorridos: ['IdRecorrido', 'Fecha', 'HoraInicio', 'HoraFin', 'Responsable', 'Planta', 'Area', 'Turno', 'Objetivo', 'Observaciones', 'PersonasContactadas', 'NovedadesDetectadas', 'Acciones', 'Evidencias'].concat(META),
    HallazgosRecorrido: ['IdHallazgo', 'IdRecorrido', 'TipoHallazgo', 'Categoria', 'Subcategoria', 'Area', 'Descripcion', 'Prioridad', 'Accion', 'GeneraNovedad', 'IdNovedad', 'GeneraCaso', 'IdCaso', 'Estado'].concat(META),
    Seguimientos: ['IdSeguimiento', 'IdCaso', 'Fecha', 'Hora', 'Responsable', 'TipoSeguimiento', 'Canal', 'Tecnica', 'Descripcion', 'Resultado', 'ProximaAccion', 'FechaProximaAccion', 'Estado', 'Evidencias'].concat(META),
    Derivaciones: ['IdDerivacion', 'IdCaso', 'Fecha', 'AreaDestino', 'ResponsableDestino', 'Motivo', 'Estado', 'FechaRespuesta', 'Resultado', 'FechaCierre', 'Observaciones'].concat(META),
    Compromisos: ['IdCompromiso', 'IdCaso', 'IdSeguimiento', 'FechaCreacionCompromiso', 'Responsable', 'Descripcion', 'FechaLimite', 'Estado', 'FechaCumplimiento', 'Evidencia', 'Observacion'].concat(META),
    Cierres: ['IdCierre', 'IdCaso', 'FechaCierreCaso', 'Responsable', 'MotivoCierre', 'ResultadoFinal', 'Evidencia', 'RequiereMonitoreo', 'Observacion'].concat(META),
    Documentos: ['IdArchivo', 'IdRegistro', 'TipoRegistro', 'NombreArchivo', 'MimeType', 'Extension', 'TamanoBytes', 'DriveFileId', 'Url', 'FechaCarga', 'UsuarioCarga', 'CategoriaDocumento', 'Sensibilidad'].concat(META),
    Catalogos: ['IdCatalogo', 'Tipo', 'Codigo', 'Valor', 'Descripcion', 'Orden', 'IdCatalogoPadre', 'TipoPadre', 'CodigoPadre', 'EsSensible'].concat(META),
    Auditoria: ['IdAuditoria', 'Tabla', 'IdRegistro', 'Accion', 'Usuario', 'FechaHora', 'Campo', 'ValorAnterior', 'ValorNuevo', 'Motivo', 'CorrelationId'],
    Configuracion: ['Clave', 'Valor', 'Descripcion', 'Tipo', 'Editable', 'FechaActualizacion', 'ActualizadoPor'],
    Importaciones: ['IdImportacion', 'TablaDestino', 'ArchivoFuente', 'HojaFuente', 'TotalFilas', 'FilasImportadas', 'FilasError', 'Estado', 'Errores', 'FechaInicio', 'FechaFin', 'UsuarioImportacion'].concat(META.filter(function (field) { return ['ArchivoFuente', 'HojaFuente', 'UsuarioImportacion'].indexOf(field) === -1; }))
  };

  var ID_FIELDS = {
    Usuarios: 'IdUsuario', Roles: 'IdRol', Permisos: 'IdPermiso', Personas: 'IdPersona',
    Formularios: 'IdFormulario', Preguntas: 'IdPregunta', OpcionesPregunta: 'IdOpcion',
    ReglasFormulario: 'IdRegla', RespuestasFormulario: 'IdDetalleRespuesta',
    Atenciones: 'IdAtencion', Casos: 'IdCaso', DetalleCasosSensibles: 'IdDetalleSensible',
    Novedades: 'IdNovedad', Recorridos: 'IdRecorrido', HallazgosRecorrido: 'IdHallazgo',
    Seguimientos: 'IdSeguimiento', Derivaciones: 'IdDerivacion', Compromisos: 'IdCompromiso',
    Cierres: 'IdCierre', Documentos: 'IdArchivo', Catalogos: 'IdCatalogo',
    Auditoria: 'IdAuditoria', Configuracion: 'Clave', Importaciones: 'IdImportacion'
  };

  var TABLE_MODULES = {
    Usuarios: 'ADMINISTRACION', Roles: 'ADMINISTRACION', Permisos: 'ADMINISTRACION',
    Personas: 'PERSONAS', Formularios: 'FORMULARIOS', Preguntas: 'FORMULARIOS',
    OpcionesPregunta: 'FORMULARIOS', ReglasFormulario: 'FORMULARIOS',
    RespuestasFormulario: 'RESPUESTAS', Atenciones: 'ATENCIONES', Casos: 'CASOS',
    DetalleCasosSensibles: 'CASOS', Novedades: 'NOVEDADES', Recorridos: 'RECORRIDOS',
    HallazgosRecorrido: 'RECORRIDOS', Seguimientos: 'SEGUIMIENTOS',
    Derivaciones: 'DERIVACIONES', Compromisos: 'COMPROMISOS', Cierres: 'CASOS',
    Documentos: 'DOCUMENTOS', Catalogos: 'CATALOGOS', Auditoria: 'AUDITORIA',
    Configuracion: 'ADMINISTRACION', Importaciones: 'IMPORTACION'
  };

  var MODULES = [
    'DASHBOARD', 'ATENCIONES', 'CASOS', 'NOVEDADES', 'RECORRIDOS', 'SEGUIMIENTOS',
    'DERIVACIONES', 'COMPROMISOS', 'PERSONAS', 'FORMULARIOS', 'RESPUESTAS', 'CATALOGOS',
    'DOCUMENTOS', 'BUSQUEDA', 'REPORTES', 'IMPORTACION', 'AUDITORIA', 'ADMINISTRACION'
  ];

  var ROLE_IDS = Object.freeze({
    ADMIN: 'ROLE_ADMIN', COORDINATOR: 'ROLE_COORDINADOR', SOCIAL_WORKER: 'ROLE_TRABAJADOR_SOCIAL',
    READ_ONLY: 'ROLE_CONSULTA', MANAGEMENT: 'ROLE_GERENCIA'
  });

  var PROCESS_TABLES = [
    'Atenciones', 'Casos', 'Novedades', 'Recorridos', 'HallazgosRecorrido',
    'Seguimientos', 'Derivaciones', 'Compromisos', 'Cierres', 'Personas'
  ];

  function get() {
    var custom = {};
    try { custom = JSON.parse(PropertiesService.getScriptProperties().getProperty(PROP_CONFIG_JSON) || '{}'); } catch (ignore) {}
    var result = {};
    Object.keys(DEFAULTS).forEach(function (key) { result[key] = DEFAULTS[key]; });
    Object.keys(custom).forEach(function (key) { result[key] = custom[key]; });
    result.spreadsheetId = PropertiesService.getScriptProperties().getProperty(PROP_SPREADSHEET_ID) || '';
    result.rootFolderId = PropertiesService.getScriptProperties().getProperty(PROP_ROOT_FOLDER_ID) || '';
    return result;
  }

  function update(values) {
    values = values || {};
    var props = PropertiesService.getScriptProperties();
    if (Object.prototype.hasOwnProperty.call(values, 'spreadsheetId')) props.setProperty(PROP_SPREADSHEET_ID, String(values.spreadsheetId || ''));
    if (Object.prototype.hasOwnProperty.call(values, 'rootFolderId')) props.setProperty(PROP_ROOT_FOLDER_ID, String(values.rootFolderId || ''));
    var current = get();
    var custom = {};
    Object.keys(DEFAULTS).forEach(function (key) {
      custom[key] = Object.prototype.hasOwnProperty.call(values, key) ? values[key] : current[key];
    });
    props.setProperty(PROP_CONFIG_JSON, JSON.stringify(custom));
    return get();
  }

  function schema(table) {
    if (!SCHEMAS[table]) throw new Error('Tabla no configurada: ' + table);
    return SCHEMAS[table].slice();
  }

  return Object.freeze({
    get: get, update: update, schema: schema,
    schemas: SCHEMAS, idFields: ID_FIELDS, tableModules: TABLE_MODULES,
    modules: MODULES, roleIds: ROLE_IDS, processTables: PROCESS_TABLES,
    properties: Object.freeze({ spreadsheetId: PROP_SPREADSHEET_ID, rootFolderId: PROP_ROOT_FOLDER_ID, setupVersion: PROP_SETUP_VERSION, importFolderId: PROP_IMPORT_FOLDER_ID })
  });
})();

var TSApplicationConfig = (function () {
  var ALLOWED = ['appName', 'locale', 'timeZone', 'pageSize', 'maxPageSize', 'maxExportRows', 'maxImportRows', 'maxFileBytes', 'maxFilesPerRecord', 'cacheSeconds', 'shareExportsWithRequester', 'allowHardDelete'];
  function save(payload, correlationId) {
    var user = TSAuth.authorize('ADMINISTRACION', 'edit');
    payload = payload || {};
    var values = TSUtils.pick(payload, ALLOWED);
    ['pageSize', 'maxPageSize', 'maxExportRows', 'maxImportRows', 'maxFileBytes', 'maxFilesPerRecord', 'cacheSeconds'].forEach(function (field) {
      if (!Object.prototype.hasOwnProperty.call(values, field)) return;
      values[field] = Number(values[field]);
      TSErrors.assert(isFinite(values[field]) && values[field] > 0, 'INVALID_CONFIG', 'Valor de configuracion invalido: ' + field, { field: field }, 422);
    });
    var currentConfig = TSConfig.get();
    var finalPageSize = values.pageSize || currentConfig.pageSize;
    var finalMaxPageSize = values.maxPageSize || currentConfig.maxPageSize;
    TSErrors.assert(finalPageSize <= finalMaxPageSize, 'INVALID_CONFIG', 'pageSize no puede superar maxPageSize.', null, 422);
    if (values.appName !== undefined) {
      values.appName = TSUtils.cleanText(values.appName, 150);
      TSErrors.assert(values.appName, 'INVALID_CONFIG', 'El nombre de la aplicacion es obligatorio.', null, 422);
    }
    if (values.shareExportsWithRequester !== undefined) values.shareExportsWithRequester = TSUtils.toBoolean(values.shareExportsWithRequester);
    if (values.allowHardDelete !== undefined) values.allowHardDelete = TSUtils.toBoolean(values.allowHardDelete);
    return TSUtils.withScriptLock(function () {
      var before = TSConfig.get();
      var after = TSConfig.update(values);
      seedConfiguration_(user.email);
      TSAudit.log('UPDATE', 'Configuracion', 'APP_CONFIG', TSUtils.pick(before, ALLOWED), TSUtils.pick(after, ALLOWED), user.email, payload.reason || 'Actualizacion de configuracion', correlationId);
      return TSUtils.pick(after, ALLOWED);
    });
  }
  return Object.freeze({ save: save });
})();
