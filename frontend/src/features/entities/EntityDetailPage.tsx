import { Fragment, useCallback, useEffect, useState, type FormEvent } from 'react';
import { useParams } from 'react-router-dom';
import { HttpError } from '../../api/client';
import type { EntityRecord, EventoHistorial } from '../../api/entities';
import type { EntityPageConfig } from './EntityConfig';

export function EntityDetailPage({ config }: { config: EntityPageConfig }) {
  const { id = '' } = useParams();
  const [registro, setRegistro] = useState<EntityRecord | null>(null);
  const [historial, setHistorial] = useState<EventoHistorial[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [motivoEliminacion, setMotivoEliminacion] = useState('');
  const [procesando, setProcesando] = useState(false);

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
    setProcesando(true);
    setError(null);
    try {
      await config.api.softDelete(id, { expected_version: registro.version, motivo: motivoEliminacion });
      setMotivoEliminacion('');
      await cargar();
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
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible restaurar el registro.');
    } finally {
      setProcesando(false);
    }
  }

  if (cargando) return <p>Cargando…</p>;
  if (!registro) return <p className="form-error">Registro no encontrado.</p>;

  return (
    <div className="detail-grid">
      <section className="panel">
        <h2>{config.tituloSingular} {registro.eliminado ? '(eliminado)' : ''}</h2>
        {error && <p className="form-error" role="alert">{error}</p>}
        <dl className="field-list">
          {config.campos.map((campo) => (
            <Fragment key={campo.nombre}>
              <dt>{campo.etiqueta}</dt>
              <dd>{String(registro[campo.nombre] ?? '—')}</dd>
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
            <button type="submit" disabled={procesando}>{procesando ? 'Eliminando…' : 'Eliminar'}</button>
          </form>
        )}
      </section>

      <section className="panel">
        <h2>Historial</h2>
        {historial.length === 0 ? (
          <p className="footnote">Sin eventos registrados.</p>
        ) : (
          <ul className="history-list">
            {historial.map((evento, indice) => (
              <li key={indice}>
                <strong>{evento.accion}</strong> · {evento.campo}: {evento.valor_anterior ?? '—'} → {evento.valor_nuevo ?? '—'}
                <br /><small>{evento.usuario} · {evento.fecha_hora}</small>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
