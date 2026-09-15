import { useEffect, useMemo, useState } from 'react';
import { HttpError } from '../../api/client';
import {
  analizarAusentismos, confirmarLoteAusentismos, listarErroresLoteAusentismos, listarLotesAusentismos,
  obtenerLoteAusentismos, type AnalisisAusentismo, type ErrorLoteAusentismo, type LoteAusentismo,
} from '../../api/importacionesAusentismos';
import { useFeedback } from '../../components/FeedbackProvider';

type Tab = 'registros' | 'importar' | 'historial';
const pageSize = 25;
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

  const active = selected ?? analysis?.lote ?? null;
  const canConfirm = Boolean(analysis?.lote.id_lote === active?.id_lote && analysis?.puede_confirmarse && active?.estado === 'ANALIZADO');
  const confirmedLots = useMemo(() => history.filter((item) => item.estado === 'CONFIRMADO'), [history]);

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
    try { const confirmed = await confirmarLoteAusentismos(active.id_lote); setSelected(confirmed); setAnalysis((current) => current ? { ...current, lote: confirmed, puede_confirmarse: false } : current); notify('Importación confirmada correctamente.'); await loadHistory(0); setHistoryPage(0); }
    catch (err) { setError(errorMessage(err, 'No fue posible confirmar la importación.')); }
    finally { setConfirming(false); }
  }
  const changeIssuePage = (next: number) => { setIssuePage(next); };
  return <section className="ausentismos-page">
    <div className="panel panel-header"><div><p className="eyebrow">Departamento Médico</p><h2>Ausentismos</h2><p>Importe y confirme lotes XLSX mediante el flujo validado del sistema.</p></div></div>
    <div className="tabs" role="tablist" aria-label="Secciones de Ausentismos">
      {([['registros', 'Registros'], ['importar', 'Importar XLSX'], ['historial', 'Historial de cargas']] as [Tab, string][]).map(([value, label]) => <button key={value} type="button" role="tab" aria-selected={tab === value} onClick={() => setTab(value)}>{label}</button>)}
    </div>
    {error && <p className="form-error" role="alert">{error}</p>}
    {tab === 'registros' && <section className="panel"><h3>Registros importados</h3><p className="footnote">La consulta individual de Ausentismos no tiene endpoint disponible. Se muestran los lotes confirmados y sus conteos reales.</p>{confirmedLots.length ? <LotTable lots={confirmedLots} onDetail={openDetail} /> : <p className="empty-state">No hay lotes confirmados en esta página de historial.</p>}</section>}
    {tab === 'importar' && <section className="panel"><h3>Importar XLSX</h3><p className="footnote">Encabezados requeridos: cedula, fecha_inicio, fecha_fin, tipo_ausentismo y motivo. observacion es opcional.</p><div className="upload-form"><label>Archivo XLSX<input aria-label="Seleccionar archivo XLSX" type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" onChange={(event) => { setFile(event.target.files?.[0] ?? null); setAnalysis(null); setSelected(null); setIssues([]); }} /></label>{file && <p className="selected-file">Archivo seleccionado: <strong>{file.name}</strong> <button type="button" className="ghost" onClick={() => setFile(null)}>Reemplazar</button></p>}<button type="button" disabled={!file || analyzing} onClick={() => void analyze()}>{analyzing ? 'Analizando archivo…' : 'Analizar archivo'}</button></div>{active && <AnalysisDetail lote={active} canConfirm={canConfirm} issues={issues} issueTotal={issueTotal} issuePage={issuePage} onIssuePage={changeIssuePage} confirming={confirming} onConfirm={confirmImport} />}</section>}
    {tab === 'historial' && <section className="panel"><div className="panel-header"><div><h3>Historial de cargas</h3><p className="footnote">Los lotes históricos son de consulta.</p></div></div>{loadingHistory ? <p className="loading-message">Cargando historial…</p> : history.length ? <LotTable lots={history} onDetail={openDetail} /> : <p className="empty-state">No existen cargas registradas.</p>}<Pagination page={historyPage} total={historyTotal} onChange={setHistoryPage} label="historial" />{selected && <div className="lot-detail"><h3>Detalle del lote</h3><AnalysisDetail lote={selected} canConfirm={false} issues={issues} issueTotal={issueTotal} issuePage={issuePage} onIssuePage={changeIssuePage} confirming={false} onConfirm={confirmImport} /></div>}</section>}
  </section>;
}

