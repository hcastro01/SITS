import { useEffect, useState, type FormEvent } from 'react';
import { HttpError } from '../../api/client';
import { canAccess } from '../../api/auth';
import { actualizarRiesgo, cerrarRiesgo, crearRiesgo, listarRiesgos, obtenerRiesgo, type RiesgoCreate, type RiesgoEstado, type RiesgoTrabajo, type RiesgoUpdate } from '../../api/riesgosTrabajo';
import { useAuth } from '../../app/AuthContext';
import { Modal } from '../../components/Modal';
import { useFeedback } from '../../components/FeedbackProvider';
import { SearchAutocompleteField } from '../formularios/SearchAutocompleteField';
import type { SearchResult } from '../../api/formBuilder';

const pageSize = 25;
const today = () => new Date().toISOString().slice(0, 10);
const blankCreate = (): RiesgoCreate => ({ persona_id: '', fecha_apertura: today(), responsable: '', estado_caso: 'ABIERTO', prioridad: '', resultado: '' });
const visible = (value: string | null | undefined) => value || '—';

function message(error: unknown, fallback: string) {
  return error instanceof HttpError ? error.message : fallback;
}

export function RiesgosTrabajoPage() {
  const { usuario } = useAuth();
  const { notify } = useFeedback();
  const [items, setItems] = useState<RiesgoTrabajo[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({ nombre: '', cedula: '', area: '', estado: '', responsable: '', desde: '', hasta: '' });
  const [draftFilters, setDraftFilters] = useState(filters);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<RiesgoTrabajo | null>(null);
  const [detail, setDetail] = useState<RiesgoTrabajo | null>(null);
  const [closing, setClosing] = useState<RiesgoTrabajo | null>(null);

  const canCreate = canAccess(usuario, 'RIESGOS_TRABAJO', 'create');
  const canEdit = canAccess(usuario, 'RIESGOS_TRABAJO', 'edit');

  async function load(targetPage = page, activeFilters = filters) {
    setLoading(true); setError(null);
    try {
      const params = new URLSearchParams({ limite: String(pageSize), offset: String(targetPage * pageSize) });
      Object.entries(activeFilters).forEach(([key, value]) => { if (value) params.set(key, value); });
      const response = await listarRiesgos(params);
      setItems(response.items); setTotal(response.total);
    } catch (caught) {
      setItems([]); setTotal(0); setError(message(caught, 'No fue posible cargar los Riesgos de trabajo.'));
    } finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, [page, filters]);

  function applyFilters(event: FormEvent) {
    event.preventDefault(); setPage(0); setFilters({ ...draftFilters });
  }

  function clearFilters() {
    const empty = { nombre: '', cedula: '', area: '', estado: '', responsable: '', desde: '', hasta: '' };
    setDraftFilters(empty); setPage(0); setFilters({ ...empty });
  }

  async function openDetail(item: RiesgoTrabajo) {
    try { setDetail(await obtenerRiesgo(item.id_caso)); }
    catch (caught) { setError(message(caught, 'No fue posible obtener el detalle del Riesgo.')); }
  }

  async function saveCreated(payload: RiesgoCreate) {
    const saved = await crearRiesgo(payload);
    setCreating(false); setPage(0); await load(0); notify(`Riesgo ${saved.codigo_caso} registrado correctamente.`);
  }

  async function saveEdited(item: RiesgoTrabajo, payload: RiesgoUpdate) {
    const saved = await actualizarRiesgo(item.id_caso, payload);
    setEditing(null); setItems((current) => current.map((entry) => entry.id_caso === saved.id_caso ? saved : entry));
    if (detail?.id_caso === saved.id_caso) setDetail(saved);
    notify('Riesgo actualizado correctamente.');
  }

  async function saveClosed(item: RiesgoTrabajo, payload: { expected_version: number; fecha_cierre_caso?: string; responsable?: string; motivo_cierre: string; resultado_final?: string }) {
    await cerrarRiesgo(item.id_caso, payload);
    setClosing(null); await load(); notify('Riesgo cerrado correctamente.');
  }

  return <section className="panel wide-panel riesgos-trabajo-page">
    <div className="panel-header"><div><p className="eyebrow">Trabajo Social · Departamento Médico</p><h2>Riesgos de trabajo</h2><p>Registro y seguimiento operativo de Riesgos de trabajo.</p></div>{canCreate && <button type="button" onClick={() => setCreating(true)}>Registrar Riesgo</button>}</div>
    {error && <p className="form-error" role="alert">{error}</p>}
    <form className="record-filters" onSubmit={applyFilters} aria-label="Filtros de Riesgos de trabajo">
      <label>Nombre de Persona<input aria-label="Filtrar por nombre" value={draftFilters.nombre} onChange={(e) => setDraftFilters({ ...draftFilters, nombre: e.target.value })} /></label>
      <label>Cédula<input aria-label="Filtrar por cédula" value={draftFilters.cedula} onChange={(e) => setDraftFilters({ ...draftFilters, cedula: e.target.value })} /></label>
      <label>Área<input aria-label="Filtrar por área" value={draftFilters.area} onChange={(e) => setDraftFilters({ ...draftFilters, area: e.target.value })} /></label>
      <label>Estado<select aria-label="Filtrar por estado" value={draftFilters.estado} onChange={(e) => setDraftFilters({ ...draftFilters, estado: e.target.value })}><option value="">Todos</option><option value="ABIERTO">Abierto</option><option value="EN_SEGUIMIENTO">En seguimiento</option><option value="CERRADO">Cerrado</option></select></label>
      <label>Responsable<input aria-label="Filtrar por responsable" value={draftFilters.responsable} onChange={(e) => setDraftFilters({ ...draftFilters, responsable: e.target.value })} /></label>
      <label>Desde<input aria-label="Fecha desde" type="date" value={draftFilters.desde} onChange={(e) => setDraftFilters({ ...draftFilters, desde: e.target.value })} /></label>
      <label>Hasta<input aria-label="Fecha hasta" type="date" value={draftFilters.hasta} onChange={(e) => setDraftFilters({ ...draftFilters, hasta: e.target.value })} /></label>
      <div className="button-row"><button type="submit">Aplicar filtros</button><button type="button" className="secondary" onClick={clearFilters}>Limpiar filtros</button></div>
    </form>
    {loading ? <p className="loading-message" role="status">Cargando Riesgos de trabajo…</p> : items.length === 0 ? <p className="empty-state">No existen Riesgos de trabajo para los filtros seleccionados.</p> : <div className="table-scroll"><table className="data-table"><thead><tr><th>Código</th><th>Fecha</th><th>Persona</th><th>Estado</th><th>Responsable</th><th>Actualización</th><th>Acciones</th></tr></thead><tbody>{items.map((item) => <tr key={item.id_caso}><td>{item.codigo_caso}<small>{item.id_caso}</small></td><td>{visible(item.fecha_apertura)}</td><td>{visible(item.persona)}<small>{visible(item.cedula)} · {visible(item.area)}</small><small>{visible(item.resumen)}</small></td><td>{item.estado_caso}</td><td>{visible(item.responsable)}<small>Por: {visible(item.registrado_por)}</small></td><td>{visible(item.fecha_actualizacion)}</td><td className="table-actions"><button type="button" className="secondary" onClick={() => void openDetail(item)}>Ver detalle</button>{canEdit && item.estado_caso !== 'CERRADO' && <><button type="button" className="secondary" onClick={() => setEditing(item)}>Editar</button><button type="button" onClick={() => setClosing(item)}>Cerrar</button></>}</td></tr>)}</tbody></table></div>}
    <div className="pagination-controls"><button type="button" className="secondary" disabled={!page || loading} onClick={() => setPage(page - 1)}>Anterior</button><span>{total ? `Mostrando ${page * pageSize + 1}-${Math.min(total, (page + 1) * pageSize)} de ${total}` : '0 registros'}</span><button type="button" className="secondary" disabled={loading || (page + 1) * pageSize >= total} onClick={() => setPage(page + 1)}>Siguiente</button></div>
    {creating && <RiesgoForm title="Registrar Riesgo" onClose={() => setCreating(false)} onSave={(payload) => saveCreated(payload as RiesgoCreate)} />}
    {editing && <RiesgoForm title={`Editar Riesgo ${editing.codigo_caso}`} riesgo={editing} onClose={() => setEditing(null)} onSave={(payload) => saveEdited(editing, payload as RiesgoUpdate)} />}
    {detail && <RiesgoDetail riesgo={detail} onClose={() => setDetail(null)} />}
    {closing && <CierreForm riesgo={closing} onClose={() => setClosing(null)} onSave={saveClosed} />}
  </section>;
}

function PersonSelector({ value, onChange }: { value: string; onChange: (id: string, label: string, data: SearchResult['data']) => void }) {
  return <SearchAutocompleteField source="PERSONAS" value={value} required selectionOnly ariaLabel="Persona" placeholder="Buscar por nombre o cédula" onSelect={(result, text) => onChange(result?.id ?? '', text, result?.data ?? {})} />;
}

function ResponsableSelector({ value, onChange }: { value: string; onChange: (next: string) => void }) {
  return <SearchAutocompleteField source="RESPONSABLES" value={value} selectionOnly ariaLabel="Responsable" placeholder="Buscar responsable" onSelect={(_result, text) => onChange(text)} />;
}

function RiesgoForm({ title, riesgo, onClose, onSave }: { title: string; riesgo?: RiesgoTrabajo; onClose: () => void; onSave: (payload: RiesgoCreate | RiesgoUpdate) => Promise<void> }) {
  const [data, setData] = useState<RiesgoCreate>(() => riesgo ? { persona_id: riesgo.persona_id, fecha_apertura: riesgo.fecha_apertura ?? today(), responsable: riesgo.responsable ?? '', estado_caso: riesgo.estado_caso, prioridad: riesgo.prioridad ?? '', resultado: riesgo.resultado ?? '' } : blankCreate());
  const [personaLabel, setPersonaLabel] = useState(riesgo?.persona ?? '');
  const [personaMeta, setPersonaMeta] = useState<SearchResult['data']>({});
  const [saving, setSaving] = useState(false); const [error, setError] = useState<string | null>(null);
  const set = <K extends keyof RiesgoCreate>(key: K, value: RiesgoCreate[K]) => setData((current) => ({ ...current, [key]: value }));
  async function submit(event: FormEvent) {
    event.preventDefault(); if (saving) return; setSaving(true); setError(null);
    try {
      if (riesgo) await onSave({ expected_version: riesgo.version, responsable: data.responsable || undefined, estado_caso: data.estado_caso, prioridad: data.prioridad || undefined, resultado: data.resultado || undefined });
      else await onSave(data);
    } catch (caught) { setError(message(caught, 'No fue posible guardar el Riesgo.')); } finally { setSaving(false); }
  }
  return <Modal titulo={title} onClose={onClose} size="large"><form className="form-grid" onSubmit={submit}>
    {!riesgo && <label className="full-width">Persona *<PersonSelector value={personaLabel} onChange={(id, label, meta) => { set('persona_id', id); setPersonaLabel(label); setPersonaMeta(meta); }} />{data.persona_id && <small>{personaMeta.nombre ?? personaLabel} · {personaMeta.cedula ?? 'Sin cédula'} · {personaMeta.area ?? 'Sin área'}</small>}</label>}
    {riesgo && <div className="full-width"><strong>Persona</strong><p>{visible(riesgo.persona)} · {visible(riesgo.cedula)} · {visible(riesgo.area)}</p></div>}
    {!riesgo && <label>Fecha de apertura *<input type="date" required value={data.fecha_apertura} onChange={(e) => set('fecha_apertura', e.target.value)} /></label>}
    <label>Responsable<ResponsableSelector value={data.responsable ?? ''} onChange={(next) => set('responsable', next)} /></label>
    <label>Estado<select value={data.estado_caso} onChange={(e) => set('estado_caso', e.target.value as RiesgoEstado)}><option value="ABIERTO">Abierto</option><option value="EN_SEGUIMIENTO">En seguimiento</option>{riesgo && <option value="CERRADO">Cerrado</option>}</select></label>
    <label>Prioridad<input value={data.prioridad ?? ''} onChange={(e) => set('prioridad', e.target.value)} /></label>
    <label className="full-width">Descripción / resumen *<textarea required value={data.resultado} onChange={(e) => set('resultado', e.target.value)} /></label>
    {error && <p className="form-error full-width" role="alert">{error}</p>}<div className="modal-actions full-width"><button type="button" className="secondary" onClick={onClose}>Cancelar</button><button type="submit" disabled={saving}>{saving ? 'Guardando…' : riesgo ? 'Guardar cambios' : 'Registrar Riesgo'}</button></div>
  </form></Modal>;
}

function RiesgoDetail({ riesgo, onClose }: { riesgo: RiesgoTrabajo; onClose: () => void }) {
  const fields: Record<string, string | number | null | undefined> = { ID: riesgo.id_caso, Código: riesgo.codigo_caso, Persona: riesgo.persona, Cédula: riesgo.cedula, Área: riesgo.area, 'Descripción / resumen': riesgo.resultado ?? riesgo.resumen, Estado: riesgo.estado_caso, Responsable: riesgo.responsable, 'Registrado por': riesgo.registrado_por, 'Fecha de creación': riesgo.fecha_creacion, 'Última actualización': riesgo.fecha_actualizacion, 'Fecha de cierre': riesgo.fecha_cierre, 'Motivo de cierre': riesgo.motivo_cierre, Versión: riesgo.version };
  return <Modal titulo={`Detalle del Riesgo ${riesgo.codigo_caso}`} onClose={onClose} size="large"><dl className="field-list">{Object.entries(fields).map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{visible(value === null || value === undefined ? null : String(value))}</dd></div>)}</dl></Modal>;
}

