import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { FeedbackProvider } from '../../components/FeedbackProvider';
import { HttpError } from '../../api/client';
import type { ContextualEntityClient } from '../../api/entities';
import { EntityListPage } from './EntityListPage';
import { beneficiosConfig, oficinaAtencionesConfig, prestamosConfig, segurosConfig, type EntityPageConfig } from './EntityConfig';

const { list, create, get, update, softDelete, restore, history } = vi.hoisted(() => ({ list: vi.fn(), create: vi.fn(), get: vi.fn(), update: vi.fn(), softDelete: vi.fn(), restore: vi.fn(), history: vi.fn() }));
vi.mock('../../app/AuthContext', () => ({ useAuth: () => ({ usuario: { permisos: { OFICINA: { create: true, read: true, edit: true, delete: true } } } }) }));
vi.mock('../../api/auth', () => ({ canAccess: (user: { permisos: Record<string, Record<string, boolean>> } | null, module: string, action: string) => Boolean(user?.permisos?.[module]?.[action]) }));
vi.mock('../formularios/SearchAutocompleteField', () => ({ SearchAutocompleteField: ({ onSelect }: { onSelect: (item: { id: string } | null, text: string) => void }) => <input aria-label="Persona" onChange={(event) => onSelect({ id: 'persona-1' }, event.target.value)} /> }));

const api = { idField: 'id_beneficio', basePath: '/oficina/beneficios', list, create, get, update, softDelete, restore, history } as unknown as ContextualEntityClient;
const config: EntityPageConfig = {
  titulo: 'Beneficios', tituloSingular: 'beneficio', rutaBase: '/trabajo-social/oficina/beneficios', api, tipoRegistro: 'BENEFICIOS', contextual: true, permissionModule: 'OFICINA', personaIdField: 'persona_id', integrations: false, maxListColumns: 9,
  filtros: [{ nombre: 'nombre', etiqueta: 'Persona o nombre' }, { nombre: 'cedula', etiqueta: 'Cédula' }, { nombre: 'fecha', etiqueta: 'Fecha', tipo: 'fecha' }, { nombre: 'tipo', etiqueta: 'Tipo de beneficio', tipo: 'select', opciones: ['TIA', 'FARMACIA'] }, { nombre: 'tipo_gestion', etiqueta: 'Tipo de gestión', tipo: 'select', opciones: ['ACTIVACION', 'BLOQUEO', 'ANULACION'] }],
  campos: [{ nombre: 'id_beneficio', etiqueta: 'ID', enFormulario: false }, { nombre: 'fecha', etiqueta: 'Fecha', tipo: 'fecha' }, { nombre: 'persona', etiqueta: 'Persona', enFormulario: false }, { nombre: 'cedula', etiqueta: 'Cédula', enFormulario: false }, { nombre: 'area_persona', etiqueta: 'Área actual', enFormulario: false }, { nombre: 'tipo_beneficio', etiqueta: 'Tipo de beneficio', tipo: 'select', opciones: ['TIA', 'FARMACIA'], requerido: true }, { nombre: 'tipo_gestion', etiqueta: 'Tipo de gestión', tipo: 'select', opciones: ['ACTIVACION', 'BLOQUEO', 'ANULACION'], requerido: true }, { nombre: 'responsable', etiqueta: 'Responsable' }, { nombre: 'registrado_por', etiqueta: 'Registrado por', enFormulario: false }],
};
const record = { id_beneficio: 'beneficio-1', fecha: '2026-09-16', persona: 'Ana Pérez', cedula: '0012345678', area_persona: 'Oficina', tipo_beneficio: 'TIA', tipo_gestion: 'ACTIVACION', responsable: 'Rosa', registrado_por: 'Autor histórico', version: 1, activo: true, eliminado: false };
const page = () => render(<MemoryRouter><FeedbackProvider><EntityListPage config={config} /></FeedbackProvider></MemoryRouter>);

beforeEach(() => { vi.clearAllMocks(); list.mockResolvedValue({ items: [record], total: 26, limite: 25, offset: 0 }); create.mockResolvedValue(record); });