function AnalysisDetail({ lote, canConfirm, issues, issueTotal, issuePage, onIssuePage, confirming, onConfirm }: { lote: LoteAusentismo; canConfirm: boolean; issues: ErrorLoteAusentismo[]; issueTotal: number; issuePage: number; onIssuePage: (page: number) => void; confirming: boolean; onConfirm: () => void }) {
  return <div className="analysis-detail"><div className="summary-grid">{[['Total de filas', lote.total_filas, ''], ['Válidas', lote.filas_validas, 'success'], ['Errores', lote.filas_con_error, lote.filas_con_error ? 'danger' : ''], ['Duplicadas', lote.filas_duplicadas, lote.filas_duplicadas ? 'warning' : ''], ['Importadas', lote.filas_importadas, 'success']].map(([label, value, tone]) => <article className={`kpi-card kpi-card--${tone}`} key={String(label)}><span className="kpi-label">{label}</span><strong className="kpi-value">{value}</strong></article>)}</div><div className="lot-status"><strong>Estado: {estadoVisual(lote, canConfirm)}</strong><span>Archivo: {lote.nombre_archivo} · Fecha: {formatDate(lote.fecha_creacion)}</span>{canConfirm && <button type="button" disabled={confirming} onClick={() => void onConfirm()}>{confirming ? 'Confirmando…' : 'Confirmar importación'}</button>}</div>{(lote.filas_con_error || lote.filas_duplicadas) > 0 && <><h4>Incidencias del lote</h4><IssuesTable issues={issues} /><Pagination page={issuePage} total={issueTotal} onChange={onIssuePage} label="incidencias" /></>}</div>;
}
function LotTable({ lots, onDetail }: { lots: LoteAusentismo[]; onDetail: (id: string) => void }) { return <div className="table-scroll"><table className="data-table"><thead><tr><th>Fecha</th><th>Archivo</th><th>Usuario</th><th>Estado</th><th>Total</th><th>Válidas</th><th>Errores</th><th>Importadas</th><th /></tr></thead><tbody>{lots.map((lote) => <tr key={lote.id_lote}><td>{formatDate(lote.fecha_creacion)}</td><td>{lote.nombre_archivo}</td><td>{lote.usuario_id}</td><td>{lote.estado}</td><td>{lote.total_filas}</td><td>{lote.filas_validas}</td><td>{lote.filas_con_error}</td><td>{lote.filas_importadas}</td><td><button type="button" className="secondary" onClick={() => void onDetail(lote.id_lote)}>Ver detalle</button></td></tr>)}</tbody></table></div>; }
function IssuesTable({ issues }: { issues: ErrorLoteAusentismo[] }) { return <div className="table-scroll"><table className="data-table"><thead><tr><th>Fila</th><th>Código de error</th><th>Mensaje</th><th>Datos de fila</th></tr></thead><tbody>{issues.map((issue) => <tr key={issue.id_error}><td>{issue.numero_fila}</td><td>{issue.codigo}</td><td>{issue.mensaje}</td><td>{safeData(issue.datos_fila)}</td></tr>)}</tbody></table></div>; }
function Pagination({ page, total, onChange, label }: { page: number; total: number; onChange: (page: number) => void; label: string }) { const pages = Math.max(1, Math.ceil(total / pageSize)); return total > pageSize ? <div className="pagination-controls"><button type="button" className="secondary" disabled={!page} onClick={() => onChange(page - 1)}>Anterior</button><span>Página {page + 1} de {pages} · {total} {label}</span><button type="button" className="secondary" disabled={page + 1 >= pages} onClick={() => onChange(page + 1)}>Siguiente</button></div> : null; }
