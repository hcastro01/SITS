import { useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { listFormResponses, type FormResponse } from '../../api/formBuilder';
import { HttpError } from '../../api/client';
import { formatDateTime } from '../../utils/dates';

export function FormResponsesPanel({ formId }: { formId: string }) {
  const [responses, setResponses] = useState<FormResponse[]>([]);
  const [query, setQuery] = useState(''); const [appliedQuery, setAppliedQuery] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { setLoading(true); setError(null); listFormResponses(formId, appliedQuery).then(setResponses).catch((err) =>
    setError(err instanceof HttpError ? err.message : 'No fue posible cargar las respuestas.')).finally(() => setLoading(false)); }, [formId, appliedQuery]);
  function search(event: FormEvent) { event.preventDefault(); setAppliedQuery(query.trim()); }
  if (loading) return <p className="footnote">Cargando respuestas…</p>;
  if (error) return <p className="form-error" role="alert">{error}</p>;
  return <><form className="response-search" role="search" onSubmit={search}><label htmlFor="response-code-search">Buscar por código</label><div><input id="response-code-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="TTHH_RRLL_00000000001" /><button type="submit">Buscar</button>{appliedQuery && <button type="button" className="secondary" onClick={() => { setQuery(''); setAppliedQuery(''); }}>Limpiar</button>}</div></form>
  {!responses.length ? <div className="empty-state"><strong>Sin respuestas</strong><p>{appliedQuery ? 'No existe una respuesta con ese código.' : 'Las respuestas y borradores aparecerán aquí.'}</p></div> : <div className="table-scroll"><table className="data-table"><thead><tr>
    <th>Código</th><th>Fecha</th><th>Usuario</th><th>Contexto</th><th>Estado</th>
  </tr></thead><tbody>{responses.map((response) => <tr key={response.id_respuesta}>
    <td>{response.codigo_respuesta ? <Link className="response-code" to={`/formularios/${response.id_formulario}/responder?${new URLSearchParams({ respuesta: response.id_respuesta, contexto_tipo: response.contexto_tipo ?? 'GENERAL', ...(response.contexto_id ? { contexto_id: response.contexto_id } : {}) })}`}>{response.codigo_respuesta}</Link> : '—'}</td>
    <td>{formatDateTime(response.fecha_respuesta)}</td><td>{response.usuario_respuesta}</td>
    <td>{response.contexto_tipo === 'GENERAL' ? 'General' : `${response.contexto_tipo ?? '—'} · ${response.contexto_id ?? '—'}`}</td>
    <td><span className={`badge${response.estado === 'BORRADOR' ? ' badge--warning' : ' badge--success'}`}>{response.estado === 'REGISTRADO' ? 'Respondido' : 'Borrador'}</span></td>
  </tr>)}</tbody></table></div>}</>;
}
