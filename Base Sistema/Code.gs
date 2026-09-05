function doGet() {
  var template = HtmlService.createTemplateFromFile('Index');
  template.appName = TSConfig.get().appName;
  return template.evaluate().setTitle(TSConfig.get().appName).addMetaTag('viewport', 'width=device-width, initial-scale=1').setXFrameOptionsMode(HtmlService.XFrameOptionsMode.DEFAULT);
}

function include(filename) {
  TSErrors.assert(/^[A-Za-z0-9_-]+$/.test(String(filename || '')), 'INVALID_TEMPLATE', 'Nombre de plantilla no valido.', null, 400);
  return HtmlService.createHtmlOutputFromFile(filename).getContent();
}

function getBootstrapData() {
  return TSErrors.guard(function () {
    var user = TSAuth.current();
    var permissions = TSAuth.permissionSummary(user);
    var catalogs = TSAuth.can(user, 'CATALOGOS', 'read') ? TSCatalog.list({}).grouped : {};
    var forms = TSAuth.can(user, 'FORMULARIOS', 'read') ? TSForms.listPublished() : [];
    return {
      app: { name: TSConfig.get().appName, version: PropertiesService.getScriptProperties().getProperty(TSConfig.properties.setupVersion) || '', pageSize: TSConfig.get().pageSize, maxFileBytes: TSConfig.get().maxFileBytes, maxFilesPerRecord: TSConfig.get().maxFilesPerRecord, allowedExtensions: TSConfig.get().allowedExtensions, allowHardDelete: TSConfig.get().allowHardDelete },
      user: { id: user.id, email: user.email, name: user.name, roleId: user.roleId, roleName: user.roleName },
      permissions: permissions, modules: Object.keys(permissions).filter(function (module) { return permissions[module].read || permissions[module].create; }),
      catalogs: catalogs, publishedForms: forms
    };
  });
}

function getDashboardData() { return TSErrors.guard(function () { return TSSearch.dashboard(); }); }
function getPublishedForms() { return TSErrors.guard(function () { return TSForms.listPublished(); }); }
function getFormDefinition(input) { return TSErrors.guard(function () { var id = input && typeof input === 'object' ? (input.id || input.formId || input.IdFormulario) : input; return TSForms.definition(id, false); }); }
function saveFormResponse(payload) { return TSErrors.guard(function (correlationId) { return TSForms.saveResponse(payload, false, correlationId); }, 'Registro creado correctamente.'); }
function saveDraft(payload) { return TSErrors.guard(function (correlationId) { return TSForms.saveResponse(payload, true, correlationId); }, 'Borrador guardado.'); }
function listForms(options) { return TSErrors.guard(function () { return TSForms.listAdmin(options); }); }
function getFormAdmin(input) { return TSErrors.guard(function () { var id = input && typeof input === 'object' ? (input.id || input.formId || input.IdFormulario) : input; return TSForms.definition(id, true); }); }
function saveFormDefinition(payload) { return TSErrors.guard(function (correlationId) { return TSForms.saveDefinition(payload, correlationId); }, 'Cambios guardados.'); }
function saveQuestion(payload) { return TSErrors.guard(function (correlationId) { return TSForms.saveQuestion(payload, correlationId); }, 'Pregunta guardada.'); }
function duplicateQuestion(input) { return TSErrors.guard(function (correlationId) { var id = input && typeof input === 'object' ? (input.id || input.questionId || input.IdPregunta) : input; return TSForms.duplicateQuestion(id, correlationId); }, 'Pregunta duplicada.'); }
function reorderQuestions(payload) { return TSErrors.guard(function (correlationId) { return TSForms.reorder(payload, correlationId); }, 'Orden actualizado.'); }
function deactivateQuestion(input) { return TSErrors.guard(function (correlationId) { var id = input && typeof input === 'object' ? (input.id || input.questionId || input.IdPregunta) : input; var reason = input && typeof input === 'object' ? input.reason : ''; return TSForms.deactivate(id, reason, correlationId); }, 'Pregunta desactivada.'); }
function changeFormStatus(input, status) { return TSErrors.guard(function (correlationId) { var id = input && typeof input === 'object' ? (input.id || input.formId || input.IdFormulario) : input; var value = input && typeof input === 'object' ? (input.status || input.Estado) : status; return TSForms.changeStatus(id, value, correlationId); }, 'Estado actualizado.'); }