describe('frontend contextual de Oficina', () => {
  it('configura exclusivamente las cuatro rutas Oficina y sus contratos aprobados', () => {
    expect([beneficiosConfig.api.basePath, oficinaAtencionesConfig.api.basePath, prestamosConfig.api.basePath, segurosConfig.api.basePath]).toEqual(['/oficina/beneficios', '/oficina/atenciones', '/oficina/prestamos', '/oficina/seguro']);
    expect(beneficiosConfig.campos.find((campo) => campo.nombre === 'tipo_beneficio')?.opciones).toEqual(['TIA', 'FARMACIA']);
    expect(beneficiosConfig.campos.find((campo) => campo.nombre === 'tipo_gestion')?.opciones).toEqual(['ACTIVACION', 'BLOQUEO', 'ANULACION']);
    expect(prestamosConfig.campos.find((campo) => campo.nombre === 'tipo')?.opciones).toEqual(['PRESTAMO', 'ANTICIPO']);
    expect(segurosConfig.campos.find((campo) => campo.nombre === 'tipo_gestion')?.opciones).toEqual(['AFILIACION', 'ENROLAMIENTO', 'COBERTURA', 'REEMBOLSO', 'PRIMA', 'DEPENDIENTE']);
    expect(prestamosConfig.campos.map((campo) => campo.nombre)).not.toEqual(expect.arrayContaining(['monto', 'interes', 'cuotas', 'plazo', 'saldo', 'amortizacion']));
    expect(segurosConfig.campos.map((campo) => campo.nombre)).not.toEqual(expect.arrayContaining(['poliza', 'deducible', 'copago', 'dependiente_nombre']));
    expect([beneficiosConfig, oficinaAtencionesConfig, prestamosConfig, segurosConfig].every((item) => item.integrations === false)).toBe(true);
  });

  it('usa el cliente Oficina, conserva trazabilidad, filtros reales y paginación', async () => {
    page(); expect(await screen.findByText('Autor histórico')).toBeInTheDocument(); expect(screen.getByRole('link', { name: 'Ver' })).toHaveAttribute('href', '/trabajo-social/oficina/beneficios/beneficio-1');
    await userEvent.type(screen.getByLabelText('Filtrar por nombre'), 'Ana'); await userEvent.selectOptions(screen.getByLabelText('Filtrar por tipo de beneficio'), 'TIA'); await userEvent.selectOptions(screen.getByLabelText('Filtrar por tipo de gestión'), 'ACTIVACION'); await userEvent.click(screen.getByRole('button', { name: 'Aplicar filtros' }));
    await waitFor(() => expect(list.mock.calls.at(-1)![0].get('nombre')).toBe('Ana')); expect(list.mock.calls.at(-1)![0].get('tipo')).toBe('TIA'); expect(list.mock.calls.at(-1)![0].get('tipo_gestion')).toBe('ACTIVACION');
    await userEvent.click(screen.getByRole('button', { name: 'Siguiente' })); await waitFor(() => expect(list.mock.calls.at(-1)![0].get('offset')).toBe('25'));
  });

  it('ofrece sólo valores aprobados y permite guardar sin Persona o limpiarla', async () => {
    page(); await screen.findByText('Ana Pérez'); await userEvent.click(screen.getByRole('button', { name: 'Nuevo beneficio' })); const dialog = screen.getByRole('dialog');
    expect(within(dialog).getByRole('option', { name: 'TIA' })).toBeInTheDocument(); expect(within(dialog).queryByRole('option', { name: 'OTRO' })).toBeNull(); expect(within(dialog).queryByLabelText(/monto|contexto_operativo/i)).toBeNull();
    await userEvent.selectOptions(within(dialog).getByLabelText('Tipo de beneficio'), 'FARMACIA'); await userEvent.selectOptions(within(dialog).getByLabelText('Tipo de gestión'), 'ANULACION'); await userEvent.click(within(dialog).getByRole('button', { name: /crear beneficio/i }));
    await waitFor(() => expect(create).toHaveBeenCalledWith(expect.objectContaining({ persona_id: null, tipo_beneficio: 'FARMACIA', tipo_gestion: 'ANULACION' })));
  });

  it('distingue carga, vacío y errores de sesión o permiso', async () => {
    let resolve!: (page: { items: []; total: number; limite: number; offset: number }) => void; list.mockImplementationOnce(() => new Promise((done) => { resolve = done; })); page(); expect(screen.getByText('Cargando…')).toBeInTheDocument(); resolve({ items: [], total: 0, limite: 25, offset: 0 }); expect(await screen.findByText('No hay registros todavía.')).toBeInTheDocument();
    list.mockRejectedValueOnce(new HttpError(401, { ok: false, code: 'SESSION_REQUIRED', message: 'Inicie sesión.', correlationId: '' })); await userEvent.click(screen.getByRole('button', { name: 'Aplicar filtros' })); expect(await screen.findByText('Inicie sesión.')).toBeInTheDocument();
    list.mockRejectedValueOnce(new HttpError(403, { ok: false, code: 'FORBIDDEN', message: 'Sin permiso.', correlationId: '' })); await userEvent.click(screen.getByRole('button', { name: 'Aplicar filtros' })); expect(await screen.findByText('Sin permiso.')).toBeInTheDocument();
  });
});
