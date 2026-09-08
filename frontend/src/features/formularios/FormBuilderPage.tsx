import { useCallback, useEffect, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import {
  getFormDefinition, listSearchSources, saveFormDefinition, setFormStatus,
  type FormDefinition, type FormQuestion, type FormSection, type SearchSource,
} from '../../api/formBuilder';
import { HttpError } from '../../api/client';
import { useFeedback } from '../../components/FeedbackProvider';
import { useUnsavedChanges } from '../../components/useUnsavedChanges';
import { DynamicFormRenderer, type FormValues } from './DynamicFormRenderer';
import { FormResponsesPanel } from './FormResponsesPanel';
import { QuestionEditor } from './QuestionEditor';

type Tab = 'configuracion' | 'preguntas' | 'vista-previa' | 'respuestas';
const DESTINATIONS = [
  ['CASOS', 'Casos'], ['ATENCIONES', 'Atenciones'], ['NOVEDADES', 'Novedades'],
  ['RECORRIDOS', 'Recorridos'], ['PERSONAS', 'Personas'], ['GENERAL', 'General'],
] as const;
function uid() { return crypto.randomUUID(); }

function newQuestion(sectionId: string | null = null): FormQuestion {
  return { id_pregunta: uid(), id_seccion: sectionId, etiqueta: 'Nueva pregunta', descripcion: null,
    tipo: 'TEXTO_CORTO', obligatoria: false, orden: 0, texto_ayuda: null,
    valor_predeterminado: null, visible: true, solo_lectura: false, longitud_maxima: null,
    validacion: {}, configuracion: {}, fuente_datos: null, mapping: {}, opciones: [] };
}

export function FormBuilderPage() {
  const { id = '' } = useParams();
  const location = useLocation(); const navigate = useNavigate();
  const { notify, confirm } = useFeedback();
  const [definition, setDefinition] = useState<FormDefinition | null>(null);
  const [sources, setSources] = useState<SearchSource[]>([]);
  const requestedTab = (location.state as { tab?: Tab } | null)?.tab;
  const [tab, setTab] = useState<Tab>(requestedTab && ['configuracion', 'preguntas', 'vista-previa', 'respuestas'].includes(requestedTab) ? requestedTab : 'configuracion');
  const [previewValues, setPreviewValues] = useState<FormValues>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useUnsavedChanges(dirty);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [form, availableSources] = await Promise.all([getFormDefinition(id), listSearchSources()]);
      setDefinition(form); setSources(availableSources);
    } catch (err) { setError(err instanceof HttpError ? err.message : 'No fue posible cargar el formulario.'); }
    finally { setLoading(false); }
  }, [id]);
  useEffect(() => { void load(); }, [load]);

  function update(patch: Partial<FormDefinition>) {
    setDefinition((current) => current ? { ...current, ...patch } : current); setDirty(true);
  }

  async function save(): Promise<FormDefinition | null> {
    if (!definition) return null;
    setSaving(true); setError(null);
    try {
      const saved = await saveFormDefinition(id, { expected_version: definition.version,
        nombre: definition.nombre, descripcion: definition.descripcion,
        permite_multiples_respuestas: definition.permite_multiples_respuestas,
        destinos: definition.destinos, secciones: definition.secciones,
        preguntas: definition.preguntas, reglas: definition.reglas });
      setDefinition(saved); setDirty(false); notify('Formulario guardado correctamente.'); return saved;
    } catch (err) { const message = err instanceof HttpError ? err.message : 'No fue posible guardar el formulario.'; setError(message); notify(message, 'error'); return null; }
    finally { setSaving(false); }
  }

  async function changeStatus(status: string) {
    if (!definition) return;
    if (['INACTIVO', 'ARCHIVADO'].includes(status) && !await confirm({ title: status === 'ARCHIVADO' ? 'Archivar formulario' : 'Despublicar formulario',
      message: 'El formulario dejará de estar disponible para nuevas respuestas.', confirmLabel: status === 'ARCHIVADO' ? 'Archivar' : 'Despublicar', danger: true })) return;
    const current = dirty ? await save() : definition;
    if (!current) return;
    setSaving(true); setError(null);
    try { await setFormStatus(id, status, current.version); notify(status === 'PUBLICADO' ? 'Formulario publicado.' : 'Estado actualizado.'); if (status === 'ARCHIVADO') navigate('/formularios'); else await load(); }
    catch (err) { const message = err instanceof HttpError ? err.message : 'No fue posible cambiar el estado.'; setError(message); notify(message, 'error'); }
    finally { setSaving(false); }
  }

  function moveQuestion(index: number, direction: -1 | 1) {
    if (!definition) return; const questions = [...definition.preguntas];
    [questions[index], questions[index + direction]] = [questions[index + direction], questions[index]];
    update({ preguntas: questions.map((question, order) => ({ ...question, orden: order })) });
  }

  function moveSection(index: number, direction: -1 | 1) {
    if (!definition) return; const sections = [...definition.secciones];
    [sections[index], sections[index + direction]] = [sections[index + direction], sections[index]];
    update({ secciones: sections.map((section, order) => ({ ...section, orden: order })) });
  }

  async function deleteQuestion(question: FormQuestion) {
    if (!definition || !await confirm({ title: 'Eliminar pregunta', message: `Se retirará «${question.etiqueta}» de la nueva definición. Las versiones históricas no se modifican.`, confirmLabel: 'Eliminar pregunta', danger: true })) return;
    update({ preguntas: definition.preguntas.filter((item) => item.id_pregunta !== question.id_pregunta),
      reglas: definition.reglas.filter((rule) => rule.id_pregunta_origen !== question.id_pregunta && rule.id_pregunta_destino !== question.id_pregunta) });
  }

  if (loading) return <p className="loading-message">Cargando constructor…</p>;
  if (!definition) return <p className="form-error">{error ?? 'Formulario no encontrado.'}</p>;

  return <div className="form-builder-page">
    <Link className="back-link" to="/formularios">← Formularios</Link>
    <section className="panel builder-hero"><div>
      <p className="eyebrow">Constructor visual · Versión publicada {definition.version_publicada || '—'}</p>
      <h2>{definition.nombre}</h2><p>{definition.descripcion || 'Sin descripción.'}</p>
    </div><div className="builder-hero-actions"><span className={`badge status-${definition.estado.toLowerCase()}`}>{definition.estado}</span>
      <button type="button" disabled={saving || !dirty} onClick={() => void save()}>{saving ? 'Guardando…' : 'Guardar cambios'}</button>
      {definition.estado !== 'PUBLICADO' ? <button type="button" className="secondary" disabled={saving || definition.preguntas.length === 0 || definition.destinos.length === 0} onClick={() => void changeStatus('PUBLICADO')}>Publicar</button>
        : <button type="button" className="secondary" disabled={saving} onClick={() => void changeStatus('INACTIVO')}>Despublicar</button>}
    </div></section>
    {error && <p className="form-error" role="alert">{error}</p>}
    <div className="tabs builder-tabs" role="tablist" aria-label="Constructor de formulario">
      {([['configuracion', 'Configuración'], ['preguntas', `Preguntas (${definition.preguntas.length})`], ['vista-previa', 'Vista previa'], ['respuestas', `Respuestas (${definition.total_respuestas})`]] as [Tab, string][]).map(([value, label]) =>
        <button key={value} type="button" role="tab" aria-selected={tab === value} onClick={() => setTab(value)}>{label}</button>)}
    </div>

    {tab === 'configuracion' && <section className="panel builder-settings"><h3>Configuración general</h3>
      <div className="builder-grid"><label className="builder-field builder-field--wide">Nombre<input value={definition.nombre} onChange={(e) => update({ nombre: e.target.value })} /></label>
        <label className="builder-field builder-field--wide">Descripción<textarea value={definition.descripcion ?? ''} onChange={(e) => update({ descripcion: e.target.value || null })} /></label></div>
      <fieldset className="destination-picker"><legend>Mostrar formulario en</legend><p>Seleccione uno o varios módulos donde estará disponible al publicarse.</p>
        <div>{DESTINATIONS.map(([value, label]) => <label key={value} className={definition.destinos.includes(value) ? 'is-selected' : ''}>
          <input type="checkbox" checked={definition.destinos.includes(value)} onChange={(e) => update({ destinos: e.target.checked ? [...definition.destinos, value] : definition.destinos.filter((item) => item !== value) })} />
          <strong>{label}</strong><small>{value === 'GENERAL' ? 'Sin contexto específico' : `Dentro de ${label.toLowerCase()}`}</small>
        </label>)}</div></fieldset>
      <label className="toggle-card"><input type="checkbox" checked={definition.permite_multiples_respuestas} onChange={(e) => update({ permite_multiples_respuestas: e.target.checked })} />
        <span><strong>Permitir múltiples respuestas por contexto</strong><small>Útil para seguimientos periódicos. Desactivado mantiene una respuesta o borrador por usuario y contexto.</small></span></label>
      <div className="button-row"><button type="button" disabled={saving || !dirty} onClick={() => void save()}>Guardar configuración</button>
        <button type="button" className="danger" disabled={saving} onClick={() => void changeStatus('ARCHIVADO')}>Archivar</button></div>
    </section>}

    {tab === 'preguntas' && <div className="builder-workspace">
      <section className="panel section-manager"><div className="section-heading"><div><h3>Secciones</h3><p className="footnote">Agrupe preguntas para facilitar formularios extensos.</p></div>
        <button type="button" className="secondary" onClick={() => update({ secciones: [...definition.secciones, { id_seccion: uid(), titulo: `Sección ${definition.secciones.length + 1}`, descripcion: null, orden: definition.secciones.length }] })}>+ Agregar sección</button></div>
        {definition.secciones.map((section, index) => <div className="section-editor-row" key={section.id_seccion}><span>{index + 1}</span>
          <input aria-label={`Título sección ${index + 1}`} value={section.titulo} onChange={(e) => update({ secciones: definition.secciones.map((item) => item.id_seccion === section.id_seccion ? { ...item, titulo: e.target.value } : item) })} />
          <input aria-label={`Descripción sección ${index + 1}`} placeholder="Descripción opcional" value={section.descripcion ?? ''} onChange={(e) => update({ secciones: definition.secciones.map((item) => item.id_seccion === section.id_seccion ? { ...item, descripcion: e.target.value || null } : item) })} />
          <div className="section-order-actions"><button type="button" className="ghost icon-button" aria-label={`Mover sección ${index + 1} arriba`} disabled={index === 0} onClick={() => moveSection(index, -1)}>↑</button>
            <button type="button" className="ghost icon-button" aria-label={`Mover sección ${index + 1} abajo`} disabled={index === definition.secciones.length - 1} onClick={() => moveSection(index, 1)}>↓</button></div>
          <button type="button" className="ghost" onClick={() => update({ secciones: definition.secciones.filter((item) => item.id_seccion !== section.id_seccion), preguntas: definition.preguntas.map((question) => question.id_seccion === section.id_seccion ? { ...question, id_seccion: null } : question) })}>Eliminar</button>
        </div>)}</section>
      <div className="question-editors">{definition.preguntas.map((question, index) => <QuestionEditor key={question.id_pregunta}
        question={question} index={index} total={definition.preguntas.length} sections={definition.secciones}
        allQuestions={definition.preguntas} rules={definition.reglas} sources={sources}
        onChange={(changed) => update({ preguntas: definition.preguntas.map((item) => item.id_pregunta === changed.id_pregunta ? changed : item) })}
        onRulesChange={(rules) => update({ reglas: rules })} onMove={(direction) => moveQuestion(index, direction)}
        onDelete={() => void deleteQuestion(question)} onDuplicate={() => { const copyId = uid(); update({ preguntas: [...definition.preguntas.slice(0, index + 1), { ...question, id_pregunta: copyId, etiqueta: `${question.etiqueta} (copia)`, opciones: question.opciones.map((option) => ({ ...option, id_opcion: uid() })) }, ...definition.preguntas.slice(index + 1)] }); }} />)}</div>
      <button type="button" className="add-question-button" onClick={() => update({ preguntas: [...definition.preguntas, newQuestion(definition.secciones[0]?.id_seccion ?? null)] })}>+ Agregar pregunta</button>
    </div>}

    {tab === 'vista-previa' && <section className="panel form-preview"><div className="preview-banner"><strong>Vista previa interactiva</strong><span>No se guardarán respuestas.</span></div>
      <div className="response-form-heading"><h2>{definition.nombre}</h2>{definition.descripcion && <p>{definition.descripcion}</p>}</div>
      <DynamicFormRenderer definition={definition} values={previewValues} onChange={setPreviewValues} />
      <button type="button" disabled>Enviar formulario</button></section>}
    {tab === 'respuestas' && <section className="panel"><h3>Respuestas</h3><FormResponsesPanel formId={definition.id_formulario} /></section>}
  </div>;
}
