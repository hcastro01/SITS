import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { HttpError } from '../../api/client';
import { FeedbackProvider } from '../../components/FeedbackProvider';
import { HierarchicalDestinationPicker, destinationPaths } from './HierarchicalDestinationPicker';

const api = vi.hoisted(() => ({ listDestinationTree: vi.fn(), listFormDestinations: vi.fn(), syncFormDestinations: vi.fn() }));
vi.mock('../../api/formBuilder', async () => ({ ...await vi.importActual<typeof import('../../api/formBuilder')>('../../api/formBuilder'), ...api }));

const tree = [{ id_destino: 'root', codigo: 'TRABAJO_SOCIAL', nombre: 'Trabajo Social', nivel: 'MACROPROCESO' as const, padre_id_destino: null, activo: true, orden: 1, hijos: [{ id_destino: 'production', codigo: 'PRODUCCION', nombre: 'Producción', nivel: 'PROCESO' as const, padre_id_destino: 'root', activo: true, orden: 2, hijos: [{ id_destino: 'rounds', codigo: 'RECORRIDOS', nombre: 'Recorridos', nivel: 'SUBPROCESO' as const, padre_id_destino: 'production', activo: true, orden: 3, hijos: [] }, { id_destino: 'news', codigo: 'NOVEDADES_PLANTA', nombre: 'Novedades de planta', nivel: 'SUBPROCESO' as const, padre_id_destino: 'production', activo: true, orden: 4, hijos: [] }] }] }];
function assignment(id: string) { return { id_asignacion: `a-${id}`, id_formulario: 'f1', id_destino_catalogo: id, activo: true, eliminado: false, version: 1, destino: tree[0].hijos[0].hijos.find((item) => item.id_destino === id)! }; }
function renderPicker(canEdit = true) { return render(<FeedbackProvider><HierarchicalDestinationPicker formId="f1" canEdit={canEdit} /></FeedbackProvider>); }

describe('HierarchicalDestinationPicker', () => {
  beforeEach(() => { vi.clearAllMocks(); api.listDestinationTree.mockResolvedValue(tree); api.listFormDestinations.mockResolvedValue([assignment('rounds')]); });
  it('carga el árbol desde API', async () => { renderPicker(); expect(await screen.findByText('Trabajo Social')).toBeInTheDocument(); expect(api.listDestinationTree).toHaveBeenCalledOnce(); });
  it('muestra la jerarquía legible', async () => { renderPicker(); expect(await screen.findByText('Producción')).toBeInTheDocument(); expect(screen.getByText('Recorridos')).toBeInTheDocument(); });
  it('carga destinos actuales', async () => { renderPicker(); expect(await screen.findByLabelText('Destino Recorridos')).toBeChecked(); });
  it('permite seleccionar un destino', async () => { renderPicker(); const user = userEvent.setup(); await user.click(await screen.findByLabelText('Destino Novedades de planta')); expect(screen.getByLabelText('Destino Novedades de planta')).toBeChecked(); });
  it('permite múltiples destinos', async () => { renderPicker(); const user = userEvent.setup(); await user.click(await screen.findByLabelText('Destino Novedades de planta')); expect(screen.getByLabelText('Destino Recorridos')).toBeChecked(); expect(screen.getByLabelText('Destino Novedades de planta')).toBeChecked(); });
  it('retira un destino sin eliminar respuestas', async () => { renderPicker(); const user = userEvent.setup(); await user.click(await screen.findByLabelText('Destino Recorridos')); expect(screen.getByLabelText('Destino Recorridos')).not.toBeChecked(); });
  it('sincroniza IDs reales al guardar', async () => { api.syncFormDestinations.mockResolvedValue([assignment('rounds'), assignment('news')]); renderPicker(); const user = userEvent.setup(); await user.click(await screen.findByLabelText('Destino Novedades de planta')); await user.click(screen.getByRole('button', { name: 'Guardar destinos' })); await waitFor(() => expect(api.syncFormDestinations).toHaveBeenCalledWith('f1', ['rounds', 'news'])); });
  it('evita doble submit mientras guarda', async () => { let done!: (value: unknown) => void; api.syncFormDestinations.mockReturnValue(new Promise((resolve) => { done = resolve; })); renderPicker(); const user = userEvent.setup(); await user.click(await screen.findByRole('button', { name: 'Guardar destinos' })); await user.click(screen.getByRole('button', { name: 'Guardando destinos…' })); expect(api.syncFormDestinations).toHaveBeenCalledOnce(); done([]); });
  it('muestra loading', () => { api.listDestinationTree.mockReturnValue(new Promise(() => undefined)); renderPicker(); expect(screen.getByText('Cargando destinos jerárquicos…')).toBeInTheDocument(); });
  it('muestra empty state', async () => { api.listDestinationTree.mockResolvedValue([]); api.listFormDestinations.mockResolvedValue([]); renderPicker(); expect(await screen.findByText('No hay destinos activos disponibles.')).toBeInTheDocument(); });
  it('muestra errores API', async () => { api.listDestinationTree.mockRejectedValue(new HttpError(500, { ok: false, code: 'ERROR', message: 'Error API.', correlationId: '' })); renderPicker(); expect(await screen.findByRole('alert')).toHaveTextContent('Error API.'); });
  it('muestra 401', async () => { api.listDestinationTree.mockRejectedValue(new HttpError(401, { ok: false, code: 'SESSION_REQUIRED', message: 'Inicie sesión.', correlationId: '' })); renderPicker(); expect(await screen.findByRole('alert')).toHaveTextContent('Inicie sesión.'); });
  it('muestra 403', async () => { api.listDestinationTree.mockRejectedValue(new HttpError(403, { ok: false, code: 'FORBIDDEN', message: 'Sin permiso.', correlationId: '' })); renderPicker(); expect(await screen.findByRole('alert')).toHaveTextContent('Sin permiso.'); });
  it('bloquea cambios sin permiso de edición', async () => { renderPicker(false); expect(await screen.findByLabelText('Destino Recorridos')).toBeDisabled(); expect(screen.getByText('No tiene permiso para modificar asignaciones de destinos.')).toBeInTheDocument(); });
  it('construye rutas para mostrar en repositorio', () => { expect(destinationPaths(tree).get('rounds')).toBe('Trabajo Social / Producción / Recorridos'); });
});
