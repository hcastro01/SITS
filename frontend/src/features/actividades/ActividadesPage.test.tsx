import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ActividadesPage } from './ActividadesPage';

const { listActivities, activityOptions, createActivity, updateActivity, archiveActivity } = vi.hoisted(() => ({ listActivities: vi.fn(), activityOptions: vi.fn(), createActivity: vi.fn(), updateActivity: vi.fn(), archiveActivity: vi.fn() }));
vi.mock('../../api/actividades', () => ({ listActivities, activityOptions, createActivity, updateActivity, archiveActivity }));
vi.mock('../../app/AuthContext', () => ({
  useAuth: () => ({ usuario: { id_usuario: 'u1', permisos: { ACTIVIDADES: { create: true, edit: true, delete: true } } } }),
}));
vi.mock('../../api/auth', () => ({ canAccess: () => true }));
vi.mock('../../components/FeedbackProvider', () => ({ useFeedback: () => ({ notify: vi.fn(), confirm: vi.fn().mockResolvedValue(false) }) }));

const row = { id_actividad: 'a1', nombre: 'Actividad vencida', descripcion: 'Descripción', responsable_id: 'u2', responsable: 'Juan', tipo_fecha: 'LIMITE', fecha_objetivo: '2026-09-14', estado: 'PENDIENTE', persona_id: null, persona: null, cedula: null, area: null, registrado_por: 'Ana', fecha_creacion: null, fecha_finalizacion: null, vencida: true, version: 1 };
function renderPage(register = false) { return render(<MemoryRouter><ActividadesPage register={register} /></MemoryRouter>); }
beforeEach(() => { vi.clearAllMocks(); listActivities.mockResolvedValue({ items: [row], total: 26, limite: 25, offset: 0 }); activityOptions.mockResolvedValue({ usuarios: [{ id: 'u2', nombre: 'Juan' }], personas: [{ id: 'p1', nombre: 'Persona', cedula: '001', area: 'Área' }] }); });

describe('Actividades', () => {
  it('renderiza tabla, vencimiento y paginación real', async () => { renderPage(); expect(await screen.findByText('Actividad vencida')).toBeInTheDocument(); expect(screen.getByText(/Vencida/)).toBeInTheDocument(); expect(screen.getByText(/Página 1 de 2/)).toBeInTheDocument(); await userEvent.click(screen.getByText('Siguiente')); await waitFor(() => expect(listActivities.mock.calls.at(-1)![0].get('offset')).toBe('25')); });
  it('envía filtros combinados y Mis actividades al backend', async () => { renderPage(); await screen.findByText('Actividad vencida'); await userEvent.selectOptions(screen.getByLabelText('Responsable'), 'u2'); await userEvent.selectOptions(screen.getByLabelText('Estado'), 'PENDIENTE'); await userEvent.selectOptions(screen.getByLabelText('Tipo de fecha'), 'LIMITE'); await userEvent.type(screen.getByLabelText('Buscar actividades'), 'vencida'); await userEvent.click(screen.getByLabelText(/Mis actividades/)); await waitFor(() => expect(listActivities.mock.calls.at(-1)![0].get('mis_actividades')).toBe('true')); expect(listActivities.mock.calls.at(-1)![0].get('responsable_id')).toBe('u2'); expect(listActivities.mock.calls.at(-1)![0].get('estado')).toBe('PENDIENTE'); });
  it('renderiza registro con responsable obligatorio y persona opcional', async () => { renderPage(true); expect(screen.getByText('Registrar actividad')).toBeInTheDocument(); expect(screen.getByLabelText(/Responsable/)).toBeRequired(); expect(screen.getByLabelText(/Persona relacionada/)).toHaveValue(''); await userEvent.type(screen.getByLabelText(/Nombre de la actividad/), 'Nueva'); await userEvent.selectOptions(screen.getByLabelText(/Responsable/), 'u2'); await userEvent.type(screen.getByLabelText(/Breve descripción/), 'Texto'); await userEvent.type(screen.getByLabelText(/Fecha objetivo/), '2026-09-20'); createActivity.mockResolvedValue(row); await userEvent.click(screen.getByText('Guardar actividad')); await waitFor(() => expect(createActivity).toHaveBeenCalled()); });
  it('completa una actividad mediante cambio de estado', async () => { renderPage(); await screen.findByText('Actividad vencida'); updateActivity.mockResolvedValue({ ...row, estado: 'COMPLETADA' }); await userEvent.click(screen.getByText('Completar')); await waitFor(() => expect(updateActivity).toHaveBeenCalledWith('a1', expect.objectContaining({ estado: 'COMPLETADA', expected_version: 1 }))); });
});
