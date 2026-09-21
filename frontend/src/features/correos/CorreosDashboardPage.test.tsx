import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { FeedbackProvider } from '../../components/FeedbackProvider';
import { HttpError } from '../../api/client';
import * as api from '../../api/correos';
import { CorreosDashboardPage } from './CorreosDashboardPage';

vi.mock('../../api/correos');
vi.mock('../../app/AuthContext', () => ({
  useAuth: () => ({ usuario: { id_usuario: 'admin', permisos: { CORREOS: { create: true, read: true, edit: true, sensitive: true }, IMPORTACION: { create: true, read: true } } } }),
}));
vi.mock('../../api/auth', () => ({ canAccess: () => true }));

const lot = {
  id_lote: 'lote-analizado', nombre_archivo: 'correos.xlsx', estado: 'ANALIZADO', origen: 'XLSX', total_filas: 4,
  filas_procesadas: 4, filas_clasificadas: 2, filas_revision: 1, filas_importadas: 0, filas_duplicadas: 0,
  filas_omitidas: 0, filas_error: 1, duracion_ms: 120, fecha_creacion: '2026-09-21T10:00:00-05:00', version: 1,
};

const correo = {
  id_correo: 'correo-qa', id_externo_correo: 'message-qa', asunto: 'Correo QA', remitente: 'qa@example.test',
  destinatarios: 'social@example.test', cc: null, fecha_recibido: '2026-09-21T10:00:00-05:00', importancia: null,
  tiene_adjuntos: false, leido: false, categoria_macro: 'CASOS_TALENTO_HUMANO', categoria_nombre: 'Casos',
  estado_categoria: 'VALIDA' as const, regla_disparadora: null, estado_clasificacion: 'CLASIFICADO' as const,
  estado_requerimiento: 'PENDIENTE' as const, responsable_seguimiento: null, origen: 'N8N',
  fecha_creacion: null, fecha_actualizacion: null, version: 1,
};

function renderPage() { return render(<FeedbackProvider><CorreosDashboardPage /></FeedbackProvider>); }

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.obtenerResumenCorreos).mockResolvedValue({ total: 0, pendientes: 0, en_seguimiento: 0, sin_clasificar: 0, por_categoria: [], por_origen: [], principales_remitentes: [] });
  vi.mocked(api.listarCorreos).mockResolvedValue({ items: [], total: 0, limite: 50, offset: 0 });
  vi.mocked(api.obtenerHistorialImportacionesCorreos).mockResolvedValue({ items: [lot] });
  vi.mocked(api.obtenerErroresImportacionCorreos).mockResolvedValue({ items: [{ fila: 8, message_id: 'mail-duplicado', codigo: 'DUPLICATE_IN_FILE', detalle: 'MessageId repetido dentro del XLSX.' }] });
  vi.mocked(api.confirmarImportacionCorreos).mockResolvedValue({ lote: { ...lot, estado: 'CONFIRMADO', filas_importadas: 2 }, filas_seleccionadas: 2, filas_importadas: 2, filas_duplicadas: 0 });
  vi.mocked(api.exportarCorreos).mockResolvedValue({ blob: new Blob(['xlsx']), filename: 'correos.xlsx' });
  Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: vi.fn(() => 'blob:correos') });
  Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: vi.fn() });
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);
});

afterEach(() => vi.restoreAllMocks());