function CierreForm({ riesgo, onClose, onSave }: { riesgo: RiesgoTrabajo; onClose: () => void; onSave: (item: RiesgoTrabajo, payload: { expected_version: number; fecha_cierre_caso?: string; responsable?: string; motivo_cierre: string; resultado_final?: string }) => Promise<void> }) {
  const [motivo, setMotivo] = useState(''); const [resultado, setResultado] = useState(''); const [fecha, setFecha] = useState(today()); const [responsable, setResponsable] = useState(riesgo.responsable ?? ''); const [saving, setSaving] = useState(false); const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent) { event.preventDefault(); if (saving) return; setSaving(true); setError(null); try { await onSave(riesgo, { expected_version: riesgo.version, fecha_cierre_caso: fecha || undefined, responsable: responsable || undefined, motivo_cierre: motivo, resultado_final: resultado || undefined }); } catch (caught) { setError(message(caught, 'No fue posible cerrar el Riesgo.')); } finally { setSaving(false); } }
  return <Modal titulo={`Cerrar Riesgo ${riesgo.codigo_caso}`} onClose={onClose}><form className="form-grid" onSubmit={submit}><label>Fecha de cierre<input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} /></label><label>Responsable<ResponsableSelector value={responsable} onChange={setResponsable} /></label><label className="full-width">Motivo de cierre *<textarea required value={motivo} onChange={(e) => setMotivo(e.target.value)} /></label><label className="full-width">Resultado final<textarea value={resultado} onChange={(e) => setResultado(e.target.value)} /></label>{error && <p className="form-error full-width" role="alert">{error}</p>}<div className="modal-actions full-width"><button type="button" className="secondary" onClick={onClose}>Cancelar</button><button type="submit" disabled={saving}>{saving ? 'Cerrando…' : 'Cerrar Riesgo'}</button></div></form></Modal>;
}
