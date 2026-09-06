import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  agregarSeguimiento, cerrarCaso, historialCaso, listarCompromisos, listarSeguimientos, obtenerCaso,
  type Caso, type Compromiso, type EventoHistorial, type Seguimiento,
} from '../../api/casos';
import { HttpError } from '../../api/client';
import { Modal } from '../../components/Modal';
import { useFeedback } from '../../components/FeedbackProvider';
import { useUnsavedChanges } from '../../components/useUnsavedChanges';
import { formatDate, formatDateTime, humanizeCode, todayInEcuador } from '../../utils/dates';
import { DocumentosPanel } from '../documentos/DocumentosPanel';
import { CasoFormModal } from './CasoFormModal';

type Tab = 'resumen' | 'seguimientos' | 'documentos' | 'historial';

const FIELD_LABELS: Record<string, string> = {
  estado_caso: 'estado del caso', prioridad: 'prioridad', responsable: 'responsable',
  ultimo_seguimiento: 'último seguimiento', fecha_cierre: 'fecha de cierre', motivo_cierre: 'motivo de cierre',
  '*': 'registro',
};

function badgeTone(value: string | null | undefined): string {
  const normalized = (value ?? '').toUpperCase();
  if (['ALTA', 'URGENTE', 'VENCIDO'].includes(normalized)) return ' badge--danger';
  if (['MEDIA', 'PENDIENTE', 'EN SEGUIMIENTO'].includes(normalized)) return ' badge--warning';
  if (['CERRADO', 'CUMPLIDO', 'RESUELTO'].includes(normalized)) return ' badge--success';
  return '';
}

function historyText(event: EventoHistorial): string {
  const action = event.accion.toUpperCase();
  const field = FIELD_LABELS[event.campo] ?? humanizeCode(event.campo).toLowerCase();
  if (action === 'CREATE') return `${event.usuario} creó ${field}`;
  if (action === 'DELETE') return `${event.usuario} eliminó ${field}`;
  if (action === 'DOWNLOAD_FILE') return `${event.usuario} descargó un documento`;
  if (event.valor_nuevo != null) return `${event.usuario} actualizó ${field} a “${humanizeCode(event.valor_nuevo)}”`;
  return `${event.usuario} actualizó ${field}`;
}

