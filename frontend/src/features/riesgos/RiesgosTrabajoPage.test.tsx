import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { FeedbackProvider } from '../../components/FeedbackProvider';
import { HttpError } from '../../api/client';
import { RiesgosTrabajoPage } from './RiesgosTrabajoPage';

const { listarRiesgos, obtenerRiesgo, crearRiesgo, actualizarRiesgo, cerrarRiesgo } = vi.hoisted(() => ({ listarRiesgos: vi.fn(), obtenerRiesgo: vi.fn(), crearRiesgo: vi.fn(), actualizarRiesgo: vi.fn(), cerrarRiesgo: vi.fn() }));
vi.mock('../../api/riesgosTrabajo', () => ({ listarRiesgos, obtenerRiesgo, crearRiesgo, actualizarRiesgo, cerrarRiesgo }));
vi.mock('../../app/AuthContext', () => ({ useAuth: () => ({ usuario: { permisos: { RIESGOS_TRABAJO: { create: true, edit: true, read: true } } } }) }));
vi.mock('../../api/auth', async () => ({ canAccess: (user: { permisos?: Record<string, Record<string, boolean>> } | null, module: string, action: string) => Boolean(user?.permisos?.[module]?.[action]) }));
vi.mock('../formularios/SearchAutocompleteField', () => ({ SearchAutocompleteField: ({ ariaLabel, onSelect }: { ariaLabel: string; onSelect: (result: { id: string; label: string; data: Record<string, string> }, text: string) => void }) => <input aria-label={ariaLabel} onChange={(event) => onSelect({ id: ariaLabel === 'Persona' ? 'persona-1' : 'responsable-1', label: event.target.value, data: { nombre: event.target.value, cedula: '0012345678', area: 'Operaciones' } }, event.target.value)} /> }));

const riesgo = { id_caso: 'r-1', codigo_caso: 'CAS-2026-1', tipo_caso: 'RIESGOS_TRABAJO' as const, persona_id: 'persona-1', persona: 'Ana Pérez', cedula: '0012345678', area: 'Operaciones', fecha_apertura: '2026-09-15', responsable: 'Juan Responsable', estado_caso: 'ABIERTO' as const, prioridad: 'ALTA', resultado: 'Superficie resbaladiza', resumen: 'Superficie resbaladiza', ultimo_seguimiento: null, fecha_creacion: '2026-09-15T10:00:00', fecha_actualizacion: '2026-09-15T11:00:00', fecha_cierre: null, motivo_cierre: null, registrado_por: 'Administradora', version: 3 };
const renderPage = () => render(<MemoryRouter><FeedbackProvider><RiesgosTrabajoPage /></FeedbackProvider></MemoryRouter>);

beforeEach(() => { vi.clearAllMocks(); listarRiesgos.mockResolvedValue({ items: [riesgo], total: 26, limite: 25, offset: 0 }); obtenerRiesgo.mockResolvedValue(riesgo); });

