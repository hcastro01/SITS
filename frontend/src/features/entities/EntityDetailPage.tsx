import { Fragment, useCallback, useEffect, useState, type FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import { HttpError } from '../../api/client';
import type { EntityRecord, EventoHistorial } from '../../api/entities';
import { DocumentosPanel } from '../documentos/DocumentosPanel';
import { EntityFormModal } from './EntityFormModal';
import type { EntityPageConfig } from './EntityConfig';
import { useFeedback } from '../../components/FeedbackProvider';
import { useUnsavedChanges } from '../../components/useUnsavedChanges';
import { formatDate, formatDateTime, humanizeCode } from '../../utils/dates';

export function EntityDetailPage({ config }: { config: EntityPageConfig }) {
  const { notify, confirm } = useFeedback();
  const { id = '' } = useParams();
  const [registro, setRegistro] = useState<EntityRecord | null>(null);
  const [historial, setHistorial] = useState<EventoHistorial[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [motivoEliminacion, setMotivoEliminacion] = useState('');
  const [procesando, setProcesando] = useState(false);
  const [editando, setEditando] = useState(false);
  useUnsavedChanges(Boolean(motivoEliminacion));

  const cargar = useCallback(async () => {
    setError(null);
    try {
      const [datos, eventos] = await Promise.all([config.api.get(id), config.api.history(id)]);
      setRegistro(datos);
      setHistorial(eventos);
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible cargar el registro.');
    } finally {
      setCargando(false);
    }
  }, [config, id]);

  useEffect(() => { cargar(); }, [cargar]);

  async function handleEliminar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!registro) return;
    if (!await confirm({ title: `Eliminar ${config.tituloSingular}`, message: 'Se aplicará una eliminación lógica y el evento quedará auditado.', confirmLabel: 'Eliminar registro', danger: true })) return;
    setProcesando(true);
    setError(null);
    try {
      await config.api.softDelete(id, { expected_version: registro.version, motivo: motivoEliminacion });
      setMotivoEliminacion('');
      await cargar();
      notify('Registro eliminado correctamente.');
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible eliminar el registro.');
    } finally {
      setProcesando(false);
    }
  }

  async function handleRestaurar() {
    setProcesando(true);
    setError(null);
    try {
      await config.api.restore(id);
      await cargar();
      notify('Registro restaurado correctamente.');
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible restaurar el registro.');
    } finally {
      setProcesando(false);
    }
  }

  if (cargando) return <p>Cargando…</p>;
  if (!registro) return <p className="form-error">Registro no encontrado.</p>;

  return (
    <div className="detail-page">
      <Link className="back-link" to={config.rutaBase}>← Volver a {config.titulo.toLowerCase()}</Link>
      <section className="panel">
        <div className="panel-header">
          <h2>{config.tituloSingular} {registro.eliminado ? '(eliminado)' : ''}</h2>
          {!registro.eliminado && (
            <button type="button" className="secondary as-button" onClick={() => setEditando(true)}>Editar</button>
          )}
        </div>
        {error && <p className="form-error" role="alert">{error}</p>}
        <dl className="field-list">
          {config.campos.map((campo) => (
            <Fragment key={campo.nombre}>
              <dt>{campo.etiqueta}</dt>
              <dd>{campo.nombre.startsWith('fecha') ? formatDate(String(registro[campo.nombre] ?? '')) : String(registro[campo.nombre] ?? '—')}</dd>
            </Fragment>
          ))}
          <dt>Versión</dt><dd>{registro.version}</dd>
        </dl>

        {registro.eliminado ? (
            <button onClick={handleRestaurar} disabled={procesando}>
            {procesando ? 'Restaurando…' : 'Restaurar'}
          </button>
        ) : (
          <form onSubmit={handleEliminar}>
            <label htmlFor="motivo-eliminacion">Motivo de eliminación</label>
            <input
              id="motivo-eliminacion" required value={motivoEliminacion}
              onChange={(event) => setMotivoEliminacion(event.target.value)}
            />
            <button type="submit" className="danger" disabled={procesando}>{procesando ? 'Eliminando…' : 'Eliminar registro'}</button>
          </form>
        )}
      </section>

      <DocumentosPanel tipoRegistro={config.tipoRegistro} idRegistro={id} />

      <section className="panel">
        <h2>Historial</h2>
        {historial.length === 0 ? (
          <p className="footnote">Sin eventos registrados.</p>
        ) : (
          <ul className="history-list">
            {historial.map((evento, indice) => (
              <li key={indice}>
                <strong>{evento.usuario} {humanizeCode(evento.accion).toLowerCase()} {humanizeCode(evento.campo).toLowerCase()}</strong>
                <small>{formatDateTime(evento.fecha_hora)}{evento.motivo ? ` · ${evento.motivo}` : ''}</small>
              </li>
            ))}
          </ul>
        )}
      </section>

      {editando && (
        <EntityFormModal
          config={config}
          registro={registro}
          onClose={() => setEditando(false)}
          onSaved={() => { setEditando(false); cargar(); }}
        />
      )}
    </div>
  );
}
