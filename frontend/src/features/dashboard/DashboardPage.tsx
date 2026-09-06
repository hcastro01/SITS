import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../app/AuthContext';
import { obtenerDashboard, type DatosDashboard } from '../../api/dashboard';
import { HttpError } from '../../api/client';

const TARJETAS: { clave: keyof DatosDashboard; etiqueta: string; icono: string; alerta?: boolean; ruta: string }[] = [
  { clave: 'casesOpen', etiqueta: 'Casos abiertos', icono: '◇', ruta: '/casos' },
  { clave: 'casesClosed', etiqueta: 'Casos cerrados', icono: '✓', ruta: '/casos' },
  { clave: 'casesPending', etiqueta: 'Casos pendientes', icono: '…', ruta: '/casos' },
  { clave: 'upcomingFollowUps', etiqueta: 'Seguimientos próximos', icono: '↻', ruta: '/casos' },
  { clave: 'overdueCommitments', etiqueta: 'Compromisos vencidos', icono: '!', alerta: true, ruta: '/casos' },
  { clave: 'pendingNews', etiqueta: 'Novedades pendientes', icono: '!', ruta: '/novedades' },
  { clave: 'toursCompleted', etiqueta: 'Recorridos realizados', icono: '↗', ruta: '/recorridos' },
];

export function DashboardPage() {
  const { usuario } = useAuth();
  const [datos, setDatos] = useState<DatosDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    let activo = true;
    obtenerDashboard()
      .then((res) => { if (activo) setDatos(res); })
      .catch((err: unknown) => { if (activo) setError(err instanceof HttpError ? err.message : 'No fue posible cargar el resumen.'); })
      .finally(() => { if (activo) setCargando(false); });
    return () => { activo = false; };
  }, []);

  const tarjetasVisibles = datos ? TARJETAS.filter((tarjeta) => datos[tarjeta.clave] !== undefined) : [];

  return (
    <section className="panel wide-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Resumen operativo</p>
          <h2>Hola, {usuario?.nombre}</h2>
        </div>
        <Link className="button-link" to="/casos">+ Nuevo caso</Link>
      </div>
      <p className="footnote">Rol: {usuario?.rol_nombre} · Indicadores según sus permisos, sin detalle sensible.</p>

      {error && <p className="form-error" role="alert">{error}</p>}

      {cargando ? (
        <p>Cargando indicadores…</p>
      ) : tarjetasVisibles.length === 0 ? (
        <p className="footnote">No tiene indicadores habilitados para su rol.</p>
      ) : (
        <div className="kpi-grid">
          {tarjetasVisibles.map((tarjeta) => {
            const valor = Number(datos?.[tarjeta.clave] ?? 0);
            const enAlerta = Boolean(tarjeta.alerta) && valor > 0;
            return (
              <Link key={tarjeta.clave} to={tarjeta.ruta} className={`kpi-card${enAlerta ? ' is-alert' : ''}`}>
                <div className="kpi-label">
                  <span>{tarjeta.etiqueta}</span>
                  <span className="kpi-icon" aria-hidden="true">{tarjeta.icono}</span>
                </div>
                <strong className="kpi-value">{valor}</strong>
                <span className="kpi-trend">{enAlerta ? 'Requiere atención' : 'Actualizado ahora'}</span>
              </Link>
            );
          })}
        </div>
      )}
    </section>
  );
}
