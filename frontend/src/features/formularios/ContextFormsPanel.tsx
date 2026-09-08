import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { listContextForms, type ContextForm } from '../../api/formBuilder';
import { HttpError } from '../../api/client';
import { formatDateTime } from '../../utils/dates';

export function ContextFormsPanel({ contextType, contextId }: { contextType: string; contextId: string }) {
  const [forms, setForms] = useState<ContextForm[]>([]); const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => { setLoading(true); setError(null); listContextForms(contextType, contextId).then(setForms)
    .catch((err) => setError(err instanceof HttpError ? err.message : 'No fue posible cargar los formularios.')).finally(() => setLoading(false)); }, [contextType, contextId]);
  useEffect(() => { load(); }, [load]);
  if (loading) return <section className="panel"><h2>Formularios</h2><p className="footnote">Cargando formularios disponibles…</p></section>;
  return <section className="panel context-forms-panel"><div className="panel-header"><div><h2>Formularios</h2><p className="footnote">Formularios publicados para este registro.</p></div><span className="badge">{forms.length} disponibles</span></div>
    {error && <p className="form-error" role="alert">{error}</p>}
    {!forms.length && !error ? <div className="empty-state"><strong>Sin formularios disponibles</strong><p>No hay formularios publicados asignados a este módulo.</p></div> : <div className="context-form-list">{forms.map((form) => {
      const answered = form.estado_respuesta === 'REGISTRADO'; const draft = form.estado_respuesta === 'BORRADOR';
      const params = new URLSearchParams({ contexto_tipo: contextType, contexto_id: contextId });
      if (form.id_respuesta) params.set('respuesta', form.id_respuesta);
      return <article key={form.id_formulario}><div><div className="context-form-title"><h3>{form.nombre}</h3><span className={`badge${answered ? ' badge--success' : draft ? ' badge--warning' : ''}`}>{answered ? 'RESPONDIDO' : form.estado_respuesta}</span></div>
        <p>{form.descripcion || `${form.total_preguntas} preguntas`}</p>{form.codigo_respuesta && <small className="response-code">Código: {form.codigo_respuesta}</small>}{form.fecha_respuesta && <small>{formatDateTime(form.fecha_respuesta)}{form.usuario_respuesta ? ` · ${form.usuario_respuesta}` : ''}</small>}</div>
        <div className="record-actions"><Link className="button-link" to={`/formularios/${form.id_formulario}/responder?${params}`}>{answered ? 'Ver respuesta' : draft ? 'Continuar' : 'Responder'}</Link>
          {answered && form.permite_multiples_respuestas && form.puede_crear && <Link className="button-link secondary-link" to={`/formularios/${form.id_formulario}/responder?contexto_tipo=${encodeURIComponent(contextType)}&contexto_id=${encodeURIComponent(contextId)}`}>Responder nuevamente</Link>}
        </div></article>;
    })}</div>}
  </section>;
}
