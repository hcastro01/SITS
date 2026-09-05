var TSAuth = (function () {
  var ACTION_COLUMNS = Object.freeze({ create: 'PuedeCrear', read: 'PuedeLeer', edit: 'PuedeEditar', delete: 'PuedeEliminar', sensitive: 'PuedeSensible', export: 'PuedeExportar' });

  function activeEmail() {
    var email = '';
    try { email = Session.getActiveUser().getEmail(); } catch (ignore) {}
    var config = TSConfig.get();
    if (!email && config.allowTestIdentity) email = PropertiesService.getScriptProperties().getProperty('TS_TEST_USER_EMAIL') || '';
    return TSUtils.normalizeEmail(email);
  }

  function current(options) {
    options = options || {};
    var email = activeEmail();
    TSErrors.assert(email, 'IDENTITY_UNAVAILABLE', 'No fue posible identificar su cuenta de Google. Verifique la modalidad de despliegue.', null, 401);
    var row = TSData.list('Usuarios', { filters: { Correo: email }, includeDeleted: true, limit: 1 }).rows[0];
    TSErrors.assert(row, 'USER_NOT_REGISTERED', 'Su usuario no esta registrado en la aplicacion.', null, 403);
    TSErrors.assert(!TSUtils.toBoolean(row.Eliminado) && TSUtils.toBoolean(row.Activo) && TSUtils.normalizeKey(row.Estado || 'ACTIVO') === 'ACTIVO', 'USER_DISABLED', 'Su usuario se encuentra inactivo.', null, 403);
    var role = TSData.findById('Roles', row.RolId, false);
    TSErrors.assert(role, 'ROLE_NOT_FOUND', 'El rol asignado no se encuentra activo.', null, 403);
    var permissions = TSData.list('Permisos', { filters: { RolId: row.RolId }, includeDeleted: false }).rows;
    if (!options.skipTouch) touchLastAccess(row, email);
    return { id: row.IdUsuario, email: email, name: row.Nombre || email, roleId: row.RolId, roleName: role.Nombre, permissions: permissions };
  }

  function touchLastAccess(user, email) {
    var key = 'touch:' + user.IdUsuario;
    try {
      var cache = CacheService.getUserCache();
      if (cache.get(key)) return;
      cache.put(key, '1', 900);
      TSData.update('Usuarios', user.IdUsuario, { UltimoAcceso: TSUtils.now() }, email);
    } catch (error) {
      console.warn('No se pudo actualizar UltimoAcceso: ' + error.message);
    }
  }

  function permissionFor(user, module) {
    module = TSUtils.normalizeKey(module);
    return user.permissions.filter(function (permission) { return TSUtils.normalizeKey(permission.Modulo) === module && TSData.isVisible(permission, false); })[0] || null;
  }

  function authorize(module, action, options) {
    options = options || {};
    var user = options.user || current();
    var permission = permissionFor(user, module);
    var column = ACTION_COLUMNS[String(action || '').toLowerCase()];
    TSErrors.assert(column, 'INVALID_ACTION', 'Accion de permiso invalida.', null, 400);
    TSErrors.assert(permission && TSUtils.toBoolean(permission[column]), 'FORBIDDEN', 'No tiene permisos para realizar esta accion.', { module: TSUtils.normalizeKey(module), action: action }, 403);
    if (options.sensitive) TSErrors.assert(TSUtils.toBoolean(permission.PuedeSensible), 'SENSITIVE_FORBIDDEN', 'No tiene permisos para consultar informacion sensible.', null, 403);
    return user;
  }

  function can(user, module, action) {
    var permission = permissionFor(user, module);
    var column = ACTION_COLUMNS[String(action || '').toLowerCase()];
    return Boolean(permission && column && TSUtils.toBoolean(permission[column]));
  }

  function isSensitiveCase(record) {
    if (!record || TSUtils.isBlank(record.NivelSensibilidad)) return false;
    var level = TSUtils.normalizeKey(record.NivelSensibilidad);
    var catalog = TSData.list('Catalogos', {
      includeDeleted: true,
      predicate: function (row) {
        if (TSUtils.normalizeKey(row.Tipo).replace(/_/g, '') !== 'NIVELSENSIBILIDAD') return false;
        return TSUtils.normalizeKey(row.Codigo) === level || TSUtils.normalizeKey(row.Valor) === level;
      }, limit: 1
    }).rows[0];
    return Boolean(catalog && TSUtils.toBoolean(catalog.EsSensible));
  }

  function maskSensitive(record) {
    var masked = TSUtils.clone(record || {});
    var fields = ['Cedula', 'Colaborador', 'IdPersona', 'Motivo', 'Resultado', 'Observaciones', 'Descripcion', 'Evidencias'];
    fields.forEach(function (field) { if (Object.prototype.hasOwnProperty.call(masked, field)) masked[field] = TSConfig.get().sensitiveMask; });
    return masked;
  }

  function isSensitiveRecord(table, record) {
    if (!record) return false;
    if (table === 'DetalleCasosSensibles') return true;
    if (table === 'Casos') return isSensitiveCase(record);
    if (record.IdCaso) {
      var parentCase = TSData.findById('Casos', record.IdCaso, true);
      return Boolean(parentCase && isSensitiveCase(parentCase));
    }
    if (table === 'RespuestasFormulario' && record.IdRegistroProceso) {
      var linkedCase = TSData.findById('Casos', record.IdRegistroProceso, true);
      return Boolean(linkedCase && isSensitiveCase(linkedCase));
    }
    if (table === 'Documentos') {
      if (!TSUtils.isBlank(record.Sensibilidad)) return true;
      var aliases = {
        CASO: 'Casos', CASOS: 'Casos', SEGUIMIENTO: 'Seguimientos', SEGUIMIENTOS: 'Seguimientos',
        DERIVACION: 'Derivaciones', DERIVACIONES: 'Derivaciones', COMPROMISO: 'Compromisos',
        COMPROMISOS: 'Compromisos', CIERRE: 'Cierres', CIERRES: 'Cierres',
        HALLAZGO: 'HallazgosRecorrido', HALLAZGOS_RECORRIDO: 'HallazgosRecorrido',
        RESPUESTA_FORMULARIO: 'RespuestasFormulario', RESPUESTAS_FORMULARIO: 'RespuestasFormulario',
        RESPUESTASFORMULARIO: 'RespuestasFormulario', HALLAZGOSRECORRIDO: 'HallazgosRecorrido'
      };
      var parentTable = aliases[TSUtils.normalizeKey(record.TipoRegistro)];
      if (parentTable) {
        var parent = parentTable === 'RespuestasFormulario'
          ? TSData.list(parentTable, { includeDeleted: true, filters: { IdRespuesta: record.IdRegistro }, limit: 1 }).rows[0]
          : TSData.findById(parentTable, record.IdRegistro, true);
        return isSensitiveRecord(parentTable, parent);
      }
    }
    return false;
  }

  function permissionSummary(user) {
    var summary = {};
    user.permissions.forEach(function (permission) {
      summary[TSUtils.normalizeKey(permission.Modulo)] = {
        create: TSUtils.toBoolean(permission.PuedeCrear), read: TSUtils.toBoolean(permission.PuedeLeer),
        edit: TSUtils.toBoolean(permission.PuedeEditar), delete: TSUtils.toBoolean(permission.PuedeEliminar),
        sensitive: TSUtils.toBoolean(permission.PuedeSensible), export: TSUtils.toBoolean(permission.PuedeExportar)
      };
    });
    return summary;
  }

  function listAdministration() {
    authorize('ADMINISTRACION', 'read');
    return { users: TSData.list('Usuarios', { includeDeleted: true, sortBy: 'Nombre' }).rows, roles: TSData.list('Roles', { includeDeleted: true, sortBy: 'Nombre' }).rows, permissions: TSData.list('Permisos', { includeDeleted: true, sortBy: 'Modulo' }).rows, modules: TSConfig.modules.slice() };
  }

  function saveUserRole(payload, correlationId) {
    var user = authorize('ADMINISTRACION', 'edit');
    payload = payload || {};
    TSValidation.required(payload, ['email', 'roleId']);
    TSErrors.assert(TSData.findById('Roles', payload.roleId, false), 'ROLE_NOT_FOUND', 'El rol seleccionado no existe.', null, 422);
    var email = TSUtils.normalizeEmail(payload.email);
    var normalizedStatus = typeof payload.status === 'boolean'
      ? (payload.status ? 'ACTIVO' : 'INACTIVO')
      : (['TRUE', '1', 'SI', 'YES'].indexOf(TSUtils.normalizeKey(payload.status)) !== -1 ? 'ACTIVO' : (TSUtils.normalizeKey(payload.status || 'ACTIVO') === 'ACTIVO' ? 'ACTIVO' : 'INACTIVO'));
    return TSUtils.withScriptLock(function () {
      var existing = TSData.list('Usuarios', { filters: { Correo: email }, includeDeleted: true, limit: 1, cache: false }).rows[0];
      if (existing && existing.RolId === TSConfig.roleIds.ADMIN && (payload.roleId !== TSConfig.roleIds.ADMIN || normalizedStatus !== 'ACTIVO')) {
        var otherAdmins = TSData.list('Usuarios', { cache: false, predicate: function (row) { return row.RolId === TSConfig.roleIds.ADMIN && String(row.IdUsuario) !== String(existing.IdUsuario) && TSUtils.normalizeKey(row.Estado || 'ACTIVO') === 'ACTIVO'; } }).total;
        TSErrors.assert(otherAdmins > 0, 'LAST_ADMIN', 'No se puede desactivar o cambiar el rol del ultimo administrador.', null, 409);
      }
      var result;
      if (existing) {
        var update = TSData.updateUnsafe('Usuarios', existing.IdUsuario, { RolId: payload.roleId, Nombre: payload.name || existing.Nombre, Estado: normalizedStatus, Activo: normalizedStatus === 'ACTIVO', Eliminado: false }, user.email, payload.expectedVersion);
        TSAudit.log('UPDATE', 'Usuarios', existing.IdUsuario, update.before, update.after, user.email, payload.reason || 'Asignacion de rol', correlationId);
        result = update.after;
      } else {
        result = TSData.insertUnsafe('Usuarios', { Correo: email, Nombre: payload.name || email, RolId: payload.roleId, Estado: normalizedStatus, Activo: normalizedStatus === 'ACTIVO' }, user.email);
        TSAudit.log('CREATE', 'Usuarios', result.IdUsuario, {}, result, user.email, payload.reason || 'Alta de usuario', correlationId);
      }
      return result;
    });
  }

  function savePermissions(payload, correlationId) {
    var user = authorize('ADMINISTRACION', 'edit');
    payload = payload || {};
    TSValidation.required(payload, ['roleId', 'module']);
    TSErrors.assert(TSData.findById('Roles', payload.roleId, false), 'ROLE_NOT_FOUND', 'El rol seleccionado no existe.', null, 422);
    var module = TSUtils.normalizeKey(payload.module);
    TSErrors.assert(TSConfig.modules.indexOf(module) !== -1, 'INVALID_MODULE', 'El modulo indicado no existe.', null, 422);
    var values = { RolId: payload.roleId, Modulo: module, PuedeCrear: TSUtils.toBoolean(payload.create), PuedeLeer: TSUtils.toBoolean(payload.read), PuedeEditar: TSUtils.toBoolean(payload.edit), PuedeEliminar: TSUtils.toBoolean(payload.delete), PuedeSensible: TSUtils.toBoolean(payload.sensitive), PuedeExportar: TSUtils.toBoolean(payload.export), Activo: true, Eliminado: false };
    if (payload.roleId === TSConfig.roleIds.ADMIN && module === 'ADMINISTRACION') TSErrors.assert(values.PuedeLeer && values.PuedeEditar, 'CORE_ADMIN_PERMISSION', 'El rol Administrador debe conservar lectura y edicion de Administracion.', null, 409);
    return TSUtils.withScriptLock(function () {
      var existing = TSData.list('Permisos', { filters: { RolId: payload.roleId, Modulo: module }, includeDeleted: true, limit: 1, cache: false }).rows[0];
      if (existing) {
        var updated = TSData.updateUnsafe('Permisos', existing.IdPermiso, values, user.email, payload.expectedVersion);
        TSAudit.log('UPDATE', 'Permisos', existing.IdPermiso, updated.before, updated.after, user.email, payload.reason || 'Cambio de permisos', correlationId);
        return updated.after;
      }
      var created = TSData.insertUnsafe('Permisos', values, user.email);
      TSAudit.log('CREATE', 'Permisos', created.IdPermiso, {}, created, user.email, payload.reason || 'Alta de permisos', correlationId);
      return created;
    });
  }

  return Object.freeze({ activeEmail: activeEmail, current: current, authorize: authorize, can: can, isSensitiveCase: isSensitiveCase, isSensitiveRecord: isSensitiveRecord, maskSensitive: maskSensitive, permissionSummary: permissionSummary, listAdministration: listAdministration, saveUserRole: saveUserRole, savePermissions: savePermissions });
})();
