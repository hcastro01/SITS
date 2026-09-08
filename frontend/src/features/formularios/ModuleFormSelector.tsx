import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { HttpError } from '../../api/client';
import { listAvailableForms, type AvailableForm, type SearchResult } from '../../api/formBuilder';
import { Modal } from '../../components/Modal';
import { SearchAutocompleteField } from './SearchAutocompleteField';

export function ModuleFormSelector({ module, moduleLabel, fixedPersonId, onClose }: {
  module: string;
  moduleLabel: string;
  fixedPersonId?: string;
  onClose: () => void;
}) {
  const navigate = useNavigate();
  const [forms, setForms] = useState<AvailableForm[]>([]);
  const [selectedForm, setSelectedForm] = useState('');
  const [selectedPerson, setSelectedPerson] = useState<SearchResult | null>(null);
  const [personText, setPersonText] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const personRequired = module === 'PERSONAS';

  useEffect(() => {
    let active = true;
    listAvailableForms(module)
      .then((items) => { if (active) { setForms(items); if (items.length === 1) setSelectedForm(items[0].id_formulario); } })
      .catch((err: unknown) => { if (active) setError(err instanceof HttpError ? err.message : 'No fue posible cargar los formularios.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [module]);

  function continueToForm() {
    const personId = fixedPersonId ?? selectedPerson?.id;
    if (!selectedForm) { setError('Seleccione un formulario para continuar.'); return; }
    if (personRequired && !personId) { setError('Seleccione una Persona de la lista de resultados.'); return; }
    const params = new URLSearchParams({ contexto_tipo: module });
    if (module === 'PERSONAS') params.set('contexto_id', personId ?? '');
    else {
      params.set('crear_contexto', '1');
      if (personId) params.set('id_persona', personId);
    }
    navigate(`/formularios/${selectedForm}/responder?${params}`);
  }

  return (
    <Modal titulo={`Nuevo registro · ${moduleLabel}`} onClose={onClose} size="large">
      <p className="selector-intro">Seleccione el formulario publicado que desea utilizar.</p>
      {error && <p className="form-error" role="alert">{error}</p>}
      {loading ? <p>Cargando formularios…</p> : forms.length === 0 ? (
        <><div className="empty-state form-selector-empty">
          <strong>No hay formularios activos disponibles para este módulo.</strong>
          <p>Un administrador puede publicar un formulario y asignarlo a {moduleLabel} desde el módulo Formularios.</p>
        </div><div className="modal-actions"><button type="button" className="secondary" onClick={onClose}>Cancelar</button></div></>
      ) : (
        <>
          <fieldset className="form-selector-list">
            <legend>Formulario</legend>
            {forms.map((form) => (
              <label key={form.id_formulario} className={selectedForm === form.id_formulario ? 'is-selected' : ''}>
                <input type="radio" name="selected-form" value={form.id_formulario}
                       checked={selectedForm === form.id_formulario} onChange={() => setSelectedForm(form.id_formulario)} />
                <span><strong>{form.nombre}</strong><small>{form.descripcion || 'Sin descripción'} · {form.total_preguntas} pregunta(s)</small></span>
              </label>
            ))}
          </fieldset>
          {!fixedPersonId && (
            <label className="person-selector-field">
              <span>Persona asociada {personRequired ? <strong aria-label="obligatorio">*</strong> : <small>(opcional)</small>}</span>
              <SearchAutocompleteField source="PERSONAS" value={personText} placeholder="Buscar Persona por nombre…"
                onSelect={(result, text) => { setSelectedPerson(result); setPersonText(text); }} />
              <small>Escriba al menos dos caracteres y seleccione una coincidencia.</small>
            </label>
          )}
          <div className="modal-actions">
            <button type="button" className="secondary" onClick={onClose}>Cancelar</button>
            <button type="button" onClick={continueToForm}>Continuar</button>
          </div>
        </>
      )}
    </Modal>
  );
}
