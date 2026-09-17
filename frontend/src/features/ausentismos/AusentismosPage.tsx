import { useEffect, useState, type FormEvent } from 'react';
import { HttpError } from '../../api/client';
import { listarAusentismos, obtenerAusentismo, type AusentismoOperativo, type FiltrosAusentismos } from '../../api/ausentismos';
import {
  analizarAusentismos, confirmarLoteAusentismos, listarErroresLoteAusentismos, listarLotesAusentismos,
  obtenerLoteAusentismos, type AnalisisAusentismo, type ErrorLoteAusentismo, type LoteAusentismo,
} from '../../api/importacionesAusentismos';
import { useFeedback } from '../../components/FeedbackProvider';
import { Modal } from '../../components/Modal';

type Tab = 'registros' | 'importar' | 'historial';
const pageSize = 25;
const filtrosAusentismosVacios = (): FiltrosAusentismos => ({ nombre: '', cedula: '', area: '', tipo_ausentismo: '', desde: '', hasta: '', origen: '', lote_id: '' });
const errorMessage = (error: unknown, fallback: string) => error instanceof HttpError ? error.message : fallback;
const formatDate = (value: string | null) => value ? new Date(value).toLocaleString('es-EC') : '—';

function estadoVisual(lote: LoteAusentismo, canConfirm: boolean) {
  if (lote.estado === 'CONFIRMADO') return 'Confirmado';
  if (lote.filas_con_error || lote.filas_duplicadas) return 'Con errores';
  return canConfirm ? 'Listo para confirmar' : 'Analizado';
}
function safeData(value: string | null) {
  if (!value) return '—';
  try { const item = JSON.parse(value) as Record<string, unknown>; return Object.entries(item).filter(([, entry]) => entry != null).map(([key, entry]) => `${key}: ${entry}`).join(' · ') || '—'; } catch { return '—'; }
}

