import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { deleteFormResponse, getFormDefinition, getFormResponse, listDestinationTree, saveFormResponse, saveFormResponseMultipart, type FormAnswer, type FormDefinition, type FormDestinationNode, type FormResponse } from '../../api/formBuilder';
import { HttpError } from '../../api/client';
import { useFeedback } from '../../components/FeedbackProvider';
import { useUnsavedChanges } from '../../components/useUnsavedChanges';
import { DynamicFormRenderer, type FieldValue, type FormValues } from './DynamicFormRenderer';
import { Modal } from '../../components/Modal';

function answerValue(answer: FormAnswer): FieldValue {
  if (answer.valor_booleano !== undefined) return answer.valor_booleano;
  return String(answer.valor_texto ?? answer.valor_numero ?? answer.valor_fecha ?? answer.valor_opcion ?? '');
}

function flattenDestinations(nodes: FormDestinationNode[]): FormDestinationNode[] {
  return nodes.flatMap((node) => [node, ...flattenDestinations(node.hijos)]);
}

function branchDestinationIds(nodes: FormDestinationNode[], processCode: string | null): Set<string> | null {
  if (!processCode) return null;
  const process = flattenDestinations(nodes).find((node) => node.codigo === processCode);
  return process ? new Set(flattenDestinations(process.hijos).map((node) => node.id_destino)) : new Set();
}

function destinationPaths(nodes: FormDestinationNode[]): Map<string, string> {
  const paths = new Map<string, string>();
  const visit = (node: FormDestinationNode, parent: string[]) => { const path = [...parent, node.nombre]; paths.set(node.id_destino, path.join(' → ')); node.hijos.forEach((child) => visit(child, path)); };
  nodes.forEach((node) => visit(node, [])); return paths;
}