describe('CorreosDashboardPage', () => {
  it('muestra las incidencias persistidas de un lote histórico', async () => {
    renderPage();
    expect(await screen.findByText('correos.xlsx')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Ver errores' }));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText('DUPLICATE_IN_FILE')).toBeInTheDocument();
    expect(within(dialog).getByText('mail-duplicado')).toBeInTheDocument();
    expect(api.obtenerErroresImportacionCorreos).toHaveBeenCalledWith('lote-analizado');
  });

  it('retoma un lote analizado y confirma sólo los clasificados', async () => {
    renderPage();
    await screen.findByText('correos.xlsx');
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar lote' }));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText(/1 correos sin categoría válida/)).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole('button', { name: 'Solo clasificados' }));
    await waitFor(() => expect(api.confirmarImportacionCorreos).toHaveBeenCalledWith('lote-analizado', false));
  });

  it('presenta análisis, filtros y la tabla vacía sin exponer cuerpos', async () => {
    vi.mocked(api.analizarCorreos).mockResolvedValue({ lote: { ...lot, filas_revision: 0, filas_error: 0 }, ultimos_100: [] });
    renderPage();
    await userEvent.upload(screen.getByLabelText('Seleccionar archivo XLSX de correos'), new File(['xlsx'], 'carga.xlsx'));
    await userEvent.click(screen.getByRole('button', { name: 'Analizar archivo' }));
    expect(await screen.findByText('Vista previa')).toBeInTheDocument();
    expect(screen.getByLabelText('Buscar correos')).toBeInTheDocument();
    expect(screen.getByText('No hay correos para estos filtros.')).toBeInTheDocument();
  });

  it('envía filtros operativos combinables y orden al servidor', async () => {
    renderPage();
    await screen.findByText('correos.xlsx');
    await userEvent.type(screen.getByLabelText('Filtrar por asunto'), 'Permiso');
    await userEvent.type(screen.getByLabelText('Filtrar por remitente'), 'ana@example.test');
    await userEvent.type(screen.getByLabelText('Filtrar por MessageId'), 'message-1');
    await userEvent.selectOptions(screen.getByLabelText('Filtrar por adjuntos'), 'true');
    await userEvent.selectOptions(screen.getByLabelText('Ordenar correos'), 'asunto_asc');
    await waitFor(() => {
      const params = vi.mocked(api.listarCorreos).mock.calls.at(-1)?.[0];
      expect(params?.get('asunto')).toBe('Permiso');
      expect(params?.get('remitente')).toBe('ana@example.test');
      expect(params?.get('message_id')).toBe('message-1');
      expect(params?.get('tiene_adjuntos')).toBe('true');
      expect(params?.get('orden')).toBe('asunto_asc');
    });
  });

  it('abre la descarga con resultados filtrados por defecto y deja el contenido sensible sin seleccionar', async () => {
    renderPage();
    await screen.findByText('correos.xlsx');
    await userEvent.type(screen.getByLabelText('Filtrar por asunto'), 'Permiso');
    await userEvent.click(screen.getByRole('button', { name: 'Descargar Excel' }));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByLabelText('Descargar resultados filtrados')).toBeChecked();
    expect(within(dialog).getByLabelText('Incluir cuerpo completo del correo')).not.toBeChecked();
    expect(within(dialog).getByLabelText('Incluir historial de seguimientos')).not.toBeChecked();
    expect(within(dialog).getByText(/cantidad final se confirma/)).toBeInTheDocument();
  });

  it('solicita el XLSX filtrado, conserva el nombre y libera el blob tras iniciar la descarga', async () => {
    renderPage();
    await screen.findByText('correos.xlsx');
    await userEvent.type(screen.getByLabelText('Filtrar por asunto'), 'Permiso');
    await userEvent.click(screen.getByRole('button', { name: 'Descargar Excel' }));
    const dialog = await screen.findByRole('dialog');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Descargar Excel' }));
    await waitFor(() => expect(api.exportarCorreos).toHaveBeenCalledWith({
      alcance: 'filtered', filtros: { asunto: 'Permiso' }, incluir_cuerpo: false, incluir_seguimientos: false,
    }));
    expect(URL.createObjectURL).toHaveBeenCalledWith(expect.any(Blob));
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:correos');
    expect(within(dialog).getByText(/la descarga se inició/i)).toBeInTheDocument();
  });

  it('traduce un 405 de un servidor desactualizado a una acción comprensible', async () => {
    vi.mocked(api.exportarCorreos).mockRejectedValue(new HttpError(405, {
      ok: false, code: 'HTTP_405', message: 'Method Not Allowed', correlationId: 'qa-405',
    }));
    renderPage();
    await screen.findByText('correos.xlsx');
    await userEvent.click(screen.getByRole('button', { name: 'Descargar Excel' }));
    const dialog = await screen.findByRole('dialog');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Descargar Excel' }));
    expect(await within(dialog).findByText(/actualice el backend/i)).toBeInTheDocument();
    expect(within(dialog).queryByText('Method Not Allowed')).not.toBeInTheDocument();
  });

  it('mantiene el éxito del seguimiento después de reiniciar su formulario', async () => {
    vi.mocked(api.listarCorreos).mockResolvedValue({ items: [correo], total: 1, limite: 50, offset: 0 });
    vi.mocked(api.obtenerCorreo).mockResolvedValue({ correo: { ...correo, cuerpo: 'Contenido QA' }, seguimientos: [] });
    vi.mocked(api.crearSeguimientoCorreo).mockResolvedValue({
      correo: { ...correo, version: 2 },
      seguimiento: { id_seguimiento: 'seguimiento-qa', fecha_seguimiento: '2026-09-21T11:00:00-05:00', detalle_seguimiento: 'Seguimiento QA', seguimiento_por: 'QA', estado_requerimiento: 'PENDIENTE' },
    });
    renderPage();
    await userEvent.click(await screen.findByRole('button', { name: 'Ver detalle' }));
    const dialog = await screen.findByRole('dialog');
    await userEvent.type(within(dialog).getByLabelText('Detalle del seguimiento'), 'Seguimiento QA');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Registrar seguimiento' }));
    await waitFor(() => expect(api.crearSeguimientoCorreo).toHaveBeenCalledWith('correo-qa', expect.objectContaining({ detalle_seguimiento: 'Seguimiento QA', expected_version: 1 })));
    expect(within(dialog).queryByText('No fue posible guardar el seguimiento.')).not.toBeInTheDocument();
    expect(within(dialog).getByText('Seguimiento QA')).toBeInTheDocument();
  });
});