function searchRecords(filters) { return TSErrors.guard(function () { return TSSearch.search(filters || {}); }); }
function getRecord(payload) { return TSErrors.guard(function (correlationId) { return TSProcesses.get(payload, correlationId); }); }
function saveRecord(payload) { return TSErrors.guard(function (correlationId) { var result = TSProcesses.save(payload, correlationId); var row = result && result.record ? result.record : result; if (row && payload) { var table = TSProcesses.resolveTable(payload.table || payload.entity || payload.type || payload.TipoRegistro); row = TSUtils.clone(row); row.id = row[TSConfig.idFields[table]] || ''; } return row; }, 'Cambios guardados.'); }
function softDeleteRecord(payload) { return TSErrors.guard(function (correlationId) { return TSProcesses.remove(payload, correlationId); }, 'Registro eliminado logicamente.'); }
function restoreRecord(payload) { return TSErrors.guard(function (correlationId) { return TSProcesses.restore(payload, correlationId); }, 'Registro restaurado.'); }
function hardDeleteRecord(payload) { return TSErrors.guard(function (correlationId) { return TSProcesses.hardRemove(payload, correlationId); }, 'Registro eliminado definitivamente.'); }
function getRecordHistory(payload) { return TSErrors.guard(function () { return TSProcesses.history(payload); }); }
function saveFollowUp(payload) { return TSErrors.guard(function (correlationId) { return TSCases.followUp(payload, correlationId); }, 'Seguimiento guardado.'); }
function saveReferral(payload) { return TSErrors.guard(function (correlationId) { return TSCases.referral(payload, correlationId); }, 'Derivacion guardada.'); }
function saveCommitment(payload) { return TSErrors.guard(function (correlationId) { return TSCases.commitment(payload, correlationId); }, 'Compromiso guardado.'); }
function closeCase(payload) { return TSErrors.guard(function (correlationId) { return TSCases.close(payload, correlationId); }, 'Caso cerrado correctamente.'); }

function listCatalogs(options) { return TSErrors.guard(function () { return TSCatalog.list(options); }); }
function saveCatalogItem(payload) { return TSErrors.guard(function (correlationId) { return TSCatalog.save(payload, correlationId); }, 'Catalogo guardado.'); }
function toggleCatalogItem(input, active) { return TSErrors.guard(function (correlationId) { var id = input && typeof input === 'object' ? (input.id || input.IdCatalogo) : input; var value = input && typeof input === 'object' ? input.active : active; var reason = input && typeof input === 'object' ? input.reason : ''; return TSCatalog.toggle(id, value, reason, correlationId); }, 'Estado actualizado.'); }
function getDependentCatalogOptions(payload) { return TSErrors.guard(function () { return TSCatalog.dependent(payload); }); }

function uploadFiles(payload) { return TSErrors.guard(function (correlationId) { return TSDrive.upload(payload, correlationId); }, 'Archivo cargado.'); }
function listRecordFiles(payload, recordId) { return TSErrors.guard(function () { if (payload && typeof payload === 'object') return TSDrive.listFiles(payload.recordType || payload.type, payload.recordId || payload.id); return TSDrive.listFiles(payload, recordId); }); }
function getFileAccess(input) { return TSErrors.guard(function (correlationId) { var id = input && typeof input === 'object' ? (input.id || input.fileId || input.IdArchivo) : input; return TSDrive.accessFile(id, correlationId); }); }

function exportSearchResults(payload) { return TSErrors.guard(function (correlationId) { return TSExport.exportResults(payload, correlationId); }, 'Exportacion preparada.'); }
function validateImport(payload) { return TSErrors.guard(function () { var result = TSImport.validate(payload); delete result._prepared; return result; }); }
function executeImport(payload) { return TSErrors.guard(function (correlationId) { return TSImport.execute(payload, correlationId); }, 'Importacion completada.'); }
function getImportStatus(payload) { return TSErrors.guard(function () { return TSImport.status(payload); }); }

function listUsersRolesPermissions() { return TSErrors.guard(function () { return TSAuth.listAdministration(); }); }
function saveUserRole(payload) { return TSErrors.guard(function (correlationId) { return TSAuth.saveUserRole(payload, correlationId); }, 'Usuario actualizado.'); }
function savePermissions(payload) { return TSErrors.guard(function (correlationId) { return TSAuth.savePermissions(payload, correlationId); }, 'Permisos actualizados.'); }
function saveApplicationConfig(payload) { return TSErrors.guard(function (correlationId) { return TSApplicationConfig.save(payload, correlationId); }, 'Configuracion actualizada.'); }
function runSetup(options) { return TSErrors.guard(function () { return setupApplication(options); }, 'Configuracion completada.'); }

/** Endpoint opcional para clientes que prefieran un unico contrato RPC. */
function apiRequest(request) {
  request = request || {};
  var routes = {
    bootstrap: getBootstrapData, dashboard: getDashboardData, publishedForms: getPublishedForms,
    formDefinition: getFormDefinition, saveResponse: saveFormResponse, saveDraft: saveDraft,
    search: searchRecords, getRecord: getRecord, saveRecord: saveRecord, upload: uploadFiles
  };
  var handler = routes[request.action];
  if (!handler) return TSErrors.guard(function () { throw new TSAppError('UNKNOWN_ACTION', 'Accion no reconocida.', null, 404); });
  return handler(request.payload || {});
}
