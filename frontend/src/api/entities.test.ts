import { afterEach, describe, expect, it, vi } from 'vitest';
import { createEntityClient } from './entities';

describe('createEntityClient', () => {
  afterEach(() => { vi.unstubAllGlobals(); });

  function mockFetch() {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve({}) });
    vi.stubGlobal('fetch', fetchMock);
    return fetchMock;
  }

  it('list() llama al endpoint base con incluir_eliminados', async () => {
    const fetchMock = mockFetch();
    const cliente = createEntityClient('/atenciones', 'id_atencion');
    await cliente.list();
    expect(fetchMock.mock.calls[0][0]).toContain('/atenciones?incluir_eliminados=false');
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: 'GET' });
  });

  it('softDelete() llama a POST {base}/{id}/eliminacion', async () => {
    const fetchMock = mockFetch();
    const cliente = createEntityClient('/atenciones', 'id_atencion');
    await cliente.softDelete('a1', { motivo: 'x', expected_version: 1 });
    expect(fetchMock.mock.calls[0][0]).toContain('/atenciones/a1/eliminacion');
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: 'POST' });
  });

  it('history() llama a GET {base}/{id}/historial', async () => {
    const fetchMock = mockFetch();
    const cliente = createEntityClient('/personas', 'id_persona');
    await cliente.history('p1');
    expect(fetchMock.mock.calls[0][0]).toContain('/personas/p1/historial');
  });
});
