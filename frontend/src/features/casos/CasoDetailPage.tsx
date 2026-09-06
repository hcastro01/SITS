import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { useParams } from 'react-router-dom';
import {
  agregarSeguimiento, cerrarCaso, historialCaso, obtenerCaso,
  type Caso, type EventoHistorial,
} from '../../api/casos';
import { HttpError } from '../../api/client';
import { DocumentosPanel } from '../documentos/DocumentosPanel';
import { CasoFormModal } from './CasoFormModal';

export function CasoDetailPage() {
  const { id = '' } = useParams();
  const [caso, setCaso] = useState<Caso | null>(null);
  const [historial, setHistorial] = useState<EventoHistorial[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [editando, setEditando] = useState(false);

  const [descripcionSeguimiento, setDescripcionSeguimiento] = useState('');
  const [enviandoSeguimiento, setEnviandoSeguimiento] = useState(false);

  const [motivoCierre, setMotivoCierre] = useState('');
  const [enviandoCierre, setEnviandoCierre] = useState(false);

  const cargar = useCallback(async () => {
    setError(null);
    try {
      const [datosCaso, eventos] = await Promise.all([obtenerCaso(id), historialCaso(id)]);
      setCaso(datosCaso);
      setHistorial(eventos);
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible cargar el caso.');
    } finally {
      setCargando(false);
    }
  }, [id]);

  useEffect(() => { cargar(); }, [cargar]);

  async function handleAgregarSeguimiento(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setEnviandoSeguimiento(true);
    setError(null);
    try {
      await agregarSeguimiento(id, {
        fecha: new Date().toISOString().slice(0, 10),
        descripcion: descripcionSeguimiento,
      });
      setDescripcionSeguimiento('');
      await cargar();
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible guardar el seguimiento.');
    } finally {
      setEnviandoSeguimiento(false);
    }
  }

  async function handleCerrarCaso(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!caso) return;
    setEnviandoCierre(true);
    setError(null);
    try {
      await cerrarCaso(id, {
        expected_version: caso.version,
        fecha_cierre_caso: new Date().toISOString().slice(0, 10),
        responsable: caso.responsable ?? 'Sin responsable',
        motivo_cierre: motivoCierre,
      });
      setMotivoCierre('');
      await cargar();
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible cerrar el caso.');
    } finally {
      setEnviandoCierre(false);
    }
  }

  if (cargando) return <p>Cargando…</p>;
  if (!caso) return <p className="form-error">Caso no encontrado.</p>;

  const cerrado = (caso.estado_caso ?? '').toUpperCase() === 'CERRADO';

  return (
    <div className="detail-grid">
      <section className="panel">
        <div className="panel-header">
          <h2>{caso.codigo_caso}</h2>
          {!cerrado && <button type="button" className="secondary as-button" onClick={() => setEditando(true)}>Editar</button>}
        </div>
        {error && <p className="form-error" role="alert">{error}</p>}
        <dl className="field-list">
          <dt>Responsable</dt><dd>{caso.responsable ?? '—'}</dd>
          <dt>Estado</dt><dd>{caso.estado_caso ?? '—'}</dd>
          <dt>Prioridad</dt><dd>{caso.prioridad ?? '—'}</dd>
          <dt>Tipo</dt><dd>{caso.tipo_caso ?? '—'}</dd>
          <dt>Sensible</dt><dd>{caso.sensible ? 'Sí' : 'No'}</dd>
          <dt>Versión</dt><dd>{caso.version}</dd>
        </dl>

        {!cerrado && (
          <>
            <h3>Agregar seguimiento</h3>
            <form onSubmit={handleAgregarSeguimiento}>
              <label htmlFor="descripcion-seguimiento">Descripción</label>
              <input
                id="descripcion-seguimiento" required value={descripcionSeguimiento}
                onChange={(e) => setDescripcionSeguimiento(e.target.value)}
              />
              <button type="submit" disabled={enviandoSeguimiento}>
                {enviandoSeguimiento ? 'Guardando…' : 'Guardar seguimiento'}
              </button>
            </form>

            <h3>Cerrar caso</h3>
            <form onSubmit={handleCerrarCaso}>
              <label htmlFor="motivo-cierre">Motivo de cierre</label>
              <input id="motivo-cierre" required value={motivoCierre} onChange={(e) => setMotivoCierre(e.target.value)} />
              <button type="submit" disabled={enviandoCierre}>{enviandoCierre ? 'Cerrando…' : 'Cerrar caso'}</button>
            </form>
          </>
        )}
      </section>

      <DocumentosPanel tipoRegistro="CASOS" idRegistro={id} />

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

      {editando && (
        <CasoFormModal
          caso={caso}
          onClose={() => setEditando(false)}
          onSaved={() => { setEditando(false); cargar(); }}
        />
      )}
    </div>
  );
}
