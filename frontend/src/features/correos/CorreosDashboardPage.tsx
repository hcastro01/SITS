import { useEffect, useState, type FormEvent } from 'react';
import { canAccess } from '../../api/auth';
import { HttpError } from '../../api/client';
import { analizarCorreos, confirmarImportacionCorreos, crearSeguimientoCorreo, exportarCorreos, listarCorreos, obtenerCorreo, obtenerErroresImportacionCorreos, obtenerHistorialImportacionesCorreos, obtenerResumenCorreos, type AnalisisCorreos, type CorreoDetalle, type CorreoResumen, type ErrorImportacionCorreo, type EstadoRequerimiento, type LoteCorreo, type ResumenCorreos, type SeguimientoCorreo } from '../../api/correos';
import { useAuth } from '../../app/AuthContext';
import { useFeedback } from '../../components/FeedbackProvider';
import { Modal } from '../../components/Modal';

const ESTADOS: readonly EstadoRequerimiento[] = ['PENDIENTE', 'EN_PROCESO', 'EN_ESPERA', 'RESUELTO', 'CERRADO'];
const MAX_XLSX_BYTES = 50 * 1024 * 1024;
const errorText = (error: unknown, fallback: string) => error instanceof HttpError ? error.message : fallback;
const exportErrorText = (error: unknown) => error instanceof HttpError && error.status === 405
  ? 'La exportación no está disponible en el servidor actual. Actualice el backend e inténtelo de nuevo.'
  : errorText(error, 'No fue posible preparar el archivo de Excel.');
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
  const [pendingConfirmation, setPendingConfirmation] = useState<LoteCorreo | null>(null);
  const [detail, setDetail] = useState<DetailState | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [savingFollowUp, setSavingFollowUp] = useState(false);
  const [stateFilter, setStateFilter] = useState('');
  const [textFilter, setTextFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [subjectFilter, setSubjectFilter] = useState('');
  const [senderFilter, setSenderFilter] = useState('');
  const [recipientFilter, setRecipientFilter] = useState('');
  const [originFilter, setOriginFilter] = useState('');
  const [importanceFilter, setImportanceFilter] = useState('');
  const [messageIdFilter, setMessageIdFilter] = useState('');
  const [dateFromFilter, setDateFromFilter] = useState('');
  const [dateToFilter, setDateToFilter] = useState('');
  const [attachmentsFilter, setAttachmentsFilter] = useState('');
  const [orderFilter, setOrderFilter] = useState('');
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [history, setHistory] = useState<LoteCorreo[]>([]);
  const [errorLot, setErrorLot] = useState<LoteCorreo | null>(null);
  const [lotErrors, setLotErrors] = useState<ErrorImportacionCorreo[]>([]);
  const [lotErrorsLoading, setLotErrorsLoading] = useState(false);
  const [lotErrorsError, setLotErrorsError] = useState<string | null>(null);
  const canViewBody = canAccess(usuario, 'CORREOS', 'sensitive');
  const canExport = canAccess(usuario, 'CORREOS', 'read') && canAccess(usuario, 'CORREOS', 'export');
  const canImport = canAccess(usuario, 'IMPORTACION', 'create') && canAccess(usuario, 'CORREOS', 'create');
  const [exportOpen, setExportOpen] = useState(false);
  const [exportScope, setExportScope] = useState<'filtered' | 'all'>('filtered');
  const [includeBody, setIncludeBody] = useState(false);
  const [includeFollowUps, setIncludeFollowUps] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportReady, setExportReady] = useState(false);

  async function load() {
    setLoading(true); setError(null);
    try {
      const params = new URLSearchParams({ limite: '50', offset: String(offset) });
      if (stateFilter) params.set('estado', stateFilter);
      if (textFilter.trim()) params.set('texto', textFilter.trim());
      if (categoryFilter.trim()) params.set('categoria', categoryFilter.trim());
      if (subjectFilter.trim()) params.set('asunto', subjectFilter.trim());
      if (senderFilter.trim()) params.set('remitente', senderFilter.trim());
      if (recipientFilter.trim()) params.set('destinatario', recipientFilter.trim());
      if (originFilter.trim()) params.set('origen', originFilter.trim());
      if (importanceFilter.trim()) params.set('importancia', importanceFilter.trim());
      if (messageIdFilter.trim()) params.set('message_id', messageIdFilter.trim());
      if (dateFromFilter) params.set('fecha_desde', dateFromFilter);
      if (dateToFilter) params.set('fecha_hasta', dateToFilter);
      if (attachmentsFilter) params.set('tiene_adjuntos', attachmentsFilter);
      if (orderFilter) params.set('orden', orderFilter);
      const [nextSummary, page, importHistory] = await Promise.all([obtenerResumenCorreos(), listarCorreos(params), canImport ? obtenerHistorialImportacionesCorreos() : Promise.resolve({ items: [] })]);
      setSummary(nextSummary); setItems(page.items); setTotal(page.total); setHistory(importHistory.items);
    } catch (caught) {
      setError(errorText(caught, 'No fue posible cargar el tablero de correos.'));
    } finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, [stateFilter, textFilter, categoryFilter, subjectFilter, senderFilter, recipientFilter, originFilter, importanceFilter, messageIdFilter, dateFromFilter, dateToFilter, attachmentsFilter, orderFilter, offset]);

  async function analyze() {
    if (!file || analyzing) return;
    if (!file.name.toLowerCase().endsWith('.xlsx')) { setError('Seleccione un archivo con extensión .xlsx.'); return; }
    if (file.size > MAX_XLSX_BYTES) { setError('El archivo supera el límite de 50 MB para esta importación.'); return; }
    setAnalyzing(true); setError(null); setAnalysis(null);
    try {
      const result = await analizarCorreos(file);
      setAnalysis(result);
    } catch (caught) { setError(errorText(caught, 'No fue posible analizar el XLSX.')); }
    finally { setAnalyzing(false); }
  }

  function requestConfirmation(lot: LoteCorreo) {
    setPendingConfirmation(lot);
    if (lot.filas_revision > 0) setAskUnclassified(true);
    else void confirmImport(lot, false);
  }

  async function confirmImport(lot: LoteCorreo, includeUnclassified: boolean) {
    if (confirming) return;
    setConfirming(true); setAskUnclassified(false); setError(null);
    try {
      const result = await confirmarImportacionCorreos(lot.id_lote, includeUnclassified);
      notify(`Se procesaron ${result.filas_seleccionadas} correos; ${result.filas_importadas} se incorporaron y ${result.filas_duplicadas} ya existían.`);
      setAnalysis(null); setFile(null); setPendingConfirmation(null); await load();
    } catch (caught) { setError(errorText(caught, 'No fue posible confirmar la carga.')); }
    finally { setConfirming(false); }
  }

  async function openLotErrors(lot: LoteCorreo) {
    setErrorLot(lot); setLotErrors([]); setLotErrorsError(null); setLotErrorsLoading(true);
    try { setLotErrors((await obtenerErroresImportacionCorreos(lot.id_lote)).items); }
    catch (caught) { setLotErrorsError(errorText(caught, 'No fue posible consultar los errores del lote.')); }
    finally { setLotErrorsLoading(false); }
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
    const form = event.currentTarget;
    const data = new FormData(form);
    setSavingFollowUp(true); setDetailError(null);
    try {
      const result = await crearSeguimientoCorreo(detail.correo.id_correo, {
        expected_version: detail.correo.version,
        detalle_seguimiento: String(data.get('detalle_seguimiento') ?? ''),
        seguimiento_por: String(data.get('seguimiento_por') ?? '') || undefined,
        estado_requerimiento: String(data.get('estado_requerimiento')) as EstadoRequerimiento,
      });
      setDetail((current) => current ? { correo: { ...current.correo, ...result.correo }, seguimientos: [result.seguimiento, ...current.seguimientos] } : current);
      form.reset(); notify('Seguimiento registrado.'); await load();
    } catch (caught) { setDetailError(errorText(caught, 'No fue posible guardar el seguimiento.')); }
    finally { setSavingFollowUp(false); }
  }

  function currentFilters() {
    const filters: Record<string, string | boolean> = {};
    if (stateFilter) filters.estado = stateFilter;
    if (textFilter.trim()) filters.texto = textFilter.trim();
    if (categoryFilter.trim()) filters.categoria = categoryFilter.trim();
    if (subjectFilter.trim()) filters.asunto = subjectFilter.trim();
    if (senderFilter.trim()) filters.remitente = senderFilter.trim();
    if (recipientFilter.trim()) filters.destinatario = recipientFilter.trim();
    if (originFilter.trim()) filters.origen = originFilter.trim();
    if (importanceFilter.trim()) filters.importancia = importanceFilter.trim();
    if (messageIdFilter.trim()) filters.message_id = messageIdFilter.trim();
    if (dateFromFilter) filters.fecha_desde = dateFromFilter;
    if (dateToFilter) filters.fecha_hasta = dateToFilter;
    if (attachmentsFilter) filters.tiene_adjuntos = attachmentsFilter === 'true';
    if (orderFilter) filters.orden = orderFilter;
    return filters;
  }

  function openExport() {
    setExportScope(Object.keys(currentFilters()).length ? 'filtered' : 'all');
    setIncludeBody(false); setIncludeFollowUps(false); setExportError(null); setExportReady(false); setExportOpen(true);
  }

  async function downloadExport() {
    if (exporting) return;
    setExporting(true); setExportError(null); setExportReady(false);
    try {
      const result = await exportarCorreos({ alcance: exportScope, filtros: currentFilters(), incluir_cuerpo: includeBody, incluir_seguimientos: includeFollowUps });
      const url = URL.createObjectURL(result.blob);
      const link = document.createElement('a');
      link.href = url; link.download = result.filename || 'SITS_Correos_Categorizados.xlsx';
      document.body.appendChild(link); link.click(); link.remove(); URL.revokeObjectURL(url);
      setExportReady(true);
    } catch (caught) { setExportError(exportErrorText(caught)); }
    finally { setExporting(false); }
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
    {canImport && <section className="panel correos-upload-card"><div><h3>Cargar XLSX</h3><p className="footnote">Límite: 50 MB. Las filas inválidas se informan por separado; podrá incluir o excluir las que requieren revisión.</p></div><div className="upload-form"><label>Archivo XLSX<input aria-label="Seleccionar archivo XLSX de correos" type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" onChange={(event) => { setFile(event.target.files?.[0] ?? null); setAnalysis(null); }} /></label><button type="button" disabled={!file || analyzing} onClick={() => void analyze()}>{analyzing ? 'Analizando archivo…' : 'Analizar archivo'}</button></div>{file && <p className="selected-file">Archivo seleccionado: <strong>{file.name}</strong></p>}{analysis && <AnalysisPanel analysis={analysis} confirming={confirming} onConfirm={() => requestConfirmation(analysis.lote)} />}</section>}
    <section className="panel module-table-card correos-table-card"><div className="module-table-card-heading"><div><h3>Correos ({total})</h3><p>Los filtros y la paginación se resuelven en el servidor. El cuerpo se consulta sólo en el detalle.</p></div><div className="upload-form"><label>Buscar<input aria-label="Buscar correos" value={textFilter} onChange={(event) => { setOffset(0); setTextFilter(event.target.value); }} /></label><label>Asunto<input aria-label="Filtrar por asunto" value={subjectFilter} onChange={(event) => { setOffset(0); setSubjectFilter(event.target.value); }} /></label><label>Remitente<input aria-label="Filtrar por remitente" value={senderFilter} onChange={(event) => { setOffset(0); setSenderFilter(event.target.value); }} /></label><label>Destinatario<input aria-label="Filtrar por destinatario" value={recipientFilter} onChange={(event) => { setOffset(0); setRecipientFilter(event.target.value); }} /></label><label>Categoría<input aria-label="Filtrar por categoría" value={categoryFilter} onChange={(event) => { setOffset(0); setCategoryFilter(event.target.value); }} /></label><label>Origen<input aria-label="Filtrar por origen" value={originFilter} onChange={(event) => { setOffset(0); setOriginFilter(event.target.value); }} /></label><label>Importancia<input aria-label="Filtrar por importancia" value={importanceFilter} onChange={(event) => { setOffset(0); setImportanceFilter(event.target.value); }} /></label><label>MessageId<input aria-label="Filtrar por MessageId" value={messageIdFilter} onChange={(event) => { setOffset(0); setMessageIdFilter(event.target.value); }} /></label><label>Desde<input aria-label="Filtrar desde fecha" type="date" value={dateFromFilter} onChange={(event) => { setOffset(0); setDateFromFilter(event.target.value); }} /></label><label>Hasta<input aria-label="Filtrar hasta fecha" type="date" value={dateToFilter} onChange={(event) => { setOffset(0); setDateToFilter(event.target.value); }} /></label><label>Adjuntos<select aria-label="Filtrar por adjuntos" value={attachmentsFilter} onChange={(event) => { setOffset(0); setAttachmentsFilter(event.target.value); }}><option value="">Todos</option><option value="true">Con adjuntos</option><option value="false">Sin adjuntos</option></select></label><label>Orden<select aria-label="Ordenar correos" value={orderFilter} onChange={(event) => { setOffset(0); setOrderFilter(event.target.value); }}><option value="">Más recientes</option><option value="asunto_asc">Asunto A–Z</option></select></label><label className="correos-state-filter">Estado<select aria-label="Filtrar por estado de requerimiento" value={stateFilter} onChange={(event) => { setOffset(0); setStateFilter(event.target.value); }}><option value="">Todos</option>{ESTADOS.map((state) => <option value={state} key={state}>{stateText(state)}</option>)}</select></label>{canExport && <button type="button" onClick={openExport}>Descargar Excel</button>}</div></div>{loading ? <p className="loading-message">Cargando correos…</p> : items.length ? <><div className="table-scroll"><table className="data-table module-data-table"><thead><tr><th>Recibido</th><th>Remitente</th><th>Asunto</th><th>Categoría</th><th>Origen</th><th>Estado</th><th /></tr></thead><tbody>{items.map((item) => <tr key={item.id_correo}><td>{dateText(item.fecha_recibido)}</td><td>{item.remitente ?? 'Sin remitente'}</td><td>{item.asunto || 'Sin asunto'}</td><td><span className="correo-category">{item.categoria_nombre ?? item.categoria_macro ?? item.estado_categoria}</span></td><td>{item.origen ?? 'Sin información'}</td><td><span className={`correo-status correo-status--${item.estado_requerimiento.toLowerCase()}`}>{stateText(item.estado_requerimiento)}</span></td><td><button type="button" className="secondary" disabled={!canViewBody} title={canViewBody ? 'Ver detalle' : 'Requiere permiso sensible de CORREOS'} onClick={() => void openDetail(item.id_correo)}>Ver detalle</button></td></tr>)}</tbody></table></div><div className="modal-actions"><button type="button" className="secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 50))}>Anterior</button><span className="footnote">{offset + 1}–{Math.min(offset + items.length, total)} de {total}</span><button type="button" disabled={offset + items.length >= total} onClick={() => setOffset(offset + 50)}>Siguiente</button></div></> : <div className="module-empty-state"><span aria-hidden="true">✉</span><div><strong>No hay correos para estos filtros.</strong><p>Analice un XLSX o ajuste los filtros de consulta.</p></div></div>}</section>
    {canImport && history.length > 0 && <section className="panel module-table-card"><h3>Historial de importaciones</h3><p className="footnote">Puede revisar las incidencias trazadas y retomar únicamente los lotes que siguen analizados.</p><div className="table-scroll"><table className="data-table"><thead><tr><th>Archivo</th><th>Fecha</th><th>Estado</th><th>Procesadas</th><th>Importadas</th><th>Duplicadas</th><th>Errores</th><th /></tr></thead><tbody>{history.map((lot) => <tr key={lot.id_lote}><td>{lot.nombre_archivo}</td><td>{dateText(lot.fecha_creacion)}</td><td>{stateText(lot.estado)}</td><td>{lot.filas_procesadas}</td><td>{lot.filas_importadas}</td><td>{lot.filas_duplicadas}</td><td>{lot.filas_error}</td><td><div className="modal-actions"><button type="button" className="secondary" onClick={() => void openLotErrors(lot)}>Ver errores</button>{lot.estado === 'ANALIZADO' && <button type="button" disabled={confirming} onClick={() => requestConfirmation(lot)}>Confirmar lote</button>}</div></td></tr>)}</tbody></table></div></section>}
    {(detailLoading || detail || detailError) && <Modal titulo="Detalle del correo" onClose={() => { if (!detailLoading) { setDetail(null); setDetailError(null); } }} size="large" closeOnBackdrop={!detailLoading}>{detailLoading ? <p className="loading-message">Cargando detalle…</p> : detailError ? <p className="form-error" role="alert">{detailError}</p> : detail && <EmailDetail data={detail} saving={savingFollowUp} onSave={saveFollowUp} />}</Modal>}
    {askUnclassified && pendingConfirmation && <Modal titulo="Correos sin clasificar" onClose={() => setAskUnclassified(false)} size="small"><p className="dialog-message">El archivo contiene {pendingConfirmation.filas_revision} correos sin categoría válida y {pendingConfirmation.filas_error} filas con error. Las filas con error quedan trazadas y no se cargarán.</p><div className="modal-actions"><button type="button" className="secondary" disabled={confirming} onClick={() => void confirmImport(pendingConfirmation, false)}>Solo clasificados</button><button type="button" disabled={confirming} onClick={() => void confirmImport(pendingConfirmation, true)}>{confirming ? 'Cargando…' : 'Incluir revisión'}</button></div></Modal>}
    {errorLot && <Modal titulo={`Errores de ${errorLot.nombre_archivo}`} onClose={() => { if (!lotErrorsLoading) setErrorLot(null); }} size="large" closeOnBackdrop={!lotErrorsLoading}>{lotErrorsLoading ? <p className="loading-message">Cargando errores…</p> : lotErrorsError ? <p className="form-error" role="alert">{lotErrorsError}</p> : lotErrors.length ? <div className="table-scroll"><table className="data-table"><thead><tr><th>Fila</th><th>MessageId</th><th>Código</th><th>Detalle</th></tr></thead><tbody>{lotErrors.map((item, index) => <tr key={`${item.fila ?? 'sin-fila'}-${item.codigo}-${index}`}><td>{item.fila ?? 'Sin fila'}</td><td>{item.message_id ?? 'Sin MessageId'}</td><td>{item.codigo}</td><td>{item.detalle}</td></tr>)}</tbody></table></div> : <p className="footnote">No hay errores persistidos para este lote.</p>}</Modal>}
    {exportOpen && <Modal titulo="Descargar Excel" onClose={() => { if (!exporting) setExportOpen(false); }} size="small" closeOnBackdrop={!exporting}><p className="dialog-message">{exportScope === 'filtered' ? `Se exportarán los resultados de los filtros actuales (${total} estimados según el listado).` : 'Se exportarán todos los correos autorizados. Esta opción ignora los filtros de búsqueda, pero mantiene los permisos.'}</p><label><input type="radio" name="export-scope" checked={exportScope === 'filtered'} onChange={() => setExportScope('filtered')} /> Descargar resultados filtrados</label><label><input type="radio" name="export-scope" checked={exportScope === 'all'} onChange={() => setExportScope('all')} /> Descargar todos los correos autorizados</label>{canViewBody && <><label><input type="checkbox" checked={includeBody} onChange={(event) => setIncludeBody(event.target.checked)} /> Incluir cuerpo completo del correo</label><label><input type="checkbox" checked={includeFollowUps} onChange={(event) => setIncludeFollowUps(event.target.checked)} /> Incluir historial de seguimientos</label></>}<p className="footnote">La categorización completa siempre se incluye. La cantidad final se confirma al preparar el archivo.</p>{exportError && <p className="form-error" role="alert">{exportError}</p>}{exportReady && <p className="success-message" role="status">El archivo está preparado y la descarga se inició. El navegador confirma el inicio, no el guardado local.</p>}<div className="modal-actions"><button type="button" className="secondary" disabled={exporting} onClick={() => setExportOpen(false)}>Cancelar</button><button type="button" disabled={exporting} onClick={() => void downloadExport()}>{exporting ? 'Preparando archivo…' : 'Descargar Excel'}</button></div></Modal>}
  </section>;
}

function AnalysisPanel({ analysis, confirming, onConfirm }: { analysis: AnalisisCorreos; confirming: boolean; onConfirm: () => void }) {
  return <div className="correos-analysis"><div className="summary-grid">{[['Total', analysis.lote.total_filas], ['Válidas', analysis.lote.filas_clasificadas], ['En revisión', analysis.lote.filas_revision], ['Errores', analysis.lote.filas_error], ['Vista previa', analysis.ultimos_100.length]].map(([label, value]) => <article className="kpi-card" key={String(label)}><span className="kpi-label">{label}</span><strong className="kpi-value">{value}</strong></article>)}</div><button type="button" disabled={confirming} onClick={onConfirm}>{confirming ? 'Cargando…' : 'Confirmar importación'}</button><p className="footnote">La vista previa muestra como máximo 100 registros por fecha; la confirmación procesa todas las filas aptas.</p><div className="table-scroll correos-preview"><table className="data-table"><thead><tr><th>Recibido</th><th>Remitente</th><th>Asunto</th><th>Clasificación</th></tr></thead><tbody>{analysis.ultimos_100.map((item) => <tr key={item.id_externo_correo}><td>{dateText(item.fecha_recibido)}</td><td>{item.remitente ?? 'Sin remitente'}</td><td>{item.asunto || 'Sin asunto'}</td><td>{item.categoria_nombre ?? item.categoria_macro ?? item.estado_categoria}</td></tr>)}</tbody></table></div></div>;
}

function EmailDetail({ data, saving, onSave }: { data: DetailState; saving: boolean; onSave: (event: FormEvent<HTMLFormElement>) => void }) {
  const { correo, seguimientos } = data;
  return <div className="correo-detail"><dl className="field-list"><div><dt>Remitente</dt><dd>{correo.remitente ?? 'Sin remitente'}</dd></div><div><dt>Recibido</dt><dd>{dateText(correo.fecha_recibido)}</dd></div><div><dt>Destinatarios</dt><dd>{correo.destinatarios ?? 'Sin información'}</dd></div><div><dt>CC</dt><dd>{correo.cc ?? 'Sin información'}</dd></div><div><dt>MessageId</dt><dd>{correo.id_externo_correo}</dd></div><div><dt>Importancia</dt><dd>{correo.importancia ?? 'Sin información'}</dd></div><div><dt>Categoría</dt><dd>{correo.categoria_nombre ?? correo.categoria_macro ?? correo.estado_categoria}</dd></div><div><dt>Origen</dt><dd>{correo.origen ?? 'Sin información'}</dd></div><div><dt>Estado</dt><dd>{stateText(correo.estado_requerimiento)}</dd></div></dl><section className="correo-body"><h3>{correo.asunto || 'Sin asunto'}</h3><pre>{correo.cuerpo || 'El correo no contiene cuerpo.'}</pre></section><section className="correo-follow-ups"><h3>Seguimientos</h3>{seguimientos.length ? <ul>{seguimientos.map((item) => <li key={item.id_seguimiento}><strong>{stateText(item.estado_requerimiento)}</strong><span>{item.detalle_seguimiento}</span><small>{item.seguimiento_por ?? 'Sin responsable'} · {dateText(item.fecha_seguimiento)}</small></li>)}</ul> : <p className="footnote">Aún no hay seguimientos registrados.</p>}<form className="form-grid" onSubmit={onSave}><label className="full-width">Detalle del seguimiento<textarea name="detalle_seguimiento" required /></label><label>Responsable<input name="seguimiento_por" defaultValue={correo.responsable_seguimiento ?? ''} /></label><label>Estado<select name="estado_requerimiento" defaultValue={correo.estado_requerimiento}>{ESTADOS.map((state) => <option key={state} value={state}>{stateText(state)}</option>)}</select></label><div className="modal-actions full-width"><button type="submit" disabled={saving}>{saving ? 'Guardando…' : 'Registrar seguimiento'}</button></div></form></section></div>;
}
