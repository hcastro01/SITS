function TSAppError(code, message, details, status) {
  this.name = 'TSAppError';
  this.code = code || 'APP_ERROR';
  this.message = message || 'No fue posible completar la operacion.';
  this.details = details || null;
  this.status = status || 400;
  if (Error.captureStackTrace) Error.captureStackTrace(this, TSAppError);
}
TSAppError.prototype = Object.create(Error.prototype);
TSAppError.prototype.constructor = TSAppError;

var TSErrors = (function () {
  function friendly(error, correlationId) {
    if (error instanceof TSAppError || (error && error.name === 'TSAppError')) {
      return { code: error.code, message: error.message, details: TSUtils.toSerializable(error.details), correlationId: correlationId };
    }
    console.error('Error interno [' + correlationId + ']: ' + (error && error.stack ? error.stack : error));
    return { code: 'INTERNAL_ERROR', message: 'Ocurrio un error al procesar la solicitud.', details: null, correlationId: correlationId };
  }

  function guard(callback, successMessage) {
    var correlationId = TSUtils.correlationId();
    try {
      var data = callback(correlationId);
      return TSUtils.toSerializable({ ok: true, data: data === undefined ? null : data, message: successMessage || '', correlationId: correlationId });
    } catch (error) {
      return { ok: false, data: null, message: error instanceof TSAppError ? error.message : 'Error al procesar.', error: friendly(error, correlationId), correlationId: correlationId };
    }
  }

  function assert(condition, code, message, details, status) {
    if (!condition) throw new TSAppError(code, message, details, status);
  }

  return Object.freeze({ guard: guard, assert: assert, friendly: friendly });
})();
