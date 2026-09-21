import { useEffect, useState, type FormEvent } from 'react';
import { canAccess } from '../../api/auth';
import { HttpError } from '../../api/client';
import { analizarCorreos, confirmarImportacionCorreos, crearSeguimientoCorreo, listarCorreos, obtenerCorreo, obtenerHistorialImportacionesCorreos, obtenerResumenCorreos, type AnalisisCorreos, type CorreoDetalle, type CorreoResumen, type EstadoRequerimiento, type LoteCorreo, type ResumenCorreos, type SeguimientoCorreo } from '../../api/correos';
import { useAuth } from '../../app/AuthContext';
import { useFeedback } from '../../components/FeedbackProvider';
import { Modal } from '../../components/Modal';

const ESTADOS: readonly EstadoRequerimiento[] = ['PENDIENTE', 'EN_PROCESO', 'EN_ESPERA', 'RESUELTO', 'CERRADO'];
const MAX_XLSX_BYTES = 50 * 1024 * 1024;
const errorText = (error: unknown, fallback: string) => error instanceof HttpError ? error.message : fallback;
const dateText = (value: string | null) => value ? new Date(value).toLocaleString('es-EC') : 'Sin fecha';
const stateText = (value: string) => value.replaceAll('_', ' ');

type DetailState = { correo: CorreoDetalle; seguimientos: SeguimientoCorreo[] };

export function CorreosDashboardPage() {
  return <CorreosDashboardContent />;
}

