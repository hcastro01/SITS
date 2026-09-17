import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { HttpError } from '../../api/client';
import { fileValidationError, MAX_DOCUMENT_BYTES, DocumentosPanel } from './DocumentosPanel';

const api = vi.hoisted(() => ({
  listarDocumentos: vi.fn(), subirDocumento: vi.fn(), eliminarDocumento: vi.fn(), descargarDocumento: vi.fn(),
}));
vi.mock('../../api/documentos', () => api);
vi.mock('../../api/riesgosTrabajo', () => ({}));
vi.mock('../../app/AuthContext', () => ({ useAuth: () => ({ usuario: { permisos: { CASOS: { edit: true }, DOCUMENTOS: { create: true, delete: true } } } }) }));
vi.mock('../../components/FeedbackProvider', () => ({ useFeedback: () => ({ notify: vi.fn(), confirm: vi.fn().mockResolvedValue(true) }) }));

const pdf = { id_archivo: 'd1', tipo_registro: 'CASOS', id_registro: 'c1', nombre_archivo: 'evidencia.pdf', mime_type: 'application/pdf', extension: 'pdf', tamano_bytes: 20, tamano_comprimido_bytes: 15, sha256: 'hash', categoria_documento: 'EVIDENCIA', version: 1, activo: true, eliminado: false, fecha_creacion: '2026-09-16T10:00:00', creado_por: 'ana@example.com' };
const image = { ...pdf, id_archivo: 'd2', nombre_archivo: 'foto.webp', mime_type: 'image/webp', extension: 'webp' };

describe('DocumentosPanel BLOB', () => {
  const createObjectURL = vi.fn();
  const revokeObjectURL = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    api.listarDocumentos.mockResolvedValue([pdf]);
    api.descargarDocumento.mockResolvedValue({ blob: new Blob(['pdf'], { type: 'application/pdf' }), filename: 'nombre-backend.pdf' });
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: createObjectURL });
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: revokeObjectURL });
    createObjectURL.mockReturnValue('blob:preview');
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);
  });

  afterEach(() => { vi.restoreAllMocks(); });

  async function renderPanel() {
    render(<DocumentosPanel tipoRegistro="CASOS" idRegistro="c1" />);
    await screen.findByText('evidencia.pdf');
  }

  it('muestra exclusivamente metadata y estados de lista vacía/error', async () => {
    await renderPanel();
    expect(screen.getByText('application/pdf')).toBeInTheDocument();
    expect(screen.queryByText('contenido_comprimido')).not.toBeInTheDocument();
    api.listarDocumentos.mockResolvedValue([]);
    render(<DocumentosPanel tipoRegistro="CASOS" idRegistro="c2" />);
    expect(await screen.findByText('Sin documentos adjuntos.')).toBeInTheDocument();
    api.listarDocumentos.mockRejectedValue(new HttpError(403, { ok: false, code: 'FORBIDDEN', message: 'Sin permiso.', correlationId: '' }));
    render(<DocumentosPanel tipoRegistro="CASOS" idRegistro="c3" />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Sin permiso.');
  });

  it('valida formato, MIME, tamaño y máximo documental antes del envío', () => {
    expect(fileValidationError(new File(['x'], 'activo.svg', { type: 'image/svg+xml' }), 0)).toContain('Solo se permiten');
    expect(fileValidationError(new File(['x'], 'foto.jpg', { type: 'application/pdf' }), 0)).toContain('no coincide');
    expect(fileValidationError(new File([new Uint8Array(MAX_DOCUMENT_BYTES + 1)], 'foto.png', { type: 'image/png' }), 0)).toContain('supera el límite');
    expect(fileValidationError(new File(['x'], 'foto.png', { type: 'image/png' }), 10)).toContain('máximo de 10');
    expect(fileValidationError(new File(['x'], 'foto.webp', { type: 'image/webp' }), 0)).toBeNull();
  });

  it('descarga por Blob autenticado y revoca la URL temporal', async () => {
    const user = userEvent.setup(); createObjectURL.mockReturnValue('blob:download'); await renderPanel();
    await user.click(screen.getByRole('button', { name: 'Descargar' }));
    expect(api.descargarDocumento).toHaveBeenCalledWith('d1');
    await waitFor(() => expect(revokeObjectURL).toHaveBeenCalledWith('blob:download'));
  });

  it('abre previews PDF e imagen y revoca la URL al cerrar', async () => {
    const user = userEvent.setup(); await renderPanel();
    await user.click(screen.getByRole('button', { name: 'Vista previa' }));
    expect(await screen.findByTitle('Vista previa de evidencia.pdf')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Cerrar vista previa' }));
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:preview');

    api.listarDocumentos.mockResolvedValue([image]);
    render(<DocumentosPanel tipoRegistro="CASOS" idRegistro="c-image" />);
    await screen.findByText('foto.webp');
    await user.click(screen.getAllByRole('button', { name: 'Vista previa' }).at(-1)!);
    expect(await screen.findByAltText('Vista previa de foto.webp')).toBeInTheDocument();
  });
});
