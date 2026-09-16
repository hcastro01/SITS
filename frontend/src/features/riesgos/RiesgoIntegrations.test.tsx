import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { HttpError } from '../../api/client';
import { DocumentosPanel } from '../documentos/DocumentosPanel';
import { ContextFormsPanel } from '../formularios/ContextFormsPanel';
import { DynamicResponsePage } from '../formularios/DynamicResponsePage';

const riesgosApi = vi.hoisted(() => ({ listarFormulariosRiesgo: vi.fn(), listarDocumentosRiesgo: vi.fn(), responderFormularioRiesgo: vi.fn() }));
const formApi = vi.hoisted(() => ({ getFormDefinition: vi.fn(), getFormResponse: vi.fn(), listDestinationTree: vi.fn() }));
vi.mock('../../api/riesgosTrabajo', async () => ({ ...await vi.importActual<typeof import('../../api/riesgosTrabajo')>('../../api/riesgosTrabajo'), ...riesgosApi }));
vi.mock('../../api/formBuilder', async () => ({ ...await vi.importActual<typeof import('../../api/formBuilder')>('../../api/formBuilder'), ...formApi }));
vi.mock('../../app/AuthContext', () => ({ useAuth: () => ({ usuario: { permisos: { RIESGOS_TRABAJO: { edit: true }, DOCUMENTOS: { create: true, delete: true } } } }) }));
vi.mock('../../components/FeedbackProvider', () => ({ useFeedback: () => ({ notify: vi.fn(), confirm: vi.fn().mockResolvedValue(true) }) }));
vi.mock('../../components/useUnsavedChanges', () => ({ useUnsavedChanges: vi.fn() }));

const forms = [
  { id_formulario: 'risk', nombre: 'Solo Riesgos', descripcion: null, estado_respuesta: 'PENDIENTE', total_preguntas: 2 },
  { id_formulario: 'multi', nombre: 'Riesgos y otro destino', descripcion: null, estado_respuesta: 'PENDIENTE', total_preguntas: 1 },
];
const documento = { id_archivo: 'doc-1', tipo_registro: 'CASOS', id_registro: 'risk-1', nombre_archivo: 'evidencia.pdf', mime_type: 'application/pdf', extension: 'pdf', tamano_bytes: 1024, tamano_comprimido_bytes: 512, sha256: 'hash', categoria_documento: 'EVIDENCIA', version: 1, activo: true, eliminado: false, fecha_creacion: '2026-09-15T10:00:00', creado_por: 'admin@example.com' };
const riskDestination = { id_destino: 'destino-riesgos-trabajo', codigo: 'RIESGOS_TRABAJO', nombre: 'Riesgos de trabajo', nivel: 'SUBPROCESO' as const, padre_id_destino: 'medico', activo: true, orden: 1, hijos: [] };
const tree = [{ id_destino: 'social', codigo: 'TRABAJO_SOCIAL', nombre: 'Trabajo Social', nivel: 'MACROPROCESO' as const, padre_id_destino: null, activo: true, orden: 1, hijos: [{ id_destino: 'medico', codigo: 'DEPARTAMENTO_MEDICO', nombre: 'Departamento Médico', nivel: 'PROCESO' as const, padre_id_destino: 'social', activo: true, orden: 1, hijos: [riskDestination] }] }];
const definition = { id_formulario: 'risk', nombre: 'Solo Riesgos', descripcion: null, responsable: null, estado: 'PUBLICADO' as const, fecha_publicacion: null, fecha_actualizacion: null, actualizado_por: null, permite_multiples_respuestas: false, version_publicada: 3, version: 4, activo: true, eliminado: false, destinos: [], destinos_jerarquicos: ['destino-riesgos-trabajo'], total_preguntas: 0, total_respuestas: 7, secciones: [], preguntas: [], reglas: [] };

