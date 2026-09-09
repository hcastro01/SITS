import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { createFormDefinition, deleteFormDefinition, duplicateFormDefinition, listFormDefinitions, setFormStatus, type FormDefinition, type FormDestination } from '../../api/formBuilder';
import { HttpError } from '../../api/client';
import { Modal } from '../../components/Modal';
import { useFeedback } from '../../components/FeedbackProvider';
import { formatDateTime } from '../../utils/dates';

const destinationLabels: Record<string, string> = { GENERAL: 'General', CASOS: 'Casos', ATENCIONES: 'Atenciones', NOVEDADES: 'Novedades', RECORRIDOS: 'Recorridos', PERSONAS: 'Personas' };
const publishedDeleteMessage = 'Debe despublicar el formulario antes de eliminarlo.';
const responsesDeleteMessage = 'Este formulario no puede eliminarse porque contiene respuestas registradas. Puede archivarlo para conservar su historial.';

export function FormulariosAdminPage() {
  const navigate = useNavigate(); const { notify, confirm } = useFeedback();
  const [forms, setForms] = useState<FormDefinition[]>([]); const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null); const [creating, setCreating] = useState(false);
  const [name, setName] = useState(''); const [description, setDescription] = useState('');
  const [destinations, setDestinations] = useState<FormDestination[]>(['GENERAL']);
  const [query, setQuery] = useState(''); const [status, setStatus] = useState(''); const [module, setModule] = useState('');
  const [formToDelete, setFormToDelete] = useState<FormDefinition | null>(null); const [deleting, setDeleting] = useState(false);
  async function load() { setError(null); try { setForms(await listFormDefinitions()); } catch (err) { setError(err instanceof HttpError ? err.message : 'No fue posible cargar los formularios.'); } finally { setLoading(false); } }
  useEffect(() => { void load(); }, []);
  const filtered = useMemo(() => forms.filter((form) => (!query || `${form.nombre} ${form.descripcion ?? ''}`.toLowerCase().includes(query.toLowerCase())) && (!status || form.estado === status) && (!module || form.destinos.includes(module as FormDestination))), [forms, query, status, module]);
  async function create(event: FormEvent) { event.preventDefault(); setError(null); try { const form = await createFormDefinition({ nombre: name, descripcion: description || null, destinos: destinations }); setCreating(false); setName(''); setDescription(''); setDestinations(['GENERAL']); notify('Formulario creado.'); navigate(`/formularios/${form.id_formulario}`); } catch (err) { setError(err instanceof HttpError ? err.message : 'No fue posible crear el formulario.'); } }
  async function statusAction(form: FormDefinition, next: string) { if (next !== 'PUBLICADO' && !await confirm({ title: next === 'ARCHIVADO' ? 'Archivar formulario' : 'Despublicar formulario', message: 'El formulario dejará de estar disponible para nuevas respuestas.', confirmLabel: next === 'ARCHIVADO' ? 'Archivar' : 'Despublicar', danger: true })) return; try { await setFormStatus(form.id_formulario, next, form.version); await load(); notify('Estado actualizado.'); } catch (err) { notify(err instanceof HttpError ? err.message : 'No fue posible cambiar el estado.', 'error'); } }
  function requestDelete(form: FormDefinition) {
    if (form.estado === 'PUBLICADO') { notify(publishedDeleteMessage, 'error'); return; }
    if (form.total_respuestas > 0) { notify(responsesDeleteMessage, 'error'); return; }
    setFormToDelete(form);
  }
  async function removeForm() {
    if (!formToDelete || deleting) return;
    setDeleting(true);
    try {
      await deleteFormDefinition(formToDelete.id_formulario, formToDelete.version);
      setForms((current) => current.filter((form) => form.id_formulario !== formToDelete.id_formulario));
      setFormToDelete(null);
      notify('Formulario eliminado correctamente.');
    } catch (err) {
      notify(err instanceof HttpError ? err.message : 'No fue posible eliminar el formulario.', 'error');
    } finally { setDeleting(false); }
  }
  return <div className="forms-admin-page"><section className="panel forms-heading"><div><p className="eyebrow">Administración</p><h2>Formularios</h2><p>Diseñe, publique y consulte formularios dinámicos para los módulos de SITS.</p></div><button type="button" onClick={() => setCreating(true)}>+ Crear formulario</button></section>
    {error && <p className="form-error" role="alert">{error}</p>}
    <section className="panel form-filters"><label className="visually-hidden" htmlFor="search-form">Buscar formulario</label><input id="search-form" placeholder="Buscar formulario…" value={query} onChange={(e) => setQuery(e.target.value)} />
      <select aria-label="Filtrar por estado" value={status} onChange={(e) => setStatus(e.target.value)}><option value="">Todos los estados</option><option value="BORRADOR">Borrador</option><option value="PUBLICADO">Publicado</option><option value="INACTIVO">Inactivo</option><option value="ARCHIVADO">Archivado</option></select>
      <select aria-label="Filtrar por módulo" value={module} onChange={(e) => setModule(e.target.value)}><option value="">Todos los módulos</option>{Object.entries(destinationLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></section>
    {loading ? <p className="loading-message">Cargando formularios…</p> : filtered.length === 0 ? <div className="panel empty-state"><strong>No se encontraron formularios</strong><p>Cree uno nuevo o ajuste los filtros.</p></div> : <div className="form-cards">{filtered.map((form) => <article className="form-card" key={form.id_formulario}>
      <div className="form-card-top"><span className={`badge status-${form.estado.toLowerCase()}`}>{form.estado}</span><span className="form-card-date">Actualizado {formatDateTime(form.fecha_actualizacion)}</span></div><h3>{form.nombre}</h3><p>{form.descripcion || 'Sin descripción.'}</p>
      <div className="form-destinations">{form.destinos.map((item) => <span key={item}>{destinationLabels[item] ?? item}</span>)}</div>
      <dl className="form-metrics"><div><dt>Preguntas</dt><dd>{form.total_preguntas}</dd></div><div><dt>Respuestas</dt><dd>{form.total_respuestas}</dd></div><div><dt>Versión</dt><dd>{form.version_publicada || '—'}</dd></div></dl>
      <div className="form-card-actions">{form.estado !== 'ARCHIVADO' && <button type="button" onClick={() => navigate(`/formularios/${form.id_formulario}`)}>Editar</button>}<button type="button" className="secondary" onClick={() => navigate(`/formularios/${form.id_formulario}`, { state: { tab: 'vista-previa' } })}>Vista previa</button>
        <button type="button" className="secondary" onClick={() => navigate(`/formularios/${form.id_formulario}`, { state: { tab: 'respuestas' } })}>Respuestas</button>
        <button type="button" className="secondary" onClick={async () => { try { const copy = await duplicateFormDefinition(form.id_formulario); notify('Formulario duplicado.'); navigate(`/formularios/${copy.id_formulario}`); } catch (err) { notify(err instanceof HttpError ? err.message : 'No fue posible duplicar.', 'error'); } }}>Duplicar</button>
        {form.estado === 'PUBLICADO' ? <button type="button" className="ghost" onClick={() => void statusAction(form, 'INACTIVO')}>Despublicar</button> : form.estado !== 'ARCHIVADO' && <button type="button" className="ghost" disabled={!form.total_preguntas || !form.destinos.length} onClick={() => void statusAction(form, 'PUBLICADO')}>Publicar</button>}
        {form.estado !== 'ARCHIVADO' && <button type="button" className="ghost ghost-danger" onClick={() => void statusAction(form, 'ARCHIVADO')}>Archivar</button>}
        {form.acciones?.eliminar && <button type="button" className="ghost ghost-danger" onClick={() => requestDelete(form)}>Eliminar</button>}
      </div></article>)}</div>}
    {creating && <Modal titulo="Crear formulario" onClose={() => setCreating(false)} size="medium"><form onSubmit={create}><label htmlFor="new-form-name">Nombre</label><input id="new-form-name" required data-autofocus value={name} onChange={(e) => setName(e.target.value)} /><label htmlFor="new-form-description">Descripción</label><textarea id="new-form-description" value={description} onChange={(e) => setDescription(e.target.value)} />
      <fieldset className="compact-destinations"><legend>Mostrar en</legend>{(['CASOS', 'ATENCIONES', 'NOVEDADES', 'RECORRIDOS', 'PERSONAS', 'GENERAL'] as FormDestination[]).map((value) => <label key={value}><input type="checkbox" checked={destinations.includes(value)} onChange={(e) => setDestinations(e.target.checked ? [...destinations, value] : destinations.filter((item) => item !== value))} /> {destinationLabels[value]}</label>)}</fieldset>
      <div className="modal-actions"><button type="button" className="secondary" onClick={() => setCreating(false)}>Cancelar</button><button type="submit" disabled={!destinations.length}>Crear formulario</button></div></form></Modal>}
    {formToDelete && <Modal titulo="Eliminar formulario" onClose={() => { if (!deleting) setFormToDelete(null); }} size="small" closeOnBackdrop={!deleting}>
      <p className="dialog-message">¿Está seguro de que desea eliminar este formulario?</p>
      <p><strong>{formToDelete.nombre}</strong></p>
      <p className="inline-alert">Esta acción eliminará el formulario de los listados del sistema.</p>
      <div className="modal-actions"><button type="button" className="secondary" disabled={deleting} onClick={() => setFormToDelete(null)}>Cancelar</button><button type="button" className="danger" disabled={deleting} onClick={() => void removeForm()}>{deleting ? 'Eliminando…' : 'Eliminar'}</button></div>
    </Modal>}
  </div>;
}
