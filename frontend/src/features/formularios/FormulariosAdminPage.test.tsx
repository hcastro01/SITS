import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { FormDefinition } from '../../api/formBuilder';
import { FeedbackProvider } from '../../components/FeedbackProvider';
import { FormulariosAdminPage } from './FormulariosAdminPage';

const apiMocks = vi.hoisted(() => ({
  createFormDefinition: vi.fn(),
  deleteFormDefinition: vi.fn(),
  duplicateFormDefinition: vi.fn(),
  listFormDefinitions: vi.fn(),
  setFormStatus: vi.fn(),
}));

vi.mock('../../api/formBuilder', async () => ({
  ...await vi.importActual<typeof import('../../api/formBuilder')>('../../api/formBuilder'),
  ...apiMocks,
}));

function form(overrides: Partial<FormDefinition> = {}): FormDefinition {
  return {
    id_formulario: 'form-1', nombre: 'Ficha eliminable', descripcion: 'Sin respuestas',
    responsable: null, estado: 'BORRADOR', fecha_publicacion: null,
    fecha_actualizacion: '2026-09-08T10:00:00Z', actualizado_por: 'admin@example.com',
    permite_multiples_respuestas: false, version_publicada: 0, version: 1,
    activo: true, eliminado: false, destinos: ['GENERAL'], total_preguntas: 2,
    total_respuestas: 0, secciones: [], preguntas: [], reglas: [],
    acciones: { eliminar: true }, ...overrides,
  };
}

async function renderPage(forms: FormDefinition[]) {
  apiMocks.listFormDefinitions.mockResolvedValue(forms);
  const user = userEvent.setup();
  const router = createMemoryRouter([
    { path: '/formularios', element: <FormulariosAdminPage /> },
    { path: '/formularios/:id', element: <div>Constructor</div> },
  ], { initialEntries: ['/formularios'] });
  render(
    <FeedbackProvider>
      <RouterProvider router={router} />
    </FeedbackProvider>,
  );
  await screen.findByRole('heading', { name: 'Formularios' });
  await screen.findByRole('heading', { name: forms[0].nombre });
  return user;
}

function cardFor(name: string): HTMLElement {
  const card = screen.getByRole('heading', { name }).closest<HTMLElement>('.form-card');
  if (!card) throw new Error(`No se encontró la tarjeta de ${name}`);
  return card;
}

describe('FormulariosAdminPage: eliminación segura', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    document.body.style.overflow = '';
  });

  it('cancela sin eliminar y el modal libera scroll y restaura el foco', async () => {
    const target = form();
    const user = await renderPage([target]);
    const deleteButton = within(cardFor(target.nombre)).getByRole('button', { name: 'Eliminar' });

    await user.click(deleteButton);
    const dialog = await screen.findByRole('dialog', { name: 'Eliminar formulario' });
    expect(within(dialog).getByText('¿Está seguro de que desea eliminar este formulario?')).toBeInTheDocument();
    expect(within(dialog).getByText(target.nombre)).toBeInTheDocument();
    expect(within(dialog).getByText('Esta acción eliminará el formulario de los listados del sistema.')).toBeInTheDocument();
    expect(document.body.style.overflow).toBe('hidden');

    await user.click(within(dialog).getByRole('button', { name: 'Cancelar' }));

    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Eliminar formulario' })).not.toBeInTheDocument());
    expect(apiMocks.deleteFormDefinition).not.toHaveBeenCalled();
    expect(screen.getByRole('heading', { name: target.nombre })).toBeInTheDocument();
    expect(document.body.style.overflow).toBe('');
    expect(document.activeElement).toBe(deleteButton);
  });

  it('elimina, actualiza la lista sin reload y conserva los filtros activos', async () => {
    const target = form();
    apiMocks.deleteFormDefinition.mockResolvedValue({ ...target, activo: false, eliminado: true, version: 2 });
    const user = await renderPage([target, form({ id_formulario: 'form-2', nombre: 'Otra ficha' })]);
    const search = screen.getByRole('textbox', { name: 'Buscar formulario' });
    await user.type(search, 'eliminable');
    const deleteButton = within(cardFor(target.nombre)).getByRole('button', { name: 'Eliminar' });
    await user.click(deleteButton);
    const dialog = await screen.findByRole('dialog', { name: 'Eliminar formulario' });

    await user.click(within(dialog).getByRole('button', { name: 'Eliminar' }));

    await waitFor(() => expect(screen.queryByRole('heading', { name: target.nombre })).not.toBeInTheDocument());
    expect(apiMocks.deleteFormDefinition).toHaveBeenCalledWith(target.id_formulario, target.version);
    expect(apiMocks.listFormDefinitions).toHaveBeenCalledTimes(1);
    expect(search).toHaveValue('eliminable');
    expect(screen.getByText('Formulario eliminado correctamente.')).toBeInTheDocument();
    expect(screen.queryByRole('dialog', { name: 'Eliminar formulario' })).not.toBeInTheDocument();
    expect(document.body.style.overflow).toBe('');
  });

  it('oculta la acción sin permiso y bloquea formularios publicados o con respuestas', async () => {
    const published = form({ id_formulario: 'published', nombre: 'Ficha publicada', estado: 'PUBLICADO' });
    const responded = form({ id_formulario: 'responded', nombre: 'Ficha respondida', total_respuestas: 3 });
    const unauthorized = form({ id_formulario: 'unauthorized', nombre: 'Ficha sin permiso', acciones: { eliminar: false } });
    const archived = form({ id_formulario: 'archived', nombre: 'Ficha archivada', estado: 'ARCHIVADO' });
    const user = await renderPage([published, responded, unauthorized, archived]);

    expect(within(cardFor(unauthorized.nombre)).queryByRole('button', { name: 'Eliminar' })).not.toBeInTheDocument();

    await user.click(within(cardFor(published.nombre)).getByRole('button', { name: 'Eliminar' }));
    expect(screen.getByText('Debe despublicar el formulario antes de eliminarlo.')).toBeInTheDocument();
    expect(screen.queryByRole('dialog', { name: 'Eliminar formulario' })).not.toBeInTheDocument();

    await user.click(within(cardFor(responded.nombre)).getByRole('button', { name: 'Eliminar' }));
    expect(screen.getByText('Este formulario no puede eliminarse porque contiene respuestas registradas. Puede archivarlo para conservar su historial.')).toBeInTheDocument();
    expect(apiMocks.deleteFormDefinition).not.toHaveBeenCalled();

    await user.click(within(cardFor(archived.nombre)).getByRole('button', { name: 'Eliminar' }));
    expect(await screen.findByRole('dialog', { name: 'Eliminar formulario' })).toBeInTheDocument();
  });
});
