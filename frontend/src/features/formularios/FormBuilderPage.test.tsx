import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { FormDefinition, FormQuestion, FormSection } from '../../api/formBuilder';
import { FeedbackProvider } from '../../components/FeedbackProvider';
import { FormBuilderPage } from './FormBuilderPage';

const apiMocks = vi.hoisted(() => ({
  getFormDefinition: vi.fn(),
  listSearchSources: vi.fn(),
  saveFormDefinition: vi.fn(),
  setFormStatus: vi.fn(),
}));

vi.mock('../../api/formBuilder', async () => ({
  ...await vi.importActual<typeof import('../../api/formBuilder')>('../../api/formBuilder'),
  ...apiMocks,
}));

function question(id: string, label: string, order: number, sectionId: string | null = null): FormQuestion {
  return {
    id_pregunta: id, id_seccion: sectionId, etiqueta: label, descripcion: null,
    tipo: 'TEXTO_CORTO', obligatoria: false, orden: order, texto_ayuda: null,
    valor_predeterminado: null, visible: true, solo_lectura: false, longitud_maxima: null,
    validacion: {}, configuracion: {}, fuente_datos: null, mapping: {}, opciones: [],
  };
}

const defaultSections: FormSection[] = [
  { id_seccion: 'section-1', titulo: 'Sección única', descripcion: null, orden: 0 },
];

function formDefinition(questions: FormQuestion[], sections = defaultSections): FormDefinition {
  return {
    id_formulario: 'form-1', nombre: 'Formulario de prueba', descripcion: null, responsable: null,
    estado: 'BORRADOR', fecha_publicacion: null, fecha_actualizacion: null, actualizado_por: null,
    permite_multiples_respuestas: false, version_publicada: 0, version: 1,
    activo: true, eliminado: false, destinos: ['GENERAL'], total_preguntas: questions.length,
    total_respuestas: 0, secciones: sections, preguntas: questions, reglas: [],
  };
}

async function renderBuilder(questions: FormQuestion[], sections = defaultSections) {
  apiMocks.getFormDefinition.mockResolvedValue(formDefinition(questions, sections));
  apiMocks.listSearchSources.mockResolvedValue([]);
  const user = userEvent.setup();
  const router = createMemoryRouter([
    { path: '/formularios/:id/editar', element: <FormBuilderPage /> },
  ], { initialEntries: [{ pathname: '/formularios/form-1/editar', state: { tab: 'preguntas' } }] });
  const result = render(
    <FeedbackProvider>
      <RouterProvider router={router} />
    </FeedbackProvider>,
  );
  await screen.findByText('Formulario de prueba');
  return { user, ...result };
}

function editorFor(label: string): HTMLElement {
  const editor = screen.getByDisplayValue(label).closest<HTMLElement>('.question-editor');
  if (!editor) throw new Error(`No se encontró el editor de ${label}`);
  return editor;
}

async function removeQuestion(user: ReturnType<typeof userEvent.setup>, label: string) {
  await user.click(within(editorFor(label)).getByRole('button', { name: 'Eliminar' }));
  const dialog = await screen.findByRole('dialog', { name: 'Eliminar pregunta' });
  expect(document.body.style.overflow).toBe('hidden');
  await user.click(within(dialog).getByRole('button', { name: 'Eliminar pregunta' }));
  await waitFor(() => expect(screen.queryByDisplayValue(label)).not.toBeInTheDocument());
  await waitFor(() => expect(document.body.style.overflow).toBe(''));
}

describe('FormBuilderPage: eliminación local de preguntas', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    document.body.style.overflow = '';
  });

  it('elimina la pregunta intermedia, selecciona la siguiente y permite mover, editar y agregar sin guardar ni recargar', async () => {
    const { user, container } = await renderBuilder([
      question('q1', 'Primera', 0),
      question('q2', 'Segunda', 1, 'section-1'),
      question('q3', 'Tercera', 2),
    ]);

    await user.click(screen.getByDisplayValue('Segunda'));
    await removeQuestion(user, 'Segunda');

    await waitFor(() => expect(editorFor('Tercera')).toHaveAttribute('data-selected', 'true'));
    await waitFor(() => expect(document.activeElement).toBe(editorFor('Tercera')));

    await user.click(within(editorFor('Tercera')).getByRole('button', { name: 'Mover arriba' }));
    expect(container.querySelector('.question-editor input') as HTMLInputElement).toHaveValue('Tercera');

    const title = screen.getByDisplayValue('Tercera');
    await user.clear(title);
    await user.type(title, 'Tercera editada');
    expect(screen.getByDisplayValue('Tercera editada')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '+ Agregar pregunta' }));
    expect(container.querySelectorAll('.question-editor')).toHaveLength(3);
    expect(screen.getByDisplayValue('Nueva pregunta').closest('.question-editor')).toHaveAttribute('data-selected', 'true');
    expect(screen.getByLabelText('Título sección 1')).toHaveValue('Sección única');
    expect(apiMocks.saveFormDefinition).not.toHaveBeenCalled();
    expect(apiMocks.getFormDefinition).toHaveBeenCalledTimes(1);
  });

  it('al eliminar la primera pregunta selecciona la que pasa a ocupar su lugar', async () => {
    const { user } = await renderBuilder([
      question('q1', 'Primera', 0), question('q2', 'Segunda', 1), question('q3', 'Tercera', 2),
    ]);

    await removeQuestion(user, 'Primera');

    await waitFor(() => expect(editorFor('Segunda')).toHaveAttribute('data-selected', 'true'));
    await waitFor(() => expect(document.activeElement).toBe(editorFor('Segunda')));
  });

  it('al eliminar la última pregunta selecciona la anterior', async () => {
    const { user } = await renderBuilder([
      question('q1', 'Primera', 0), question('q2', 'Segunda', 1), question('q3', 'Tercera', 2),
    ]);
    await user.click(screen.getByDisplayValue('Tercera'));

    await removeQuestion(user, 'Tercera');

    await waitFor(() => expect(editorFor('Segunda')).toHaveAttribute('data-selected', 'true'));
    await waitFor(() => expect(document.activeElement).toBe(editorFor('Segunda')));
  });

  it('al eliminar la única pregunta deja la selección vacía, enfoca Agregar y mantiene operativa la UI', async () => {
    const { user, container } = await renderBuilder([question('q1', 'Única', 0, 'section-1')]);

    await removeQuestion(user, 'Única');

    expect(container.querySelectorAll('.question-editor')).toHaveLength(0);
    expect(screen.getByRole('status')).toHaveTextContent('No hay preguntas');
    await waitFor(() => expect(document.activeElement).toBe(screen.getByRole('button', { name: '+ Agregar pregunta' })));

    await user.click(screen.getByRole('button', { name: '+ Agregar pregunta' }));
    expect(screen.getByDisplayValue('Nueva pregunta').closest('.question-editor')).toHaveAttribute('data-selected', 'true');
    expect(document.body.style.overflow).toBe('');
  });
});