describe('Integraciones reales de RiesgosTrabajo', () => {
  beforeEach(() => { vi.clearAllMocks(); riesgosApi.listarFormulariosRiesgo.mockResolvedValue(forms); riesgosApi.listarDocumentosRiesgo.mockResolvedValue([documento]); formApi.getFormDefinition.mockResolvedValue(definition); formApi.getFormResponse.mockResolvedValue(null); formApi.listDestinationTree.mockResolvedValue(tree); riesgosApi.responderFormularioRiesgo.mockResolvedValue({ id_respuesta: 'r1', codigo_respuesta: 'RIE-0007', version: 1, id_destino_respuesta: 'destino-riesgos-trabajo' }); });

  it('muestra solamente las plantillas ya filtradas por el endpoint contextual, incluida una multidestino una vez', async () => {
    render(<MemoryRouter><ContextFormsPanel contextType="CASOS" contextId="risk-1" riesgoId="risk-1" /></MemoryRouter>);
    expect(screen.getByText('Cargando formularios disponibles…')).toBeInTheDocument();
    expect(await screen.findByText('Solo Riesgos')).toBeInTheDocument();
    expect(screen.getByText('Riesgos y otro destino')).toBeInTheDocument();
    expect(screen.queryByText('Solo Accidentes')).not.toBeInTheDocument();
    expect(screen.queryByText('Solo Ausentismos')).not.toBeInTheDocument();
    expect(screen.queryByText('Solo Producción')).not.toBeInTheDocument();
    expect(riesgosApi.listarFormulariosRiesgo).toHaveBeenCalledWith('risk-1');
  });

  it.each([[401, 'Inicie sesión.'], [403, 'Sin permiso.']] as const)('propaga %i al cargar Formularios', async (status, message) => {
    riesgosApi.listarFormulariosRiesgo.mockRejectedValue(new HttpError(status, { ok: false, code: 'DENIED', message, correlationId: '' }));
    render(<MemoryRouter><ContextFormsPanel contextType="CASOS" contextId="risk-1" riesgoId="risk-1" /></MemoryRouter>);
    expect(await screen.findByRole('alert')).toHaveTextContent(message);
  });

  it('presenta vacío y error real de Formularios', async () => {
    riesgosApi.listarFormulariosRiesgo.mockResolvedValue([]);
    const { rerender } = render(<MemoryRouter><ContextFormsPanel contextType="CASOS" contextId="risk-1" riesgoId="risk-1" /></MemoryRouter>);
    expect(await screen.findByText('Sin formularios disponibles')).toBeInTheDocument();
    riesgosApi.listarFormulariosRiesgo.mockRejectedValue(new Error('offline'));
    rerender(<MemoryRouter><ContextFormsPanel contextType="CASOS" contextId="risk-2" riesgoId="risk-2" /></MemoryRouter>);
    expect(await screen.findByRole('alert')).toHaveTextContent('No fue posible cargar los formularios.');
  });

  it('responde por el endpoint contextual con el destino real de Riesgos, contexto Caso y sin doble envío', async () => {
    render(<MemoryRouter initialEntries={['/formularios/risk/responder?contexto_tipo=CASOS&contexto_id=risk-1&riesgo_id=risk-1&id_persona=persona-1']}><Routes><Route path="/formularios/:id/responder" element={<DynamicResponsePage />} /></Routes></MemoryRouter>);
    const user = userEvent.setup(); await screen.findByText('Solo Riesgos');
    let resolve!: (value: unknown) => void; riesgosApi.responderFormularioRiesgo.mockReturnValue(new Promise((done) => { resolve = done; }));
    await user.click(screen.getByRole('button', { name: 'Enviar formulario' }));
    expect(riesgosApi.responderFormularioRiesgo).toHaveBeenCalledOnce();
    expect(screen.getAllByRole('button', { name: 'Guardando…' })).toHaveLength(2);
    expect(riesgosApi.responderFormularioRiesgo).toHaveBeenCalledWith('risk-1', 'risk', expect.objectContaining({ contexto_tipo: 'CASOS', contexto_id: 'risk-1', id_persona: 'persona-1', id_destino_respuesta: 'destino-riesgos-trabajo' }));
    resolve({ id_respuesta: 'r1', codigo_respuesta: 'RIE-0007', version: 1, id_destino_respuesta: 'destino-riesgos-trabajo' });
  });

  it('muestra metadata, loading, vacío, error y permisos del panel documental contextual', async () => {
    const { rerender } = render(<DocumentosPanel tipoRegistro="CASOS" idRegistro="risk-1" riesgoId="risk-1" />);
    expect(screen.getByText('Cargando documentos…')).toBeInTheDocument();
    expect(await screen.findByText('evidencia.pdf')).toBeInTheDocument(); expect(screen.getByText('EVIDENCIA')).toBeInTheDocument(); expect(screen.getByText('admin@example.com')).toBeInTheDocument();
    riesgosApi.listarDocumentosRiesgo.mockResolvedValue([]);
    rerender(<DocumentosPanel tipoRegistro="CASOS" idRegistro="risk-2" riesgoId="risk-2" />);
    expect(await screen.findByText('Sin documentos adjuntos.')).toBeInTheDocument();
    riesgosApi.listarDocumentosRiesgo.mockRejectedValue(new HttpError(403, { ok: false, code: 'FORBIDDEN', message: 'Sin permiso.', correlationId: '' }));
    rerender(<DocumentosPanel tipoRegistro="CASOS" idRegistro="risk-3" riesgoId="risk-3" />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Sin permiso.');
  });

  it.each([[401, 'Inicie sesión.'], [403, 'Sin permiso.']] as const)('propaga %i al cargar Documentos', async (status, message) => {
    riesgosApi.listarDocumentosRiesgo.mockRejectedValue(new HttpError(status, { ok: false, code: 'DENIED', message, correlationId: '' }));
    render(<DocumentosPanel tipoRegistro="CASOS" idRegistro="risk-1" riesgoId="risk-1" />);
    expect(await screen.findByRole('alert')).toHaveTextContent(message);
  });
});
