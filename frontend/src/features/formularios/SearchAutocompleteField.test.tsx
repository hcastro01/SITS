import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { FormDefinition, SearchResult } from '../../api/formBuilder';
import { DynamicFormRenderer, type FormValues } from './DynamicFormRenderer';
import { SearchAutocompleteField } from './SearchAutocompleteField';

const apiMocks = vi.hoisted(() => ({ searchFormOptions: vi.fn() }));

vi.mock('../../api/formBuilder', async () => ({
  ...await vi.importActual<typeof import('../../api/formBuilder')>('../../api/formBuilder'),
  ...apiMocks,
}));

const people: SearchResult[] = [
  { id: 'person-1', label: 'CATAGUA OCHOA JENNIFER ELIANI', data: { nombre: 'CATAGUA OCHOA JENNIFER ELIANI' } },
];

function renderRemote(source = 'RESPONSABLES', onSelect = vi.fn()) {
  const user = userEvent.setup();
  render(<SearchAutocompleteField source={source} value="" ariaLabel="Responsable" onSelect={onSelect} />);
  return { user, onSelect, input: screen.getByRole('combobox', { name: 'Responsable' }) };
}

describe('SearchAutocompleteField', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('no abre ni consulta al recibir foco', async () => {
    const { user, input } = renderRemote();
    await user.click(input);
    expect(input).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
    expect(apiMocks.searchFormOptions).not.toHaveBeenCalled();
  });

  it('busca Responsable en su fuente con debounce y mantiene visible la selección', async () => {
    apiMocks.searchFormOptions.mockResolvedValue(people);
    const onSelect = vi.fn();
    function Harness() {
      const [value, setValue] = useState('');
      return <SearchAutocompleteField source="RESPONSABLES" value={value} ariaLabel="Responsable"
        onSelect={(result, text) => { onSelect(result, text); setValue(result?.id ?? text); }} />;
    }
    const user = userEvent.setup();
    render(<Harness />);
    const input = screen.getByRole('combobox', { name: 'Responsable' });

    await user.type(input, 'jen');
    expect(apiMocks.searchFormOptions).not.toHaveBeenCalled();
    await waitFor(() => expect(apiMocks.searchFormOptions).toHaveBeenCalledTimes(1));
    expect(apiMocks.searchFormOptions).toHaveBeenCalledWith('RESPONSABLES', 'jen', undefined, false);
    await user.click(await screen.findByRole('option', { name: people[0].label }));

    expect(onSelect).toHaveBeenLastCalledWith(people[0], people[0].label);
    expect(input).toHaveValue(people[0].label);
    expect(input).toHaveAttribute('aria-expanded', 'false');
  });

  it('consulta Áreas sin mezclar la fuente de Personas', async () => {
    const areas = [{ id: 'CONTROL DE CALIDAD', label: 'CONTROL DE CALIDAD', data: { area: 'CONTROL DE CALIDAD' } }];
    apiMocks.searchFormOptions.mockResolvedValue(areas);
    const { user, input } = renderRemote('AREAS');

    await user.type(input, 'calidad');

    await screen.findByRole('option', { name: 'CONTROL DE CALIDAD' });
    expect(apiMocks.searchFormOptions).toHaveBeenCalledTimes(1);
    expect(apiMocks.searchFormOptions).toHaveBeenCalledWith('AREAS', 'calidad', undefined, false);
  });

  it('el botón abre voluntariamente una lista limitada y vuelve a cerrarla', async () => {
    apiMocks.searchFormOptions.mockResolvedValue(people);
    const { user, input } = renderRemote();

    await user.click(screen.getByRole('button', { name: 'Mostrar opciones de Responsable' }));
    expect(await screen.findByRole('option', { name: people[0].label })).toBeInTheDocument();
    expect(apiMocks.searchFormOptions).toHaveBeenCalledWith('RESPONSABLES', '', undefined, true);
    expect(input).toHaveAttribute('aria-expanded', 'true');

    await user.click(screen.getByRole('button', { name: 'Cerrar opciones de Responsable' }));
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
    expect(input).toHaveAttribute('aria-expanded', 'false');
  });

  it('permite seleccionar con teclado y Escape cierra sin seleccionar', async () => {
    const onSelect = vi.fn();
    const options = [
      { id: 'quality', label: 'Gestión de Calidad', data: {} },
      { id: 'operations', label: 'Operaciones', data: {} },
    ];
    const user = userEvent.setup();
    render(<SearchAutocompleteField options={options} value="" ariaLabel="Área" onSelect={onSelect} />);
    const input = screen.getByRole('combobox', { name: 'Área' });

    await user.click(input);
    await user.keyboard('{ArrowDown}{ArrowDown}{Enter}');
    expect(onSelect).toHaveBeenLastCalledWith(options[0], options[0].label);
    expect(input).toHaveValue('Gestión de Calidad');

    await user.click(screen.getByRole('button', { name: 'Mostrar opciones de Área' }));
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });

  it('filtra opciones locales sin distinguir tildes y muestra el estado vacío', async () => {
    const options = [{ id: 'quality', label: 'Gestión de Calidad', data: {} }];
    const user = userEvent.setup();
    render(<SearchAutocompleteField options={options} value="" ariaLabel="Área" onSelect={vi.fn()} />);
    const input = screen.getByRole('combobox', { name: 'Área' });

    await user.type(input, 'gestion');
    expect(await screen.findByRole('option', { name: 'Gestión de Calidad' })).toBeInTheDocument();
    await user.clear(input);
    await user.type(input, 'finanzas');
    expect(await screen.findByText('No se encontraron coincidencias.')).toBeInTheDocument();
    expect(apiMocks.searchFormOptions).not.toHaveBeenCalled();
  });

  it('mantiene operativa una lista desplegable de un formulario existente', async () => {
    const definition: FormDefinition = {
      id_formulario: 'form-1', nombre: 'Formulario existente', descripcion: null, responsable: null,
      estado: 'PUBLICADO', fecha_publicacion: null, fecha_actualizacion: null, actualizado_por: null,
      permite_multiples_respuestas: false, version_publicada: 1, version: 1, activo: true,
      eliminado: false, destinos: ['GENERAL'], total_preguntas: 1, total_respuestas: 0,
      secciones: [], reglas: [], preguntas: [{
        id_pregunta: 'area', id_seccion: null, etiqueta: 'Área', descripcion: null,
        tipo: 'LISTA_DESPLEGABLE', obligatoria: true, orden: 0, texto_ayuda: null,
        valor_predeterminado: null, visible: true, solo_lectura: false, longitud_maxima: null,
        validacion: {}, configuracion: {}, fuente_datos: null, mapping: {}, opciones: [
          { id_opcion: 'o1', valor: 'CALIDAD', etiqueta: 'Control de Calidad', orden: 0 },
        ],
      }],
    };
    function Harness() {
      const [values, setValues] = useState<FormValues>({});
      return <><DynamicFormRenderer definition={definition} values={values} onChange={setValues} />
        <output>{String(values.area ?? '')}</output></>;
    }
    const user = userEvent.setup();
    render(<Harness />);

    await user.click(screen.getByRole('button', { name: 'Mostrar opciones de Área' }));
    await user.click(screen.getByRole('option', { name: 'Control de Calidad' }));
    expect(screen.getByRole('combobox', { name: 'Área' })).toHaveValue('Control de Calidad');
    expect(screen.getByText('CALIDAD')).toBeInTheDocument();
  });
});
