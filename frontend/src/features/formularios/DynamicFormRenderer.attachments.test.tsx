import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { DynamicFormRenderer, type FormValues } from './DynamicFormRenderer';
import { saveFormResponseMultipart, type FormDefinition } from '../../api/formBuilder';

const getForBlob = vi.hoisted(() => vi.fn());
vi.mock('../../api/client', async () => ({ ...await vi.importActual<typeof import('../../api/client')>('../../api/client'), getForBlob }));

const question = (id: string, type: 'ARCHIVO' | 'FOTOGRAFIA', config: Record<string, unknown> = {}) => ({
  id_pregunta: id, id_seccion: null, etiqueta: id, descripcion: null, tipo: type, obligatoria: false,
  orden: 0, texto_ayuda: null, valor_predeterminado: null, visible: true, solo_lectura: false,
  longitud_maxima: null, validacion: {}, configuracion: config, fuente_datos: null, mapping: {}, opciones: [],
});
const definition = (questions = [question('10', 'ARCHIVO'), question('20', 'FOTOGRAFIA', { max_files: 2 })]): FormDefinition => ({
  id_formulario: 'f1', nombre: 'Adjuntos', descripcion: null, responsable: null, estado: 'PUBLICADO', fecha_publicacion: null,
  fecha_actualizacion: null, actualizado_por: null, permite_multiples_respuestas: true, version_publicada: 1, version: 1,
  activo: true, eliminado: false, destinos: ['GENERAL'], total_preguntas: questions.length, total_respuestas: 0,
  secciones: [], preguntas: questions, reglas: [],
});

describe('adjuntos de DynamicFormRenderer', () => {
  const create = vi.fn(); const revoke = vi.fn();
  beforeEach(() => { vi.clearAllMocks(); Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: create }); Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: revoke }); create.mockReturnValueOnce('blob:local').mockReturnValueOnce('blob:persisted').mockReturnValueOnce('blob:download'); });
  afterEach(() => { cleanup(); vi.useRealTimers(); });

  it('crea y revoca la URL local de fotografía al reemplazar y desmontar', () => {
    let values: FormValues = {}; const onChange = vi.fn((next) => { values = next; });
    const view = render(<DynamicFormRenderer definition={definition()} values={values} onChange={onChange} />);
    const input = screen.getByLabelText('20') as HTMLInputElement;
    const first = new File(['one'], 'one.jpg', { type: 'image/jpeg' });
    fireEvent.change(input, { target: { files: [first] } });
    view.rerender(<DynamicFormRenderer definition={definition()} values={values} onChange={onChange} />);
    expect(create).toHaveBeenCalledWith(first);
    const second = new File(['two'], 'two.jpg', { type: 'image/jpeg' });
    fireEvent.change(screen.getByLabelText('20'), { target: { files: [second] } });
    view.rerender(<DynamicFormRenderer definition={definition()} values={values} onChange={onChange} />);
    expect(revoke).toHaveBeenCalledWith('blob:local');
    view.unmount(); expect(revoke).toHaveBeenCalledTimes(2);
  });

  it('obtiene preview autenticado y revoca la URL al cerrar', async () => {
    create.mockReset().mockReturnValue('blob:persisted');
    getForBlob.mockResolvedValue({ blob: new Blob(['pdf'], { type: 'application/pdf' }), filename: 'stored.pdf' });
    render(<DynamicFormRenderer definition={definition([question('10', 'ARCHIVO')])} values={{ '10': [{ id_archivo: 'd1', nombre_archivo: 'stored.pdf', mime_type: 'application/pdf', tamano_bytes: 3 }] }} onChange={vi.fn()} readOnly responseId="r1" />);
    await userEvent.setup().click(screen.getByRole('button', { name: 'Vista previa' }));
    await waitFor(() => expect(getForBlob).toHaveBeenCalledWith('/formularios/respuestas/r1/adjuntos/d1/contenido'));
    await userEvent.setup().click(screen.getByRole('button', { name: 'Cerrar vista previa' }));
    expect(revoke).toHaveBeenCalledWith('blob:persisted');
  });
});

describe('multipart de respuestas', () => {
  it('mantiene payload escalar y repite archivo:id_pregunta sin serializar File', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ id_respuesta: 'r1' }), { status: 201, headers: { 'Content-Type': 'application/json' } }));
    const a = new File(['a'], 'a.pdf', { type: 'application/pdf' }); const b = new File(['b'], 'b.png', { type: 'image/png' });
    await saveFormResponseMultipart('/formularios/f1/respuestas', { respuestas: [{ id_pregunta: 'text', valor_texto: 'ok' }] }, [{ id_pregunta: '10', file: a }, { id_pregunta: '10', file: b }, { id_pregunta: '20', file: b }]);
    const body = fetchSpy.mock.calls[0][1]?.body as FormData;
    expect(JSON.parse(String(body.get('payload')))).toEqual({ respuestas: [{ id_pregunta: 'text', valor_texto: 'ok' }] });
    expect(body.getAll('archivo:10')).toHaveLength(2); expect(body.getAll('archivo:20')).toHaveLength(1);
    fetchSpy.mockRestore();
  });
});
