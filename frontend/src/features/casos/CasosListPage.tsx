import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../app/AuthContext';
import { canAccess } from '../../api/auth';
import { listarCasos, type Caso } from '../../api/casos';
import { HttpError } from '../../api/client';
import { humanizeCode } from '../../utils/dates';
import { ModuleFormRecordsPanel } from '../formularios/ModuleFormRecordsPanel';
import { ModuleFormSelector } from '../formularios/ModuleFormSelector';

export function CasosListPage() {
  const { usuario } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [casos, setCasos] = useState<Caso[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [selectorAbierto, setSelectorAbierto] = useState(false);
  const canCreate = canAccess(usuario, 'CASOS', 'create') && canAccess(usuario, 'RESPUESTAS', 'create');

  useEffect(() => {
    if ((location.state as { newRecord?: boolean } | null)?.newRecord && canCreate) {
      setSelectorAbierto(true);
      navigate(location.pathname, { replace: true, state: null });
    }
  }, [canCreate, location.pathname, location.state, navigate]);

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
        {canCreate && <button type="button" className="button-link as-button" onClick={() => setSelectorAbierto(true)}>Nuevo registro</button>}
      </div>
      {error && <p className="form-error" role="alert">{error}</p>}
      {cargando ? (
        <p>Cargando…</p>
      ) : casos.length === 0 ? (
        <p className="footnote">No hay casos registrados todavía.</p>
      ) : (
        <div className="table-scroll"><table className="data-table">
          <thead>
            <tr><th>Código</th><th>Responsable</th><th>Estado</th><th>Prioridad</th><th></th></tr>
          </thead>
          <tbody>
            {casos.map((caso) => (
              <tr key={caso.id_caso}>
                <td>{caso.codigo_caso}</td>
                <td>{caso.responsable ?? '—'}</td>
                <td><span className="badge">{humanizeCode(caso.estado_caso)}</span></td>
                <td><span className="badge">{humanizeCode(caso.prioridad)}</span></td>
                <td><Link to={`/casos/${caso.id_caso}`}>Ver</Link></td>
              </tr>
            ))}
          </tbody>
        </table></div>
      )}

      <ModuleFormRecordsPanel module="CASOS" />

      {selectorAbierto && <ModuleFormSelector module="CASOS" moduleLabel="Casos"
                                              onClose={() => setSelectorAbierto(false)} />}
    </section>
  );
}
