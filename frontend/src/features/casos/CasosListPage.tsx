import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { listarCasos, type Caso } from '../../api/casos';
import { HttpError } from '../../api/client';
import { CasoFormModal } from './CasoFormModal';

export function CasosListPage() {
  const [casos, setCasos] = useState<Caso[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [modalAbierto, setModalAbierto] = useState(false);

  useEffect(() => {
    let activo = true;
    listarCasos()
      .then((datos) => { if (activo) setCasos(datos); })
      .catch((err: unknown) => { if (activo) setError(err instanceof HttpError ? err.message : 'No fue posible cargar los casos.'); })
      .finally(() => { if (activo) setCargando(false); });
    return () => { activo = false; };
  }, []);

  return (
    <section className="panel wide-panel">
      <div className="panel-header">
        <h2>Casos</h2>
        <button type="button" className="button-link as-button" onClick={() => setModalAbierto(true)}>Nuevo caso</button>
      </div>
      {error && <p className="form-error" role="alert">{error}</p>}
      {cargando ? (
        <p>Cargando…</p>
      ) : casos.length === 0 ? (
        <p className="footnote">No hay casos registrados todavía.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr><th>Código</th><th>Responsable</th><th>Estado</th><th>Prioridad</th><th></th></tr>
          </thead>
          <tbody>
            {casos.map((caso) => (
              <tr key={caso.id_caso}>
                <td>{caso.codigo_caso}</td>
                <td>{caso.responsable ?? '—'}</td>
                <td>{caso.estado_caso ?? '—'}</td>
                <td>{caso.prioridad ?? '—'}</td>
                <td><Link to={`/casos/${caso.id_caso}`}>Ver</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {modalAbierto && (
        <CasoFormModal
          onClose={() => setModalAbierto(false)}
          onSaved={(caso) => { setModalAbierto(false); setCasos((previo) => [caso, ...previo]); }}
        />
      )}
    </section>
  );
}
