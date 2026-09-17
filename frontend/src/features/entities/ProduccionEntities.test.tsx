import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { FeedbackProvider } from '../../components/FeedbackProvider';
import { HttpError } from '../../api/client';
import type { ContextualEntityClient } from '../../api/entities';
import { EntityListPage } from './EntityListPage';
import type { EntityPageConfig } from './EntityConfig';

const { list, create, get, update, softDelete, restore, history } = vi.hoisted(() => ({ list: vi.fn(), create: vi.fn(), get: vi.fn(), update: vi.fn(), softDelete: vi.fn(), restore: vi.fn(), history: vi.fn() }));
vi.mock('../../app/AuthContext', () => ({ useAuth: () => ({ usuario: { permisos: { PRODUCCION: { create: true, read: true, edit: true } } } }) }));
vi.mock('../../api/auth', () => ({ canAccess: (user: { permisos: Record<string, Record<string, boolean>> } | null, module: string, action: string) => Boolean(user?.permisos?.[module]?.[action]) }));
vi.mock('../formularios/SearchAutocompleteField', () => ({ SearchAutocompleteField: ({ onSelect }: { onSelect: (item: { id: string } | null, text: string) => void }) => <input aria-label="Persona" onChange={(event) => onSelect({ id: 'persona-1' }, event.target.value)} /> }));

const api = { idField: 'id_atencion', basePath: '/produccion/atenciones', list, create, get, update, softDelete, restore, history } as unknown as ContextualEntityClient;
const config: EntityPageConfig = { titulo: 'Atenciones de Producción', tituloSingular: 'atención de Producción', rutaBase: '/trabajo-social/produccion/atenciones', api, tipoRegistro: 'ATENCIONES', contextual: true, permissionModule: 'PRODUCCION', campos: [
  { nombre: 'id_atencion', etiqueta: 'ID', enFormulario: false }, { nombre: 'fecha', etiqueta: 'Fecha' }, { nombre: 'persona', etiqueta: 'Persona', enFormulario: false }, { nombre: 'cedula', etiqueta: 'Cédula', enFormulario: false }, { nombre: 'area_persona', etiqueta: 'Área actual', enFormulario: false }, { nombre: 'motivo', etiqueta: 'Motivo' }, { nombre: 'responsable', etiqueta: 'Responsable' }, { nombre: 'registrado_por', etiqueta: 'Registrado por', enFormulario: false }, { nombre: 'estado', etiqueta: 'Estado' },
] };
const record = { id_atencion: 'a-produccion', fecha: '2026-09-15', persona: 'Ana Pérez', cedula: '0012345678', area_persona: 'Planta', motivo: 'Orientación', responsable: 'Juan', registrado_por: 'Autor histórico', estado: 'ABIERTO', version: 1, activo: true, eliminado: false };
const page = () => render(<MemoryRouter><FeedbackProvider><EntityListPage config={config} /></FeedbackProvider></MemoryRouter>);

beforeEach(() => { vi.clearAllMocks(); list.mockResolvedValue({ items: [record], total: 26, limite: 25, offset: 0 }); create.mockResolvedValue(record); });

describe('frontend contextual de Producción', () => {
  it('usa la ruta contextual, conserva trazabilidad y pagina sin incluir históricos ajenos', async () => {
    page(); expect(await screen.findByText('Ana Pérez')).toBeInTheDocument(); expect(screen.getByText('Autor histórico')).toBeInTheDocument(); expect(screen.getByRole('link', { name: 'Ver' })).toHaveAttribute('href', '/trabajo-social/produccion/atenciones/a-produccion'); expect(list.mock.calls[0][0].toString()).toContain('offset=0'); await userEvent.click(screen.getByRole('button', { name: 'Siguiente' })); await waitFor(() => expect(list.mock.calls.at(-1)![0].get('offset')).toBe('25'));
  });

  it('envía filtros reales, permite Persona opcional y no expone contexto editable', async () => {
    page(); await screen.findByText('Ana Pérez'); await userEvent.type(screen.getByLabelText('Filtrar por nombre'), 'Ana'); await userEvent.type(screen.getByLabelText('Filtrar por cédula'), '001'); await userEvent.click(screen.getByRole('button', { name: 'Aplicar filtros' })); await waitFor(() => expect(list.mock.calls.at(-1)![0].get('nombre')).toBe('Ana')); expect(list.mock.calls.at(-1)![0].get('cedula')).toBe('001'); await userEvent.click(screen.getByRole('button', { name: 'Nuevo atención de Producción' })); const dialog = screen.getByRole('dialog'); expect(within(dialog).queryByLabelText(/contexto_operativo/i)).toBeNull(); await userEvent.type(within(dialog).getByLabelText('Motivo'), 'Consulta'); await userEvent.click(within(dialog).getByRole('button', { name: /crear atención/i })); await waitFor(() => expect(create).toHaveBeenCalledWith(expect.not.objectContaining({ contexto_operativo: expect.anything(), id_persona: expect.anything() })));
  });

  it('distingue carga, vacío y errores 401/403', async () => {
    let resolve!: (page: { items: []; total: number; limite: number; offset: number }) => void; list.mockImplementationOnce(() => new Promise((done) => { resolve = done; })); page(); expect(screen.getByText('Cargando…')).toBeInTheDocument(); resolve({ items: [], total: 0, limite: 25, offset: 0 }); expect(await screen.findByText('No hay registros todavía.')).toBeInTheDocument(); list.mockRejectedValueOnce(new HttpError(401, { ok: false, code: 'SESSION_REQUIRED', message: 'Inicie sesión.', correlationId: '' })); await userEvent.click(screen.getByRole('button', { name: 'Aplicar filtros' })); expect(await screen.findByText('Inicie sesión.')).toBeInTheDocument(); list.mockRejectedValueOnce(new HttpError(403, { ok: false, code: 'FORBIDDEN', message: 'Sin permiso.', correlationId: '' })); await userEvent.click(screen.getByRole('button', { name: 'Aplicar filtros' })); expect(await screen.findByText('Sin permiso.')).toBeInTheDocument();
  });
});