function CorreosDashboardContent() {
  const { usuario } = useAuth();
  const { notify } = useFeedback();
  const [summary, setSummary] = useState<ResumenCorreos | null>(null);
  const [items, setItems] = useState<CorreoResumen[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<AnalisisCorreos | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [askUnclassified, setAskUnclassified] = useState(false);
  const [detail, setDetail] = useState<DetailState | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [savingFollowUp, setSavingFollowUp] = useState(false);
  const [stateFilter, setStateFilter] = useState('');
  const [textFilter, setTextFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [history, setHistory] = useState<LoteCorreo[]>([]);
  const canViewBody = canAccess(usuario, 'CORREOS', 'sensitive');
  const canImport = canAccess(usuario, 'IMPORTACION', 'create') && canAccess(usuario, 'CORREOS', 'create');

  async function load() {
    setLoading(true); setError(null);
    try {
      const params = new URLSearchParams({ limite: '50', offset: String(offset) });
      if (stateFilter) params.set('estado', stateFilter);
      if (textFilter.trim()) params.set('texto', textFilter.trim());
      if (categoryFilter.trim()) params.set('categoria', categoryFilter.trim());
      const [nextSummary, page, importHistory] = await Promise.all([obtenerResumenCorreos(), listarCorreos(params), canImport ? obtenerHistorialImportacionesCorreos() : Promise.resolve({ items: [] })]);
      setSummary(nextSummary); setItems(page.items); setTotal(page.total); setHistory(importHistory.items);
    } catch (caught) {
      setError(errorText(caught, 'No fue posible cargar el tablero de correos.'));
    } finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, [stateFilter, textFilter, categoryFilter, offset]);

  async function analyze() {
    if (!file || analyzing) return;
    if (!file.name.toLowerCase().endsWith('.xlsx')) { setError('Seleccione un archivo con extensión .xlsx.'); return; }
    if (file.size > MAX_XLSX_BYTES) { setError('El archivo supera el límite de 50 MB para esta importación.'); return; }
    setAnalyzing(true); setError(null); setAnalysis(null);
    try {
      const result = await analizarCorreos(file);
      setAnalysis(result);
      if (result.lote.filas_revision > 0) setAskUnclassified(true);
    } catch (caught) { setError(errorText(caught, 'No fue posible analizar el XLSX.')); }
    finally { setAnalyzing(false); }
  }

  async function confirmImport(includeUnclassified: boolean) {
    if (!analysis || confirming) return;
    setConfirming(true); setAskUnclassified(false); setError(null);
    try {
      const result = await confirmarImportacionCorreos(analysis.lote.id_lote, includeUnclassified);
      notify(`Se procesaron ${result.filas_seleccionadas} correos; ${result.filas_importadas} se incorporaron y ${result.filas_duplicadas} ya existían.`);
      setAnalysis(null); setFile(null); await load();
    } catch (caught) { setError(errorText(caught, 'No fue posible confirmar la carga.')); }
    finally { setConfirming(false); }
  }

  async function openDetail(id: string) {
    if (!canViewBody) { setError('No tiene permiso para visualizar el cuerpo de los correos.'); return; }
    setDetail(null); setDetailError(null); setDetailLoading(true);
    try { setDetail(await obtenerCorreo(id)); }
    catch (caught) { setDetailError(errorText(caught, 'No fue posible cargar el detalle del correo.')); }
    finally { setDetailLoading(false); }
  }

  async function saveFollowUp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!detail || savingFollowUp) return;
    const data = new FormData(event.currentTarget);
    setSavingFollowUp(true); setDetailError(null);
    try {
      const result = await crearSeguimientoCorreo(detail.correo.id_correo, {
        expected_version: detail.correo.version,
        detalle_seguimiento: String(data.get('detalle_seguimiento') ?? ''),
        seguimiento_por: String(data.get('seguimiento_por') ?? '') || undefined,
        estado_requerimiento: String(data.get('estado_requerimiento')) as EstadoRequerimiento,
      });
      setDetail((current) => current ? { correo: { ...current.correo, ...result.correo }, seguimientos: [result.seguimiento, ...current.seguimientos] } : current);
      event.currentTarget.reset(); notify('Seguimiento registrado.'); await load();
    } catch (caught) { setDetailError(errorText(caught, 'No fue posible guardar el seguimiento.')); }
    finally { setSavingFollowUp(false); }
  }

  return <section className="correos-page module-operational-page">
    <header className="module-page-hero correos-hero"><div><p className="eyebrow">Trabajo Social · Bandeja operativa</p><h2>Correos y seguimiento</h2><p>Importe, consulte y dé seguimiento a correos persistidos de forma trazable.</p></div></header>
    {error && <p className="form-error" role="alert">{error}</p>}
    <section className="correos-kpis" aria-label="Resumen de correos">
      {[
        ['Correos en tablero', summary?.total ?? 0, 'info'], ['Pendientes', summary?.pendientes ?? 0, 'warning'],
        ['En seguimiento', summary?.en_seguimiento ?? 0, 'violet'], ['Sin clasificar', summary?.sin_clasificar ?? 0, 'danger'],
      ].map(([label, value, tone]) => <article className={`dashboard-kpi-card kpi-card--${tone}`} key={String(label)}><div className="dashboard-kpi-top"><span className="dashboard-kpi-icon" aria-hidden="true">✉</span><span className="dashboard-kpi-label">{label}</span></div><strong className="dashboard-kpi-value">{value}</strong></article>)}
    </section>
    {canImport && <section className="panel correos-upload-card"><div><h3>Cargar XLSX</h3><p className="footnote">Límite: 50 MB. Las filas inválidas se informan por separado; podrá incluir o excluir las que requieren revisión.</p></div><div className="upload-form"><label>Archivo XLSX<input aria-label="Seleccionar archivo XLSX de correos" type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" onChange={(event) => { setFile(event.target.files?.[0] ?? null); setAnalysis(null); }} /></label><button type="button" disabled={!file || analyzing} onClick={() => void analyze()}>{analyzing ? 'Analizando archivo…' : 'Analizar archivo'}</button></div>{file && <p className="selected-file">Archivo seleccionado: <strong>{file.name}</strong></p>}{analysis && <AnalysisPanel analysis={analysis} confirming={confirming} onConfirm={() => analysis.lote.filas_revision ? setAskUnclassified(true) : void confirmImport(false)} />}</section>}
    <section className="panel module-table-card correos-table-card"><div className="module-table-card-heading"><div><h3>Correos ({total})</h3><p>Los filtros y la paginación se resuelven en el servidor. El cuerpo se consulta sólo en el detalle.</p></div><div className="upload-form"><label>Buscar<input aria-label="Buscar correos" value={textFilter} onChange={(event) => { setOffset(0); setTextFilter(event.target.value); }} /></label><label>Categoría<input aria-label="Filtrar por categoría" value={categoryFilter} onChange={(event) => { setOffset(0); setCategoryFilter(event.target.value); }} /></label><label className="correos-state-filter">Estado<select aria-label="Filtrar por estado de requerimiento" value={stateFilter} onChange={(event) => { setOffset(0); setStateFilter(event.target.value); }}><option value="">Todos</option>{ESTADOS.map((state) => <option value={state} key={state}>{stateText(state)}</option>)}</select></label></div></div>{loading ? <p className="loading-message">Cargando correos…</p> : items.length ? <><div className="table-scroll"><table className="data-table module-data-table"><thead><tr><th>Recibido</th><th>Remitente</th><th>Asunto</th><th>Categoría</th><th>Origen</th><th>Estado</th><th /></tr></thead><tbody>{items.map((item) => <tr key={item.id_correo}><td>{dateText(item.fecha_recibido)}</td><td>{item.remitente ?? 'Sin remitente'}</td><td>{item.asunto || 'Sin asunto'}</td><td><span className="correo-category">{item.categoria_nombre ?? item.categoria_macro ?? item.estado_categoria}</span></td><td>{item.origen ?? 'Sin información'}</td><td><span className={`correo-status correo-status--${item.estado_requerimiento.toLowerCase()}`}>{stateText(item.estado_requerimiento)}</span></td><td><button type="button" className="secondary" disabled={!canViewBody} title={canViewBody ? 'Ver detalle' : 'Requiere permiso sensible de CORREOS'} onClick={() => void openDetail(item.id_correo)}>Ver detalle</button></td></tr>)}</tbody></table></div><div className="modal-actions"><button type="button" className="secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 50))}>Anterior</button><span className="footnote">{offset + 1}–{Math.min(offset + items.length, total)} de {total}</span><button type="button" disabled={offset + items.length >= total} onClick={() => setOffset(offset + 50)}>Siguiente</button></div></> : <div className="module-empty-state"><span aria-hidden="true">✉</span><div><strong>No hay correos para estos filtros.</strong><p>Analice un XLSX o ajuste los filtros de consulta.</p></div></div>}</section>
    {canImport && history.length > 0 && <section className="panel module-table-card"><h3>Historial de importaciones</h3><div className="table-scroll"><table className="data-table"><thead><tr><th>Archivo</th><th>Fecha</th><th>Procesadas</th><th>Importadas</th><th>Duplicadas</th><th>Errores</th></tr></thead><tbody>{history.map((lot) => <tr key={lot.id_lote}><td>{lot.nombre_archivo}</td><td>{dateText(lot.fecha_creacion)}</td><td>{lot.filas_procesadas}</td><td>{lot.filas_importadas}</td><td>{lot.filas_duplicadas}</td><td>{lot.filas_error}</td></tr>)}</tbody></table></div></section>}
    {(detailLoading || detail || detailError) && <Modal titulo="Detalle del correo" onClose={() => { if (!detailLoading) { setDetail(null); setDetailError(null); } }} size="large" closeOnBackdrop={!detailLoading}>{detailLoading ? <p className="loading-message">Cargando detalle…</p> : detailError ? <p className="form-error" role="alert">{detailError}</p> : detail && <EmailDetail data={detail} saving={savingFollowUp} onSave={saveFollowUp} />}</Modal>}
    {askUnclassified && analysis && <Modal titulo="Correos sin clasificar" onClose={() => setAskUnclassified(false)} size="small"><p className="dialog-message">El archivo contiene {analysis.lote.filas_revision} correos sin categoría válida y {analysis.lote.filas_error} filas con error. Las filas con error quedan trazadas y no se cargarán.</p><div className="modal-actions"><button type="button" className="secondary" disabled={confirming} onClick={() => void confirmImport(false)}>Solo clasificados</button><button type="button" disabled={confirming} onClick={() => void confirmImport(true)}>{confirming ? 'Cargando…' : 'Incluir revisión'}</button></div></Modal>}
  </section>;
}

function AnalysisPanel({ analysis, confirming, onConfirm }: { analysis: AnalisisCorreos; confirming: boolean; onConfirm: () => void }) {
  return <div className="correos-analysis"><div className="summary-grid">{[['Total', analysis.lote.total_filas], ['Válidas', analysis.lote.filas_clasificadas], ['En revisión', analysis.lote.filas_revision], ['Errores', analysis.lote.filas_error], ['Vista previa', analysis.ultimos_100.length]].map(([label, value]) => <article className="kpi-card" key={String(label)}><span className="kpi-label">{label}</span><strong className="kpi-value">{value}</strong></article>)}</div><button type="button" disabled={confirming} onClick={onConfirm}>{confirming ? 'Cargando…' : 'Confirmar importación'}</button><p className="footnote">La vista previa muestra como máximo 100 registros por fecha; la confirmación procesa todas las filas aptas.</p><div className="table-scroll correos-preview"><table className="data-table"><thead><tr><th>Recibido</th><th>Remitente</th><th>Asunto</th><th>Clasificación</th></tr></thead><tbody>{analysis.ultimos_100.map((item) => <tr key={item.id_externo_correo}><td>{dateText(item.fecha_recibido)}</td><td>{item.remitente ?? 'Sin remitente'}</td><td>{item.asunto || 'Sin asunto'}</td><td>{item.categoria_nombre ?? item.categoria_macro ?? item.estado_categoria}</td></tr>)}</tbody></table></div></div>;
}

function EmailDetail({ data, saving, onSave }: { data: DetailState; saving: boolean; onSave: (event: FormEvent<HTMLFormElement>) => void }) {
  const { correo, seguimientos } = data;
  return <div className="correo-detail"><dl className="field-list"><div><dt>Remitente</dt><dd>{correo.remitente ?? 'Sin remitente'}</dd></div><div><dt>Recibido</dt><dd>{dateText(correo.fecha_recibido)}</dd></div><div><dt>Destinatarios</dt><dd>{correo.destinatarios ?? 'Sin información'}</dd></div><div><dt>CC</dt><dd>{correo.cc ?? 'Sin información'}</dd></div><div><dt>MessageId</dt><dd>{correo.id_externo_correo}</dd></div><div><dt>Importancia</dt><dd>{correo.importancia ?? 'Sin información'}</dd></div><div><dt>Categoría</dt><dd>{correo.categoria_nombre ?? correo.categoria_macro ?? correo.estado_categoria}</dd></div><div><dt>Origen</dt><dd>{correo.origen ?? 'Sin información'}</dd></div><div><dt>Estado</dt><dd>{stateText(correo.estado_requerimiento)}</dd></div></dl><section className="correo-body"><h3>{correo.asunto || 'Sin asunto'}</h3><pre>{correo.cuerpo || 'El correo no contiene cuerpo.'}</pre></section><section className="correo-follow-ups"><h3>Seguimientos</h3>{seguimientos.length ? <ul>{seguimientos.map((item) => <li key={item.id_seguimiento}><strong>{stateText(item.estado_requerimiento)}</strong><span>{item.detalle_seguimiento}</span><small>{item.seguimiento_por ?? 'Sin responsable'} · {dateText(item.fecha_seguimiento)}</small></li>)}</ul> : <p className="footnote">Aún no hay seguimientos registrados.</p>}<form className="form-grid" onSubmit={onSave}><label className="full-width">Detalle del seguimiento<textarea name="detalle_seguimiento" required /></label><label>Responsable<input name="seguimiento_por" defaultValue={correo.responsable_seguimiento ?? ''} /></label><label>Estado<select name="estado_requerimiento" defaultValue={correo.estado_requerimiento}>{ESTADOS.map((state) => <option key={state} value={state}>{stateText(state)}</option>)}</select></label><div className="modal-actions full-width"><button type="submit" disabled={saving}>{saving ? 'Guardando…' : 'Registrar seguimiento'}</button></div></form></section></div>;
}
