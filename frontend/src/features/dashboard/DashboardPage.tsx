import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../app/AuthContext';
import { obtenerDashboard, type DatosDashboard } from '../../api/dashboard';
import { HttpError } from '../../api/client';
import { formatDate, humanizeCode } from '../../utils/dates';

const TARJETAS: { clave: keyof DatosDashboard; etiqueta: string; icono: string; alerta?: boolean; ruta: string; tono: 'info' | 'success' | 'warning' | 'danger' }[] = [
  { clave: 'casesOpen', etiqueta: 'Casos abiertos', icono: '◇', ruta: '/casos', tono: 'info' },
  { clave: 'casesClosed', etiqueta: 'Casos cerrados', icono: '✓', ruta: '/casos', tono: 'success' },
  { clave: 'casesPending', etiqueta: 'Casos pendientes', icono: '…', ruta: '/casos', tono: 'warning' },
  { clave: 'upcomingFollowUps', etiqueta: 'Seguimientos próximos', icono: '↻', ruta: '/casos', tono: 'info' },
  { clave: 'overdueCommitments', etiqueta: 'Compromisos vencidos', icono: '!', alerta: true, ruta: '/casos', tono: 'danger' },
  { clave: 'pendingNews', etiqueta: 'Novedades pendientes', icono: '!', ruta: '/novedades', tono: 'warning' },
  { clave: 'toursCompleted', etiqueta: 'Recorridos realizados', icono: '↗', ruta: '/recorridos', tono: 'success' },
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

  const bloques = datos ? [
    { title: 'Pendientes', subtitle: 'Casos que requieren gestión', items: datos.pendingCases ?? [], danger: false },
    { title: 'Próximos seguimientos', subtitle: 'Acciones programadas desde hoy', items: datos.upcomingFollowUpItems ?? [], danger: false },
    { title: 'Compromisos vencidos', subtitle: 'Atención prioritaria', items: datos.overdueCommitmentItems ?? [], danger: true },
  ] : [];

  return (
    <section className="dashboard-page">
      <div className="panel panel-header dashboard-heading">
        <div>
          <p className="eyebrow">Resumen operativo</p>
          <h2>Hola, {usuario?.nombre}. Esto requiere atención.</h2>
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
              <Link key={tarjeta.clave} to={tarjeta.ruta} className={`kpi-card kpi-card--${tarjeta.tono}${enAlerta ? ' is-alert' : ''}`}>
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
      {!cargando && datos && (
        <div className="dashboard-actions">
          {bloques.map((bloque) => (
            <section key={bloque.title} className={`dashboard-block${bloque.danger ? ' dashboard-block--danger' : ''}`}>
              <div className="section-heading">
                <div><h3>{bloque.title}</h3><p className="footnote">{bloque.subtitle}</p></div>
                <span className={bloque.danger && bloque.items.length ? 'badge badge--danger' : 'badge'}>{bloque.items.length}</span>
              </div>
              {bloque.items.length === 0 ? (
                <p className="footnote">No hay elementos en esta categoría.</p>
              ) : (
                <ul className="action-list">
                  {bloque.items.map((item, index) => (
                    <li key={`${item.caseId}-${item.date}-${index}`} className={bloque.danger ? 'overdue' : undefined}>
                      <Link to={`/casos/${item.caseId}`}>
                        <strong>{item.caseCode}</strong><span>{formatDate(item.date)}</span>
                        <p>{item.description ?? item.owner ?? humanizeCode(item.status)}</p>
                        <small>{item.priority ? `Prioridad: ${humanizeCode(item.priority)}` : humanizeCode(item.status)}</small>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          ))}
        </div>
      )}
    </section>
  );
}