export function AusentismosPage() {
  const { notify, confirm } = useFeedback();
  const [tab, setTab] = useState<Tab>('importar'); const [file, setFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<AnalisisAusentismo | null>(null); const [selected, setSelected] = useState<LoteAusentismo | null>(null);
  const [issues, setIssues] = useState<ErrorLoteAusentismo[]>([]); const [issueTotal, setIssueTotal] = useState(0); const [issuePage, setIssuePage] = useState(0);
  const [history, setHistory] = useState<LoteAusentismo[]>([]); const [historyTotal, setHistoryTotal] = useState(0); const [historyPage, setHistoryPage] = useState(0);
  const [loadingHistory, setLoadingHistory] = useState(true); const [analyzing, setAnalyzing] = useState(false); const [confirming, setConfirming] = useState(false); const [error, setError] = useState<string | null>(null);
  const [records, setRecords] = useState<AusentismoOperativo[]>([]); const [recordTotal, setRecordTotal] = useState(0); const [recordPage, setRecordPage] = useState(0); const [recordFilters, setRecordFilters] = useState<FiltrosAusentismos>(filtrosAusentismosVacios);
  const [loadingRecords, setLoadingRecords] = useState(false); const [recordError, setRecordError] = useState<string | null>(null); const [detail, setDetail] = useState<AusentismoOperativo | null>(null); const [detailLoading, setDetailLoading] = useState(false); const [detailError, setDetailError] = useState<string | null>(null);

  const active = selected ?? analysis?.lote ?? null;
  const canConfirm = Boolean(analysis?.lote.id_lote === active?.id_lote && analysis?.puede_confirmarse && active?.estado === 'ANALIZADO');
  function recordParams(page: number, filters: FiltrosAusentismos) {
    const params = new URLSearchParams({ limite: String(pageSize), offset: String(page * pageSize) });
    (Object.entries(filters) as [keyof FiltrosAusentismos, string][]).forEach(([key, value]) => { if (value.trim()) params.set(key, value.trim()); });
    return params;
  }
  async function loadRecords(page = recordPage, filters = recordFilters) {
    setLoadingRecords(true); setRecordError(null);
    try { const data = await listarAusentismos(recordParams(page, filters)); setRecords(data.items); setRecordTotal(data.total); }
    catch (err) { setRecords([]); setRecordTotal(0); setRecordError(errorMessage(err, 'No fue posible cargar los registros de Ausentismos.')); }
    finally { setLoadingRecords(false); }
  }

  async function loadHistory(page = historyPage) {
    setLoadingHistory(true);
    try { const data = await listarLotesAusentismos(new URLSearchParams({ limite: String(pageSize), offset: String(page * pageSize) })); setHistory(data.items); setHistoryTotal(data.total); }
    catch (err) { setError(errorMessage(err, 'No fue posible cargar el historial de importaciones.')); }
    finally { setLoadingHistory(false); }
  }
  async function loadIssues(lote: LoteAusentismo, page = issuePage) {
    try { const data = await listarErroresLoteAusentismos(lote.id_lote, new URLSearchParams({ limite: String(pageSize), offset: String(page * pageSize) })); setIssues(data.items); setIssueTotal(data.total); }
    catch (err) { setError(errorMessage(err, 'No fue posible cargar las incidencias del lote.')); }
  }
  useEffect(() => { void loadHistory(); }, [historyPage]);
  useEffect(() => { if (tab === 'registros') void loadRecords(); }, [tab, recordPage]);
  useEffect(() => { if (active && (active.filas_con_error || active.filas_duplicadas)) void loadIssues(active); else { setIssues([]); setIssueTotal(0); } }, [active?.id_lote, issuePage]);

  async function analyze() {
    if (!file || analyzing) return;
    setAnalyzing(true); setError(null);
    try { const result = await analizarAusentismos(file); setAnalysis(result); setSelected(result.lote); setIssuePage(0); setTab('importar'); notify('Archivo analizado. Revise el resultado antes de confirmar.', 'info'); await loadHistory(0); setHistoryPage(0); }
    catch (err) { setError(errorMessage(err, 'No fue posible analizar el archivo.')); }
    finally { setAnalyzing(false); }
  }
  async function openDetail(id: string) {
    setError(null);
    try { const lote = await obtenerLoteAusentismos(id); setAnalysis(null); setSelected(lote); setIssuePage(0); setTab('historial'); }
    catch (err) { setError(errorMessage(err, 'No fue posible cargar el detalle del lote.')); }
  }
  async function confirmImport() {
    if (!active || !canConfirm || confirming) return;
    if (!await confirm({ title: 'Confirmar importación', message: 'Esta acción registrará los Ausentismos válidos del lote.', confirmLabel: 'Confirmar importación' })) return;
    setConfirming(true); setError(null);
    try { const confirmed = await confirmarLoteAusentismos(active.id_lote); setSelected(confirmed); setAnalysis((current) => current ? { ...current, lote: confirmed, puede_confirmarse: false } : current); notify('Importación confirmada correctamente.'); await loadHistory(0); setHistoryPage(0); await loadRecords(0); setRecordPage(0); }
    catch (err) { setError(errorMessage(err, 'No fue posible confirmar la importación.')); }
    finally { setConfirming(false); }
  }
  const changeIssuePage = (next: number) => { setIssuePage(next); };
  function updateRecordFilter(field: keyof FiltrosAusentismos, value: string) { setRecordFilters((current) => ({ ...current, [field]: value })); setRecordPage(0); }
  function applyRecordFilters(event: FormEvent) { event.preventDefault(); setRecordPage(0); void loadRecords(0); }
  function clearRecordFilters() { const empty = filtrosAusentismosVacios(); setRecordFilters(empty); setRecordPage(0); void loadRecords(0, empty); }
  async function openRecordDetail(id: string) { setDetail(null); setDetailError(null); setDetailLoading(true); try { setDetail(await obtenerAusentismo(id)); } catch (err) { setDetailError(errorMessage(err, 'No fue posible cargar el detalle del Ausentismo.')); } finally { setDetailLoading(false); } }
  return <section className="ausentismos-page">
    <div className="panel panel-header"><div><p className="eyebrow">Departamento Médico</p><h2>Ausentismos</h2><p>Importe y confirme lotes XLSX mediante el flujo validado del sistema.</p></div></div>
    <div className="tabs" role="tablist" aria-label="Secciones de Ausentismos">
      {([['registros', 'Registros'], ['importar', 'Importar XLSX'], ['historial', 'Historial de cargas']] as [Tab, string][]).map(([value, label]) => <button key={value} type="button" role="tab" aria-selected={tab === value} onClick={() => setTab(value)}>{label}</button>)}
    </div>
    {error && <p className="form-error" role="alert">{error}</p>}
    {tab === 'registros' && <section className="panel"><div className="panel-header"><div><h3>Registros operativos</h3><p className="footnote">Ausentismos individuales registrados en el sistema.</p></div></div><form className="form-grid ausentismos-filters" onSubmit={applyRecordFilters}><label>Nombre<input aria-label="Filtrar por nombre" value={recordFilters.nombre} onChange={(event) => updateRecordFilter('nombre', event.target.value)} /></label><label>Cédula<input aria-label="Filtrar por cédula" value={recordFilters.cedula} onChange={(event) => updateRecordFilter('cedula', event.target.value)} /></label><label>Área<input aria-label="Filtrar por área" value={recordFilters.area} onChange={(event) => updateRecordFilter('area', event.target.value)} /></label><label>Tipo de ausentismo<input aria-label="Filtrar por tipo de ausentismo" value={recordFilters.tipo_ausentismo} onChange={(event) => updateRecordFilter('tipo_ausentismo', event.target.value)} /></label><label>Fecha desde<input aria-label="Filtrar desde" type="date" value={recordFilters.desde} onChange={(event) => updateRecordFilter('desde', event.target.value)} /></label><label>Fecha hasta<input aria-label="Filtrar hasta" type="date" value={recordFilters.hasta} onChange={(event) => updateRecordFilter('hasta', event.target.value)} /></label><label>Origen<select aria-label="Filtrar por origen" value={recordFilters.origen} onChange={(event) => updateRecordFilter('origen', event.target.value)}><option value="">Todos los orígenes</option><option value="IMPORTACION_XLSX">Importación XLSX</option></select></label><label>Lote<input aria-label="Filtrar por lote" value={recordFilters.lote_id} onChange={(event) => updateRecordFilter('lote_id', event.target.value)} /></label><div className="button-row full-width"><button type="submit">Aplicar filtros</button><button type="button" className="secondary" onClick={clearRecordFilters}>Limpiar filtros</button></div></form>{recordError ? <p className="form-error" role="alert">{recordError}</p> : loadingRecords ? <p className="loading-message">Cargando registros…</p> : records.length ? <RecordsTable records={records} onDetail={(id) => void openRecordDetail(id)} /> : <p className="empty-state">No existen registros de Ausentismos para los filtros seleccionados.</p>}<RecordPagination page={recordPage} total={recordTotal} count={records.length} onChange={setRecordPage} />{(detailLoading || detail || detailError) && <Modal titulo="Detalle de Ausentismo" onClose={() => { if (!detailLoading) { setDetail(null); setDetailError(null); } }} size="medium" closeOnBackdrop={!detailLoading}>{detailLoading ? <p className="loading-message">Cargando detalle…</p> : detailError ? <p className="form-error" role="alert">{detailError}</p> : detail && <RecordDetail record={detail} />}</Modal>}</section>}
    {tab === 'importar' && <section className="panel"><h3>Importar XLSX</h3><p className="footnote">Encabezados requeridos: cedula, fecha_inicio, fecha_fin, tipo_ausentismo y motivo. observacion es opcional.</p><div className="upload-form"><label>Archivo XLSX<input aria-label="Seleccionar archivo XLSX" type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" onChange={(event) => { setFile(event.target.files?.[0] ?? null); setAnalysis(null); setSelected(null); setIssues([]); }} /></label>{file && <p className="selected-file">Archivo seleccionado: <strong>{file.name}</strong> <button type="button" className="ghost" onClick={() => setFile(null)}>Reemplazar</button></p>}<button type="button" disabled={!file || analyzing} onClick={() => void analyze()}>{analyzing ? 'Analizando archivo…' : 'Analizar archivo'}</button></div>{active && <AnalysisDetail lote={active} canConfirm={canConfirm} issues={issues} issueTotal={issueTotal} issuePage={issuePage} onIssuePage={changeIssuePage} confirming={confirming} onConfirm={confirmImport} />}</section>}
    {tab === 'historial' && <section className="panel"><div className="panel-header"><div><h3>Historial de cargas</h3><p className="footnote">Los lotes históricos son de consulta.</p></div></div>{loadingHistory ? <p className="loading-message">Cargando historial…</p> : history.length ? <LotTable lots={history} onDetail={openDetail} /> : <p className="empty-state">No existen cargas registradas.</p>}<Pagination page={historyPage} total={historyTotal} onChange={setHistoryPage} label="historial" />{selected && <div className="lot-detail"><h3>Detalle del lote</h3><AnalysisDetail lote={selected} canConfirm={false} issues={issues} issueTotal={issueTotal} issuePage={issuePage} onIssuePage={changeIssuePage} confirming={false} onConfirm={confirmImport} /></div>}</section>}
  </section>;
}

function AnalysisDetail({ lote, canConfirm, issues, issueTotal, issuePage, onIssuePage, confirming, onConfirm }: { lote: LoteAusentismo; canConfirm: boolean; issues: ErrorLoteAusentismo[]; issueTotal: number; issuePage: number; onIssuePage: (page: number) => void; confirming: boolean; onConfirm: () => void }) {
  return <div className="analysis-detail"><div className="summary-grid">{[['Total de filas', lote.total_filas, ''], ['Válidas', lote.filas_validas, 'success'], ['Errores', lote.filas_con_error, lote.filas_con_error ? 'danger' : ''], ['Duplicadas', lote.filas_duplicadas, lote.filas_duplicadas ? 'warning' : ''], ['Importadas', lote.filas_importadas, 'success']].map(([label, value, tone]) => <article className={`kpi-card kpi-card--${tone}`} key={String(label)}><span className="kpi-label">{label}</span><strong className="kpi-value">{value}</strong></article>)}</div><div className="lot-status"><strong>Estado: {estadoVisual(lote, canConfirm)}</strong><span>Archivo: {lote.nombre_archivo} · Fecha: {formatDate(lote.fecha_creacion)}</span>{canConfirm && <button type="button" disabled={confirming} onClick={() => void onConfirm()}>{confirming ? 'Confirmando…' : 'Confirmar importación'}</button>}</div>{(lote.filas_con_error || lote.filas_duplicadas) > 0 && <><h4>Incidencias del lote</h4><IssuesTable issues={issues} /><Pagination page={issuePage} total={issueTotal} onChange={onIssuePage} label="incidencias" /></>}</div>;
}
function RecordsTable({ records, onDetail }: { records: AusentismoOperativo[]; onDetail: (id: string) => void }) { return <div className="table-scroll"><table className="data-table ausentismos-records-table"><thead><tr><th>Persona</th><th>Cédula</th><th>Área</th><th>Tipo de ausentismo</th><th>Fecha inicio</th><th>Fecha fin</th><th>Motivo</th><th>Registrado por</th><th>Origen</th><th>Acciones</th></tr></thead><tbody>{records.map((record) => <tr key={record.id_ausentismo}><td>{record.persona}</td><td>{record.cedula ?? 'Sin información'}</td><td>{record.area ?? 'Sin información'}</td><td>{record.tipo_ausentismo}</td><td>{record.fecha_inicio}</td><td>{record.fecha_fin}</td><td>{record.motivo}</td><td>{record.registrado_por ?? 'Sin información'}</td><td>{record.origen ?? 'Sin información'}</td><td><button type="button" className="secondary" onClick={() => onDetail(record.id_ausentismo)}>Ver detalle</button></td></tr>)}</tbody></table></div>; }
function RecordPagination({ page, total, count, onChange }: { page: number; total: number; count: number; onChange: (page: number) => void }) { const first = total ? page * pageSize + 1 : 0; const last = total ? page * pageSize + count : 0; return <div className="pagination-controls"><button type="button" className="secondary" disabled={!page || !total} onClick={() => onChange(page - 1)}>Anterior</button><span>{total ? `Mostrando ${first}-${last} de ${total}` : '0 registros'}</span><button type="button" className="secondary" disabled={page * pageSize + count >= total} onClick={() => onChange(page + 1)}>Siguiente</button></div>; }
function RecordDetail({ record }: { record: AusentismoOperativo }) { const fields: [string, string | null][] = [['Persona', record.persona], ['Cédula', record.cedula], ['Área', record.area], ['Fecha inicio', record.fecha_inicio], ['Fecha fin', record.fecha_fin], ['Tipo de ausentismo', record.tipo_ausentismo], ['Motivo', record.motivo], ['Observación', record.observacion], ['Fecha de registro', formatDate(record.fecha_registro)], ['Registrado por', record.registrado_por], ['Origen', record.origen], ['Lote relacionado', record.lote_nombre_archivo ? `${record.lote_nombre_archivo} (${record.lote_id})` : null]]; return <dl className="field-list">{fields.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value || 'Sin información'}</dd></div>)}</dl>; }
function LotTable({ lots, onDetail }: { lots: LoteAusentismo[]; onDetail: (id: string) => void }) { return <div className="table-scroll"><table className="data-table"><thead><tr><th>Fecha</th><th>Archivo</th><th>Usuario</th><th>Estado</th><th>Total</th><th>Válidas</th><th>Errores</th><th>Importadas</th><th /></tr></thead><tbody>{lots.map((lote) => <tr key={lote.id_lote}><td>{formatDate(lote.fecha_creacion)}</td><td>{lote.nombre_archivo}</td><td>{lote.usuario_id}</td><td>{lote.estado}</td><td>{lote.total_filas}</td><td>{lote.filas_validas}</td><td>{lote.filas_con_error}</td><td>{lote.filas_importadas}</td><td><button type="button" className="secondary" onClick={() => void onDetail(lote.id_lote)}>Ver detalle</button></td></tr>)}</tbody></table></div>; }
function IssuesTable({ issues }: { issues: ErrorLoteAusentismo[] }) { return <div className="table-scroll"><table className="data-table"><thead><tr><th>Fila</th><th>Código de error</th><th>Mensaje</th><th>Datos de fila</th></tr></thead><tbody>{issues.map((issue) => <tr key={issue.id_error}><td>{issue.numero_fila}</td><td>{issue.codigo}</td><td>{issue.mensaje}</td><td>{safeData(issue.datos_fila)}</td></tr>)}</tbody></table></div>; }
function Pagination({ page, total, onChange, label }: { page: number; total: number; onChange: (page: number) => void; label: string }) { const pages = Math.max(1, Math.ceil(total / pageSize)); return total > pageSize ? <div className="pagination-controls"><button type="button" className="secondary" disabled={!page} onClick={() => onChange(page - 1)}>Anterior</button><span>Página {page + 1} de {pages} · {total} {label}</span><button type="button" className="secondary" disabled={page + 1 >= pages} onClick={() => onChange(page + 1)}>Siguiente</button></div> : null; }