describe('RiesgosTrabajoPage', () => {
  it('renderiza exclusivamente la tabla contextual, columnas y paginación', async () => {
    renderPage(); expect(await screen.findByText('CAS-2026-1')).toBeInTheDocument(); expect(screen.getByText('Ana Pérez')).toBeInTheDocument(); expect(screen.getByText('Ana Pérez').parentElement).toHaveTextContent('0012345678'); expect(screen.getByText('Ana Pérez').parentElement).toHaveTextContent('Operaciones'); expect(screen.getByText('Mostrando 1-25 de 26')).toBeInTheDocument(); await userEvent.click(screen.getByRole('button', { name: 'Siguiente' })); await waitFor(() => expect(listarRiesgos.mock.calls.at(-1)![0].get('offset')).toBe('25')); expect(listarRiesgos.mock.calls.at(-1)![0].get('tipo_caso')).toBeNull();
  });

  it('envía los filtros combinados al backend, conserva los filtros y los limpia', async () => {
    renderPage(); await screen.findByText('CAS-2026-1'); await userEvent.type(screen.getByLabelText('Filtrar por nombre'), 'Ana'); await userEvent.type(screen.getByLabelText('Filtrar por cédula'), '001'); await userEvent.type(screen.getByLabelText('Filtrar por área'), 'Operaciones'); await userEvent.selectOptions(screen.getByLabelText('Filtrar por estado'), 'EN_SEGUIMIENTO'); await userEvent.type(screen.getByLabelText('Filtrar por responsable'), 'Juan'); await userEvent.type(screen.getByLabelText('Fecha desde'), '2026-09-01'); await userEvent.type(screen.getByLabelText('Fecha hasta'), '2026-09-30'); await userEvent.click(screen.getByRole('button', { name: 'Aplicar filtros' })); await waitFor(() => expect(listarRiesgos.mock.calls.at(-1)![0].get('nombre')).toBe('Ana')); const query = listarRiesgos.mock.calls.at(-1)![0]; expect(query.get('cedula')).toBe('001'); expect(query.get('area')).toBe('Operaciones'); expect(query.get('estado')).toBe('EN_SEGUIMIENTO'); expect(query.get('responsable')).toBe('Juan'); expect(query.get('desde')).toBe('2026-09-01'); expect(query.get('hasta')).toBe('2026-09-30'); await userEvent.click(screen.getByRole('button', { name: 'Siguiente' })); await waitFor(() => expect(listarRiesgos.mock.calls.at(-1)![0].get('nombre')).toBe('Ana')); await userEvent.click(screen.getByRole('button', { name: 'Limpiar filtros' })); await waitFor(() => expect(listarRiesgos.mock.calls.at(-1)![0].get('nombre')).toBeNull());
  });

  it('registra un Riesgo con Persona real, responsable seleccionado y sin tipo_caso', async () => {
    crearRiesgo.mockResolvedValue(riesgo); renderPage(); await screen.findByText('CAS-2026-1'); await userEvent.click(screen.getByRole('button', { name: 'Registrar Riesgo' })); const dialog = screen.getByRole('dialog'); await userEvent.type(within(dialog).getByLabelText('Persona'), 'Ana Pérez'); await userEvent.type(within(dialog).getByLabelText('Responsable'), 'Juan Responsable'); await userEvent.type(within(dialog).getByLabelText('Descripción / resumen *'), 'Riesgo informado'); expect(within(dialog).queryByLabelText(/tipo_caso/i)).toBeNull(); await userEvent.click(within(dialog).getByRole('button', { name: 'Registrar Riesgo' })); await waitFor(() => expect(crearRiesgo).toHaveBeenCalledWith(expect.objectContaining({ persona_id: 'persona-1', responsable: 'Juan Responsable', resultado: 'Riesgo informado' }))); expect(crearRiesgo.mock.calls[0][0]).not.toHaveProperty('tipo_caso');
  });

  it('navega al detalle integrado contextual', async () => {
    renderPage(); await screen.findByText('CAS-2026-1'); expect(screen.getByRole('link', { name: 'Ver detalle' })).toHaveAttribute('href', '/trabajo-social/departamento-medico/riesgos/r-1');
  });

  it('edita solo los campos autorizados y conserva la versión', async () => {
    actualizarRiesgo.mockResolvedValue({ ...riesgo, estado_caso: 'EN_SEGUIMIENTO' }); renderPage(); await screen.findByText('CAS-2026-1'); await userEvent.click(screen.getByRole('button', { name: 'Editar' })); const dialog = screen.getByRole('dialog'); expect(within(dialog).queryByLabelText(/tipo_caso/i)).toBeNull(); await userEvent.selectOptions(within(dialog).getByLabelText('Estado'), 'EN_SEGUIMIENTO'); await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar cambios' })); await waitFor(() => expect(actualizarRiesgo).toHaveBeenCalledWith('r-1', expect.objectContaining({ expected_version: 3, estado_caso: 'EN_SEGUIMIENTO' })));
  });

  it('cierra mediante el contrato real y evita doble submit', async () => {
    cerrarRiesgo.mockImplementation(() => new Promise<void>(() => undefined)); renderPage(); await screen.findByText('CAS-2026-1'); await userEvent.click(screen.getByRole('button', { name: 'Cerrar' })); const dialog = screen.getByRole('dialog'); await userEvent.type(within(dialog).getByLabelText('Motivo de cierre *'), 'Control aplicado'); await userEvent.click(within(dialog).getByRole('button', { name: 'Cerrar Riesgo' })); await waitFor(() => expect(cerrarRiesgo).toHaveBeenCalledWith('r-1', expect.objectContaining({ expected_version: 3, motivo_cierre: 'Control aplicado' }))); expect(within(dialog).getByText('Cerrando…')).toBeDisabled();
  });

  it('representa loading, vacío, 401, 403 y error del API', async () => {
    let resolve!: (value: { items: []; total: number; limite: number; offset: number }) => void; listarRiesgos.mockImplementationOnce(() => new Promise((done) => { resolve = done; })); renderPage(); expect(screen.getByText('Cargando Riesgos de trabajo…')).toBeInTheDocument(); resolve({ items: [], total: 0, limite: 25, offset: 0 }); expect(await screen.findByText(/No existen Riesgos/)).toBeInTheDocument(); listarRiesgos.mockRejectedValueOnce(new HttpError(401, { ok: false, code: 'SESSION_REQUIRED', message: 'Inicie sesión.', correlationId: '' })); await userEvent.click(screen.getByRole('button', { name: 'Aplicar filtros' })); expect(await screen.findByText('Inicie sesión.')).toBeInTheDocument(); listarRiesgos.mockRejectedValueOnce(new HttpError(403, { ok: false, code: 'FORBIDDEN', message: 'Sin permiso.', correlationId: '' })); await userEvent.click(screen.getByRole('button', { name: 'Aplicar filtros' })); expect(await screen.findByText('Sin permiso.')).toBeInTheDocument();
  });
});
