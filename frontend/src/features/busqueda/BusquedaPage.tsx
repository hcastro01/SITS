import { useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { buscarPorCodigo, buscarRegistrosPersona, type ConsolidatedRecord, type PersonRecordsResponse } from '../../api/busqueda';
import { HttpError } from '../../api/client';
import type { SearchResult } from '../../api/formBuilder';
import { SearchAutocompleteField } from '../formularios/SearchAutocompleteField';
import { humanizeCode } from '../../utils/dates';

const CODE_PATTERN = /^TTHH_RRLL_\d{11}$/i;

function actionUrl(item: ConsolidatedRecord, action?: 'editar' | 'eliminar') {
  if (item.tipo_registro === 'REGISTRO_BASE') return `/${item.contexto_tipo.toLowerCase()}/${item.contexto_id}`;
  const params = new URLSearchParams({ contexto_tipo: item.contexto_tipo, contexto_id: item.contexto_id, respuesta: item.id_respuesta ?? '' });
  if (action) params.set(action, '1');
  return `/formularios/${item.id_formulario}/responder?${params}`;
}

function RecordCard({ item }: { item: ConsolidatedRecord }) {
  return <article className="consolidated-record-card">
    <div className="record-card-main">
      <span className="response-code">{item.codigo_respuesta ?? 'Pendiente de asignación'}</span>
      <div className="record-card-tags"><span className="badge">{humanizeCode(item.contexto_tipo)}</span><span className="badge">{humanizeCode(item.estado)}</span></div>
      <h3>{item.formulario ?? `${humanizeCode(item.contexto_tipo)} histórico`}</h3>
      <dl><div><dt>Persona</dt><dd>{item.persona ?? '—'}</dd></div><div><dt>Fecha</dt><dd>{item.fecha_respuesta ?? '—'}</dd></div><div><dt>Responsable</dt><dd>{item.responsable ?? '—'}</dd></div><div><dt>Versión</dt><dd>{item.version}</dd></div></dl>
    </div>
    <div className="record-actions">
      {item.acciones.ver && <Link className="button-link secondary-link" to={actionUrl(item)}>Ver</Link>}
      {item.acciones.continuar && <Link className="button-link" to={actionUrl(item)}>Continuar</Link>}
      {item.acciones.editar && <Link className="button-link secondary-link" to={actionUrl(item, 'editar')}>Editar</Link>}
      {item.acciones.eliminar && <Link className="button-link danger-link-button" to={actionUrl(item, 'eliminar')}>Eliminar</Link>}
    </div>
  </article>;
}

export function BusquedaPage() {
  const [query, setQuery] = useState('');
  const [selectedPerson, setSelectedPerson] = useState<SearchResult | null>(null);
  const [data, setData] = useState<PersonRecordsResponse | null>(null);
  const [codeResult, setCodeResult] = useState<ConsolidatedRecord | null>(null);
  const [moduleFilter, setModuleFilter] = useState(''); const [stateFilter, setStateFilter] = useState('');
  const [page, setPage] = useState(1); const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadPerson(person = selectedPerson, nextPage = page) {
    if (!person) { setError('Seleccione una Persona de la lista de resultados.'); return; }
    setLoading(true); setError(null); setCodeResult(null);
    try { setData(await buscarRegistrosPersona(person.id, nextPage, moduleFilter, stateFilter)); }
    catch (err) { setError(err instanceof HttpError ? err.message : 'No fue posible consultar los registros de la Persona.'); }
    finally { setLoading(false); }
  }

  useEffect(() => { if (selectedPerson) void loadPerson(selectedPerson, page); }, [moduleFilter, stateFilter, page]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (CODE_PATTERN.test(query.trim())) {
      setLoading(true); setError(null); setData(null);
      try { setCodeResult(await buscarPorCodigo(query)); }
      catch (err) { setCodeResult(null); setError(err instanceof HttpError ? err.message : 'No fue posible buscar el código.'); }
      finally { setLoading(false); }
      return;
    }
    setPage(1); await loadPerson(selectedPerson, 1);
  }

  return <div className="person-search-page">
    <section className="panel search-hero"><p className="eyebrow">Consulta consolidada</p><h2>Buscar Persona o código</h2><p>Seleccione una Persona por nombre o ingrese un código TTHH_RRLL completo.</p>
      <form onSubmit={submit} className="consolidated-search-form"><label><span>Nombre de Persona o código de registro</span><SearchAutocompleteField source="PERSONAS" value={query} ariaLabel="Nombre de Persona o código de registro" placeholder="Ej. Ana López o TTHH_RRLL_00000000045" onSelect={(result, text) => { setSelectedPerson(result); setQuery(text); setCodeResult(null); if (result) { setPage(1); void loadPerson(result, 1); } }} /></label><button type="submit" disabled={loading}>{loading ? 'Buscando…' : 'Buscar'}</button></form>
      {error && <p className="form-error" role="alert">{error}</p>}
    </section>
    {codeResult && <section className="panel search-results-panel"><div className="section-heading"><div><p className="eyebrow">Resultado exacto</p><h2>{codeResult.codigo_respuesta}</h2></div></div><RecordCard item={codeResult} /></section>}
    {data && <section className="panel search-results-panel">
      <div className="person-summary"><div><p className="eyebrow">Persona seleccionada</p><h2>{data.persona.nombre}</h2><p>{[data.persona.codigo_empleado && `Código ${data.persona.codigo_empleado}`, data.persona.cedula && `Cédula ${data.persona.cedula}`].filter(Boolean).join(' · ') || 'Información disponible de Persona'}</p></div><strong>{data.total}<span>registros relacionados</span></strong></div>
      <div className="record-filters"><label>Módulo<select value={moduleFilter} onChange={(event) => { setModuleFilter(event.target.value); setPage(1); }}><option value="">Todos los módulos</option><option value="CASOS">Casos</option><option value="ATENCIONES">Atenciones</option><option value="NOVEDADES">Novedades</option><option value="RECORRIDOS">Recorridos</option><option value="PERSONAS">Personas</option><option value="FORMULARIOS">Solo formularios</option></select></label><label>Estado<select value={stateFilter} onChange={(event) => { setStateFilter(event.target.value); setPage(1); }}><option value="">Todos los estados</option><option value="REGISTRADO">Registrados</option><option value="BORRADOR">Borradores</option></select></label></div>
      {loading ? <p>Cargando registros…</p> : data.items.length === 0 ? <p className="empty-state">No hay registros relacionados con estos filtros.</p> : <div className="consolidated-records">{data.items.map((item) => <RecordCard key={`${item.tipo_registro}-${item.id_respuesta ?? item.contexto_id}`} item={item} />)}</div>}
      {data.total_paginas > 1 && <div className="pagination-controls"><button type="button" className="secondary" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Anterior</button><span>Página {data.pagina} de {data.total_paginas}</span><button type="button" className="secondary" disabled={page >= data.total_paginas} onClick={() => setPage((value) => value + 1)}>Siguiente</button></div>}
    </section>}
  </div>;
}
