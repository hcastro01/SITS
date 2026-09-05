var TSUtils = (function () {
  function uuid(prefix) {
    var value = Utilities.getUuid().replace(/-/g, '').toUpperCase();
    return (prefix ? String(prefix).toUpperCase() + '-' : '') + value;
  }

  function now() { return new Date(); }

  function normalizeEmail(value) { return String(value || '').trim().toLowerCase(); }

  function normalizeKey(value) {
    return String(value || '').trim().toUpperCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^A-Z0-9]+/g, '_').replace(/^_|_$/g, '');
  }

  function isBlank(value) { return value === null || value === undefined || String(value).trim() === ''; }

  function toBoolean(value) {
    if (typeof value === 'boolean') return value;
    if (typeof value === 'number') return value !== 0;
    return ['true', '1', 'si', 'sí', 'yes', 'y', 'x'].indexOf(String(value || '').trim().toLowerCase()) !== -1;
  }

  function asDate(value, fieldName) {
    if (value instanceof Date && !isNaN(value.getTime())) return value;
    if (isBlank(value)) return null;
    var dateOnly = String(value).match(/^(\d{4})-(\d{2})-(\d{2})$/);
    var parsed = dateOnly ? new Date(Number(dateOnly[1]), Number(dateOnly[2]) - 1, Number(dateOnly[3])) : new Date(value);
    if (isNaN(parsed.getTime())) throw new Error('Fecha invalida' + (fieldName ? ' en ' + fieldName : '') + '.');
    return parsed;
  }

  function cleanText(value, maxLength) {
    if (value === null || value === undefined) return '';
    var text = String(value).replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, '').trim();
    if (maxLength && text.length > maxLength) text = text.substring(0, maxLength);
    return text;
  }

  function safeFileName(value) {
    var name = cleanText(value || 'archivo', 180).replace(/[\\/:*?"<>|]/g, '_').replace(/\.{2,}/g, '.');
    return name || 'archivo';
  }

  function escapeHtml(value) {
    return String(value === null || value === undefined ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function parseJson(value, fallback) {
    if (value === null || value === undefined || value === '') return fallback;
    if (typeof value === 'object') return value;
    try { return JSON.parse(String(value)); } catch (ignore) { return fallback; }
  }

  function stringifyCell(value) {
    if (value === null || value === undefined) return '';
    if (value instanceof Date) return value;
    if (Array.isArray(value) || (typeof value === 'object')) return JSON.stringify(value);
    if (typeof value === 'string' && /^[=+\-@]/.test(value)) return "'" + value;
    return value;
  }

  function toSerializable(value) {
    if (value instanceof Date) return value.toISOString();
    if (Array.isArray(value)) return value.map(toSerializable);
    if (value && typeof value === 'object') {
      var out = {};
      Object.keys(value).forEach(function (key) { if (key.charAt(0) !== '_') out[key] = toSerializable(value[key]); });
      return out;
    }
    if (typeof value === 'undefined') return null;
    return value;
  }

  function clone(value) { return JSON.parse(JSON.stringify(toSerializable(value))); }

  function valuesEqual(a, b) {
    if (a instanceof Date || b instanceof Date) {
      try { return asDate(a).getTime() === asDate(b).getTime(); } catch (ignore) { return false; }
    }
    return JSON.stringify(toSerializable(a)) === JSON.stringify(toSerializable(b));
  }

  function pick(source, keys) {
    var result = {};
    source = source || {};
    keys.forEach(function (key) {
      if (Object.prototype.hasOwnProperty.call(source, key)) result[key] = source[key];
    });
    return result;
  }

  function chunk(list, size) {
    var chunks = [];
    for (var i = 0; i < list.length; i += size) chunks.push(list.slice(i, i + size));
    return chunks;
  }

  function withScriptLock(callback) {
    var lock = LockService.getScriptLock();
    var acquired = lock.tryLock(TSConfig.get().lockTimeoutMs);
    if (!acquired) throw new TSAppError('LOCK_TIMEOUT', 'El sistema esta procesando otra operacion. Intente nuevamente.', null, 409);
    try { return callback(); } finally { lock.releaseLock(); }
  }

  function csvEscape(value) {
    var text = value instanceof Date ? value.toISOString() : String(value === null || value === undefined ? '' : value);
    if (typeof value === 'string' && /^[=+\-@\t\r]/.test(text)) text = "'" + text;
    return /[",\r\n]/.test(text) ? '"' + text.replace(/"/g, '""') + '"' : text;
  }

  function correlationId() { return uuid('REQ').substring(0, 28); }

  return Object.freeze({
    uuid: uuid, now: now, normalizeEmail: normalizeEmail, normalizeKey: normalizeKey,
    isBlank: isBlank, toBoolean: toBoolean, asDate: asDate, cleanText: cleanText,
    safeFileName: safeFileName, escapeHtml: escapeHtml, parseJson: parseJson,
    stringifyCell: stringifyCell, toSerializable: toSerializable, clone: clone,
    valuesEqual: valuesEqual, pick: pick, chunk: chunk, withScriptLock: withScriptLock,
    csvEscape: csvEscape, correlationId: correlationId
  });
})();
