import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { get, HttpError, post, SESSION_EXPIRED_EVENT } from './client';

function mockFetchOnce(status: number, body: unknown, ok = status >= 200 && status < 300) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok,
    status,
    statusText: 'Error',
    json: () => Promise.resolve(body),
  }));
}

describe('cliente HTTP', () => {
  beforeEach(() => { vi.restoreAllMocks(); });
  afterEach(() => { vi.unstubAllGlobals(); });

  it('devuelve el cuerpo JSON en una respuesta exitosa', async () => {
    mockFetchOnce(200, { hola: 'mundo' });
    const resultado = await get<{ hola: string }>('/algo');
    expect(resultado).toEqual({ hola: 'mundo' });
  });

  it('lanza HttpError con code/message/correlationId en una respuesta de error', async () => {
    mockFetchOnce(403, { ok: false, code: 'FORBIDDEN', message: 'No tiene permisos.', correlationId: 'abc' });
    await expect(get('/algo')).rejects.toMatchObject({ status: 403, code: 'FORBIDDEN', message: 'No tiene permisos.' });
  });

  it('siempre envía las peticiones con credentials: include', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve({}) });
    vi.stubGlobal('fetch', fetchMock);
    await post('/algo', { x: 1 });
    expect(fetchMock).toHaveBeenCalledWith(expect.any(String), expect.objectContaining({ credentials: 'include' }));
  });

  it('degrada a un HttpError genérico si el cuerpo de error no es JSON válido', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false, status: 500, statusText: 'Internal Server Error',
      json: () => Promise.reject(new Error('no es JSON')),
    }));
    try {
      await get('/algo');
      throw new Error('debía lanzar');
    } catch (error) {
      expect(error).toBeInstanceOf(HttpError);
      expect((error as HttpError).status).toBe(500);
    }
  });

  it('notifica al contexto de autenticación cuando la sesión expiró', async () => {
    mockFetchOnce(401, { ok: false, code: 'SESSION_REQUIRED', message: 'Sesión expirada.', correlationId: 'c1' });
    const listener = vi.fn();
    window.addEventListener(SESSION_EXPIRED_EVENT, listener);
    await expect(get('/privado')).rejects.toBeInstanceOf(HttpError);
    expect(listener).toHaveBeenCalledOnce();
    window.removeEventListener(SESSION_EXPIRED_EVENT, listener);
  });
});