export function CasoDetailProductionPage() {
  const { id = '' } = useParams();
  const { notify, confirm } = useFeedback();
  const [caso, setCaso] = useState<Caso | null>(null);
  const [historial, setHistorial] = useState<EventoHistorial[]>([]);
  const [seguimientos, setSeguimientos] = useState<Seguimiento[]>([]);
  const [compromisos, setCompromisos] = useState<Compromiso[]>([]);
  const [tab, setTab] = useState<Tab>('resumen');
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [editando, setEditando] = useState(false);
  const [cerrando, setCerrando] = useState(false);
  const [descripcion, setDescripcion] = useState('');
  const [proximaAccion, setProximaAccion] = useState('');
  const [fechaProxima, setFechaProxima] = useState('');
  const [enviandoSeguimiento, setEnviandoSeguimiento] = useState(false);
  const [motivoCierre, setMotivoCierre] = useState('');
  const [enviandoCierre, setEnviandoCierre] = useState(false);

  const dirty = Boolean(descripcion || proximaAccion || fechaProxima || motivoCierre);
  useUnsavedChanges(dirty);

  const cargar = useCallback(async () => {
    setError(null);
    try {
      const [datosCaso, eventos, listaSeguimientos, listaCompromisos] = await Promise.all([
        obtenerCaso(id), historialCaso(id), listarSeguimientos(id), listarCompromisos(id),
      ]);
      setCaso(datosCaso);
      setHistorial(eventos);
      setSeguimientos(listaSeguimientos);
      setCompromisos(listaCompromisos);
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible cargar el caso.');
    } finally {
      setCargando(false);
    }
  }, [id]);

  useEffect(() => { void cargar(); }, [cargar]);

  const pendientes = useMemo(() => compromisos.filter((item) => !['CERRADO', 'CUMPLIDO', 'CANCELADO'].includes((item.estado ?? '').toUpperCase())), [compromisos]);

  async function handleAgregarSeguimiento(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setEnviandoSeguimiento(true);
    setError(null);
    try {
      await agregarSeguimiento(id, {
        fecha: todayInEcuador(), descripcion,
        proxima_accion: proximaAccion || undefined,
        fecha_proxima_accion: fechaProxima || undefined,
        estado: 'ABIERTO',
      });
      setDescripcion(''); setProximaAccion(''); setFechaProxima('');
      await cargar();
      notify('Seguimiento registrado correctamente.');
    } catch (err) {
      const message = err instanceof HttpError ? err.message : 'No fue posible guardar el seguimiento.';
      setError(message); notify(message, 'error');
    } finally { setEnviandoSeguimiento(false); }
  }

  async function handleCerrarCaso(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!caso) return;
    setEnviandoCierre(true);
    setError(null);
    try {
      await cerrarCaso(id, {
        expected_version: caso.version,
        fecha_cierre_caso: todayInEcuador(),
        responsable: caso.responsable ?? 'Sin responsable',
        motivo_cierre: motivoCierre,
      });
      setMotivoCierre(''); setCerrando(false);
      await cargar();
      notify('Caso cerrado correctamente.');
    } catch (err) {
      const message = err instanceof HttpError ? err.message : 'No fue posible cerrar el caso.';
      setError(message); notify(message, 'error');
    } finally { setEnviandoCierre(false); }
  }

  async function requestCloseEdit() {
    setEditando(false);
  }

  async function requestCloseCase() {
    if (!motivoCierre || await confirm({
      title: 'Cambios sin guardar', message: 'El motivo de cierre todavía no se guardó.',
      confirmLabel: 'Salir sin guardar', cancelLabel: 'Continuar editando', danger: true,
    })) {
      setMotivoCierre(''); setCerrando(false);
    }
  }

  if (cargando) return <p className="loading-message">Cargando caso…</p>;
  if (!caso) return <p className="form-error">{error ?? 'Caso no encontrado.'}</p>;
  const cerrado = (caso.estado_caso ?? '').toUpperCase() === 'CERRADO';

  return (
    <div className="detail-page">
      <Link className="back-link" to="/casos">← Volver a casos</Link>
      <section className="panel">
        <div className="detail-title-row">
          <div><p className="eyebrow">Detalle del caso</p><h2>{caso.codigo_caso}</h2></div>
          <div className="status-cluster" aria-label="Estado y prioridad">
            <span className={`badge${badgeTone(caso.estado_caso)}`}>Estado: {humanizeCode(caso.estado_caso)}</span>
            <span className={`badge${badgeTone(caso.prioridad)}`}>Prioridad: {humanizeCode(caso.prioridad)}</span>
          </div>
        </div>
        {error && <p className="form-error" role="alert">{error}</p>}
      </section>

      <div className="tabs" role="tablist" aria-label="Secciones del caso">
        {([['resumen', 'Resumen'], ['seguimientos', `Seguimientos (${seguimientos.length})`], ['documentos', 'Documentos'], ['historial', 'Historial']] as [Tab, string][]).map(([value, label]) => (
          <button key={value} type="button" role="tab" aria-selected={tab === value} aria-controls={`panel-${value}`} onClick={() => setTab(value)}>{label}</button>
        ))}
      </div>

      {tab === 'resumen' && (
        <section id="panel-resumen" role="tabpanel" className="panel tab-panel">
          <div className="panel-header">
            <div><h2>Resumen</h2><p className="footnote">Información principal y compromisos abiertos.</p></div>
            {!cerrado && <button type="button" className="secondary" onClick={() => setEditando(true)}>Editar caso</button>}
          </div>
          <dl className="field-list">
            <dt>Responsable</dt><dd>{caso.responsable ?? '—'}</dd>
            <dt>Tipo de caso</dt><dd>{humanizeCode(caso.tipo_caso)}</dd>
            <dt>Fecha de apertura</dt><dd>{formatDate(caso.fecha_apertura)}</dd>
            <dt>Sensibilidad</dt><dd>{caso.sensible ? 'Información sensible' : 'Estándar'}</dd>
            <dt>Compromisos pendientes</dt><dd>{pendientes.length}</dd>
          </dl>
          {!cerrado && <div className="button-row"><button type="button" className="danger" onClick={() => setCerrando(true)}>Cerrar caso</button></div>}
        </section>
      )}

      {tab === 'seguimientos' && (
        <section id="panel-seguimientos" role="tabpanel" className="panel tab-panel">
          <h2>Seguimientos</h2>
          {!cerrado && (
            <form onSubmit={handleAgregarSeguimiento}>
              <label htmlFor="descripcion-seguimiento">Descripción</label>
              <textarea id="descripcion-seguimiento" required value={descripcion} onChange={(e) => setDescripcion(e.target.value)} />
              <div className="form-grid">
                <div><label htmlFor="proxima-accion">Próxima acción</label><input id="proxima-accion" value={proximaAccion} onChange={(e) => setProximaAccion(e.target.value)} /></div>
                <div><label htmlFor="fecha-proxima">Fecha de próxima acción</label><input id="fecha-proxima" type="date" min={todayInEcuador()} value={fechaProxima} onChange={(e) => setFechaProxima(e.target.value)} /></div>
              </div>
              <div className="button-row"><button type="submit" disabled={enviandoSeguimiento}>{enviandoSeguimiento ? 'Guardando…' : 'Guardar seguimiento'}</button></div>
            </form>
          )}
          {seguimientos.length === 0 ? <p className="footnote">Aún no hay seguimientos.</p> : (
            <ul className="history-list">
              {seguimientos.map((item) => <li key={item.id_seguimiento}><strong>{item.descripcion ?? 'Seguimiento'}</strong><small>{formatDate(item.fecha)} · {item.responsable ?? 'Sin responsable'}</small>{item.proxima_accion && <p>Próxima acción: {item.proxima_accion} · {formatDate(item.fecha_proxima_accion)}</p>}</li>)}
            </ul>
          )}
        </section>
      )}

      {tab === 'documentos' && <div id="panel-documentos" role="tabpanel" className="tab-panel"><DocumentosPanel tipoRegistro="CASOS" idRegistro={id} /></div>}

      {tab === 'historial' && (
        <section id="panel-historial" role="tabpanel" className="panel tab-panel">
          <h2>Historial</h2>
          {historial.length === 0 ? <p className="footnote">Sin eventos registrados.</p> : (
            <ul className="history-list">{historial.map((event, index) => <li key={`${event.fecha_hora}-${index}`}><strong>{historyText(event)}</strong><small>{formatDateTime(event.fecha_hora)}{event.motivo ? ` · ${event.motivo}` : ''}</small></li>)}</ul>
          )}
        </section>
      )}

      {editando && <CasoFormModal caso={caso} onClose={requestCloseEdit} onSaved={() => { setEditando(false); void cargar(); notify('Cambios actualizados correctamente.'); }} />}
      {cerrando && (
        <Modal titulo={`Cerrar caso ${caso.codigo_caso}`} onClose={() => void requestCloseCase()} closeOnBackdrop={!enviandoCierre} size="small">
          <p className="inline-alert">El caso quedará cerrado y este cambio se registrará en el historial.</p>
          <form onSubmit={handleCerrarCaso}>
            <label htmlFor="motivo-cierre">Motivo de cierre</label>
            <textarea id="motivo-cierre" required data-autofocus value={motivoCierre} onChange={(e) => setMotivoCierre(e.target.value)} />
            <div className="modal-actions"><button type="button" className="secondary" onClick={() => void requestCloseCase()}>Cancelar</button><button type="submit" className="danger" disabled={enviandoCierre}>{enviandoCierre ? 'Cerrando…' : 'Confirmar cierre'}</button></div>
          </form>
        </Modal>
      )}
    </div>
  );
}
