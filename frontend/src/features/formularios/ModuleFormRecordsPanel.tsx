import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { HttpError } from '../../api/client';
import { listModuleFormResponses, type PaginatedModuleResponses } from '../../api/formBuilder';
import { humanizeCode } from '../../utils/dates';

export function ModuleFormRecordsPanel({ module }: { module: string }) {
  const [data, setData] = useState<PaginatedModuleResponses | null>(null);
  const [page, setPage] = useState(1);
  const [state, setState] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true; setLoading(true); setError(null);
    listModuleFormResponses(module, page, state)
      .then((result) => { if (active) setData(result); })
      .catch((err: unknown) => { if (active) setError(err instanceof HttpError ? err.message : 'No fue posible cargar los registros de formularios.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [module, page, state]);

  return (
    <section className="module-form-records" aria-labelledby={`${module}-dynamic-title`}>
      <div className="section-heading module-records-heading">
        <div><h3 id={`${module}-dynamic-title`}>Registros mediante formularios</h3><p className="footnote">Respuestas dinámicas vinculadas a este módulo.</p></div>
        <label>Estado<select value={state} onChange={(event) => { setState(event.target.value); setPage(1); }}>
          <option value="">Todos</option><option value="BORRADOR">Borrador</option><option value="REGISTRADO">Registrado</option>
        </select></label>
      </div>
      {error && <p className="form-error" role="alert">{error}</p>}
      {loading ? <p>Cargando registros…</p> : !data?.items.length ? <p className="footnote">No hay registros dinámicos todavía.</p> : (
        <div className="table-scroll"><table className="data-table dynamic-record-table">
          <thead><tr><th>Código</th><th>Formulario</th><th>Persona</th><th>Fecha</th><th>Estado</th><th>Acciones</th></tr></thead>
          <tbody>{data.items.map((item) => {
            const base = `/formularios/${item.id_formulario}/responder?contexto_tipo=${encodeURIComponent(item.contexto_tipo ?? module)}&contexto_id=${encodeURIComponent(item.contexto_id ?? '')}&respuesta=${encodeURIComponent(item.id_respuesta)}`;
            return <tr key={item.id_respuesta}>
              <td><span className="response-code">{item.codigo_respuesta ?? 'Pendiente'}</span></td>
              <td>{item.formulario}</td><td>{item.persona ?? '—'}</td><td>{item.fecha_respuesta ?? '—'}</td>
              <td><span className="badge">{humanizeCode(item.estado)}</span></td>
              <td><div className="record-actions">
                {item.acciones?.ver && <Link to={base}>Ver</Link>}
                {item.acciones?.continuar && <Link to={base}>Continuar borrador</Link>}
                {item.acciones?.editar && <Link to={`${base}&editar=1`}>Editar</Link>}
                {item.acciones?.eliminar && <Link className="danger-link" to={`${base}&eliminar=1`}>Eliminar</Link>}
              </div></td>
            </tr>;
          })}</tbody>
        </table></div>
      )}
      {data && data.total_paginas > 1 && <div className="pagination-controls">
        <button type="button" className="secondary" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Anterior</button>
        <span>Página {data.pagina} de {data.total_paginas}</span>
        <button type="button" className="secondary" disabled={page >= data.total_paginas} onClick={() => setPage((value) => value + 1)}>Siguiente</button>
      </div>}
    </section>
  );
}