export function DynamicResponsePage() {
  const { id = '' } = useParams(); const [params] = useSearchParams(); const navigate = useNavigate();
  const { notify, confirm } = useFeedback(); const contextType = params.get('contexto_tipo') ?? 'GENERAL';
  const contextId = params.get('contexto_id'); const responseId = params.get('respuesta');
  const createContext = params.get('crear_contexto') === '1'; const personId = params.get('id_persona');
  const editRequested = params.get('editar') === '1';
  const requestedDestinationId = params.get('id_destino_respuesta'); const contextualProcessCode = params.get('proceso_contextual');
  const riesgoId = params.get('riesgo_id');
  const productionKind = params.get('produccion_tipo') as 'atenciones' | 'recorridos' | 'novedades' | null;
  const productionId = params.get('produccion_id');
  const officeKind = params.get('oficina_tipo') as 'atenciones' | 'beneficios' | 'prestamos' | 'seguro' | null;
  const officeId = params.get('oficina_id');
  const [definition, setDefinition] = useState<FormDefinition | null>(null); const [response, setResponse] = useState<FormResponse | null>(null);
  const [destinationTree, setDestinationTree] = useState<FormDestinationNode[]>([]); const [selectedDestinationId, setSelectedDestinationId] = useState<string | null>(null);
  const [values, setValues] = useState<FormValues>({}); const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false); const [error, setError] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(params.get('eliminar') === '1'); const [deleteReason, setDeleteReason] = useState('');
  const clientKey = useRef(crypto.randomUUID()); const finalized = response?.estado === 'REGISTRADO';
  const editing = Boolean(finalized && editRequested && response?.acciones?.editar);
  const readOnly = Boolean(finalized && !editing);
  useUnsavedChanges(dirty && !saving && !readOnly);
  useEffect(() => { let active = true; Promise.all([getFormDefinition(id), listDestinationTree(), responseId ? getFormResponse(responseId) : Promise.resolve(null)])
    .then(([form, tree, saved]) => { if (!active) return; setDefinition(saved?.definicion ?? form); setDestinationTree(tree); setResponse(saved); setSelectedDestinationId(saved?.id_destino_respuesta ?? null); if (saved?.respuestas) {
      const next: FormValues = {}; saved.respuestas.forEach((answer) => { const value = answer.adjuntos?.length ? answer.adjuntos : answerValue(answer); const existing = next[answer.id_pregunta]; next[answer.id_pregunta] = existing === undefined ? value : Array.isArray(existing) ? [...existing as string[], String(value)] : [String(existing), String(value)]; }); setValues(next); setDirty(false);
    }}).catch((err) => { if (active) setError(err instanceof HttpError ? err.message : 'No fue posible cargar el formulario.'); }).finally(() => { if (active) setLoading(false); }); return () => { active = false; }; }, [id, responseId]);

  const destinations = useMemo(() => {
    if (!definition) return [];
    const permitted = new Set(definition.destinos_jerarquicos ?? []); const branchIds = branchDestinationIds(destinationTree, contextualProcessCode);
    return flattenDestinations(destinationTree).filter((node) => node.nivel === 'SUBPROCESO' && node.activo && permitted.has(node.id_destino) && (!branchIds || branchIds.has(node.id_destino)));
  }, [definition, destinationTree, contextualProcessCode]);
  const destinationById = useMemo(() => new Map(destinations.map((node) => [node.id_destino, node])), [destinations]);
  const allDestinationPaths = useMemo(() => destinationPaths(destinationTree), [destinationTree]);
  useEffect(() => {
    if (!definition || response) return;
    if (requestedDestinationId && destinationById.has(requestedDestinationId)) setSelectedDestinationId(requestedDestinationId);
    else if (destinations.length === 1) setSelectedDestinationId(destinations[0].id_destino);
    else if (requestedDestinationId) setSelectedDestinationId(null);
  }, [definition, response, requestedDestinationId, destinations, destinationById]);

  function toAnswers(): FormAnswer[] {
    if (!definition) return []; const result: FormAnswer[] = [];
    definition.preguntas.forEach((question) => { const value = values[question.id_pregunta]; if (value === undefined || value === '' || (Array.isArray(value) && !value.length)) return;
      if (['ARCHIVO', 'FOTOGRAFIA'].includes(question.tipo) && Array.isArray(value)) return;
      const items = Array.isArray(value) ? value : [value]; items.forEach((item) => {
        if (['NUMERO', 'NUMERO_ENTERO', 'NUMERO_DECIMAL', 'MONEDA', 'PORCENTAJE', 'ESCALA', 'CALIFICACION'].includes(question.tipo)) result.push({ id_pregunta: question.id_pregunta, valor_numero: Number(item) });
        else if (['FECHA', 'HORA', 'FECHA_HORA'].includes(question.tipo)) result.push({ id_pregunta: question.id_pregunta, valor_fecha: String(item) });
        else if (['SELECCION_UNICA', 'LISTA_DESPLEGABLE', 'SELECCION_MULTIPLE', 'CASILLAS', 'BUSQUEDA', 'ARCHIVO', 'FOTOGRAFIA'].includes(question.tipo)) result.push({ id_pregunta: question.id_pregunta, valor_opcion: String(item) });
        else result.push({ id_pregunta: question.id_pregunta, valor_texto: String(item) });
      });
    }); return result;
  }

  async function persist(draft: boolean) {
    if (!definition || readOnly) return;
    const hasHierarchicalDestinations = (definition.destinos_jerarquicos ?? []).length > 0;
    const responseDestinationId = response?.id_destino_respuesta ?? selectedDestinationId;
    if (!response && hasHierarchicalDestinations && (!responseDestinationId || !destinationById.has(responseDestinationId))) { setError(destinations.length ? 'Seleccione un destino válido para registrar la respuesta.' : 'No hay destinos válidos disponibles para este formulario en la rama actual.'); return; }
    if (!draft && !await confirm({ title: editing ? 'Guardar cambios' : 'Enviar respuesta final', message: editing ? 'Se guardará una nueva versión de la respuesta conservando su código y trazabilidad.' : 'La respuesta quedará registrada. Verifique la información antes de continuar.', confirmLabel: editing ? 'Guardar cambios' : 'Enviar formulario' })) return;
    setSaving(true); setError(null);
    try {
      const basePayload = { borrador: true, respuestas: toAnswers(), id_envio_cliente: clientKey.current,
        contexto_tipo: contextType, contexto_id: contextId, id_respuesta: response?.id_respuesta,
        expected_version: response?.version, crear_contexto: createContext && !response,
        id_persona: personId, editar_registrado: editing, id_destino_respuesta: responseDestinationId };
      const files = definition.preguntas.flatMap((question) => {
        const value = values[question.id_pregunta]; return Array.isArray(value) && value.some((item) => item instanceof File) ? (value as File[]).map((file) => ({ question, file })) : [];
      });
      const payload = { ...basePayload, borrador: draft };
      const path = riesgoId ? `/riesgos-trabajo/${encodeURIComponent(riesgoId)}/formularios/${encodeURIComponent(id)}/respuestas`
        : productionKind && productionId ? `/produccion/${productionKind}/${encodeURIComponent(productionId)}/formularios/${encodeURIComponent(id)}/respuestas`
        : officeKind && officeId ? `/oficina/${officeKind}/${encodeURIComponent(officeId)}/formularios/${encodeURIComponent(id)}/respuestas`
        : `/formularios/${encodeURIComponent(id)}/respuestas`;
      const saved = files.length || riesgoId || productionKind || officeKind
        ? await saveFormResponseMultipart(path, payload, files.map(({ question, file }) => ({ id_pregunta: question.id_pregunta, file })))
        : await saveFormResponse(id, payload);
      setResponse(saved); setDirty(false); notify(draft ? 'Borrador guardado correctamente.' : `Formulario enviado correctamente. Código: ${saved.codigo_respuesta ?? 'no disponible'}.`);
      const stableParams = new URLSearchParams({ contexto_tipo: saved.contexto_tipo ?? contextType, respuesta: saved.id_respuesta });
      if (saved.contexto_id) stableParams.set('contexto_id', saved.contexto_id);
      navigate(`/formularios/${id}/responder?${stableParams}`, { replace: true });
    } catch (err) { const message = err instanceof HttpError ? err.message : 'No fue posible guardar la respuesta.'; setError(message); notify(message, 'error'); }
    finally { setSaving(false); }
  }
  function submit(event: FormEvent) { event.preventDefault(); void persist(false); }
  async function removeResponse() {
    if (!response || !deleteReason.trim()) { setError('Debe indicar el motivo de eliminación.'); return; }
    setSaving(true); setError(null);
    try {
      await deleteFormResponse(response.id_respuesta, response.version, deleteReason.trim());
      notify('Registro eliminado correctamente.');
      const targetType = response.contexto_tipo ?? contextType;
      navigate(targetType === 'GENERAL' ? `/formularios/${id}` : `/${targetType.toLowerCase()}`);
    } catch (err) { const message = err instanceof HttpError ? err.message : 'No fue posible eliminar el registro.'; setError(message); notify(message, 'error'); }
    finally { setSaving(false); }
  }
  if (loading) return <p className="loading-message">Cargando formulario…</p>;
  if (!definition) return <p className="form-error">{error ?? 'Formulario no encontrado.'}</p>;
  const responseDestination = response?.id_destino_respuesta ? allDestinationPaths.get(response.id_destino_respuesta) : undefined;
  const selectedDestination = selectedDestinationId ? destinationById.get(selectedDestinationId) : undefined;
  const modulePath = contextType === 'GENERAL' ? `/formularios/${id}` : `/${contextType.toLowerCase()}`;
  const backPath = contextId ? `${modulePath}/${contextId}` : modulePath;
  return <div className="response-page"><Link className="back-link" to={backPath}>← Volver</Link>
    <section id="response-detail" className="panel response-panel module-response-panel"><div className="response-form-heading"><p className="eyebrow">{editing ? 'Editar respuesta registrada' : finalized ? 'Respuesta registrada' : response ? 'Continuar borrador' : 'Nuevo formulario'}</p><h2>{definition.nombre}</h2>{response && <p className="response-code-display"><span>Código</span><strong>{response.codigo_respuesta ?? 'Pendiente de asignación'}</strong></p>}{definition.descripcion && <p>{definition.descripcion}</p>}
      {response && <dl className="response-metadata"><div><dt>Módulo</dt><dd>{response.contexto_tipo ?? 'GENERAL'}</dd></div><div><dt>Persona</dt><dd>{response.persona ?? '—'}</dd></div><div><dt>Estado</dt><dd>{response.estado}</dd></div><div><dt>Fecha</dt><dd>{response.fecha_respuesta ?? '—'}</dd></div><div><dt>Respondido por</dt><dd>{response.usuario_respuesta}</dd></div></dl>}
    </div>
      {error && <p className="form-error" role="alert">{error}</p>}
      {!readOnly && !response && (definition.destinos_jerarquicos ?? []).length > 0 && <section className="destination-manager module-destination-manager" aria-label="Destino del registro"><h3>Destino del registro</h3>{destinations.length === 1 && selectedDestination ? <p><strong>Este registro se guardará en:</strong> {allDestinationPaths.get(selectedDestination.id_destino)}</p> : <label>¿Dónde se registrará esta respuesta?<select value={selectedDestinationId ?? ''} onChange={(event) => { setSelectedDestinationId(event.target.value || null); setDirty(true); }}><option value="">Seleccione un destino</option>{destinations.map((destination) => <option key={destination.id_destino} value={destination.id_destino}>{allDestinationPaths.get(destination.id_destino)}</option>)}</select></label>}<p className="footnote">El destino se valida nuevamente al guardar.</p></section>}
      {(responseDestination || selectedDestination) && <p className="footnote"><strong>Destino del registro:</strong> {responseDestination ?? allDestinationPaths.get(selectedDestination?.id_destino ?? '')}</p>}
      <form onSubmit={submit}><DynamicFormRenderer definition={definition} values={values} onChange={(next) => { setValues(next); setDirty(true); }} readOnly={readOnly} responseId={response?.id_respuesta} />
        {!readOnly && <div className="response-actions">{!editing && <button type="button" className="secondary" disabled={saving} onClick={() => void persist(true)}>{saving ? 'Guardando…' : 'Guardar borrador'}</button>}<button type="submit" disabled={saving}>{saving ? 'Guardando…' : editing ? 'Guardar cambios' : 'Enviar formulario'}</button></div>}
        {readOnly && <><div className="inline-success">Respuesta registrada correctamente. Código: <strong>{response?.codigo_respuesta}</strong>.</div><div className="response-actions"><a className="button-link secondary-link" href="#response-detail">Ver respuesta</a><Link className="button-link" to={(response?.contexto_tipo ?? contextType) === 'GENERAL' ? `/formularios/${id}` : `/${(response?.contexto_tipo ?? contextType).toLowerCase()}`}>Volver al módulo</Link></div></>}
      </form>
      {response?.acciones?.eliminar && <div className="danger-zone"><button type="button" className="danger" onClick={() => setDeleteOpen(true)}>Eliminar registro</button></div>}
    </section>
    {deleteOpen && response?.acciones?.eliminar && <Modal titulo="Eliminar registro" size="small" onClose={() => setDeleteOpen(false)}>
      <p className="dialog-message">La eliminación será lógica y quedará registrada en auditoría. El código no se reutilizará.</p>
      <label>Motivo de eliminación<textarea value={deleteReason} onChange={(event) => setDeleteReason(event.target.value)} rows={3} /></label>
      <div className="modal-actions"><button type="button" className="secondary" onClick={() => setDeleteOpen(false)}>Cancelar</button><button type="button" className="danger" disabled={saving || !deleteReason.trim()} onClick={() => void removeResponse()}>Eliminar</button></div>
    </Modal>}
  </div>;
}
