import { useEffect, useMemo, useState, type CSSProperties } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../app/AuthContext';
import { canAccess } from '../../api/auth';
import { obtenerDashboard, type DashboardItem, type DatosDashboard } from '../../api/dashboard';
import { HttpError } from '../../api/client';
import { ECUADOR_TIME_ZONE, formatDate, humanizeCode } from '../../utils/dates';

const TARJETAS: { clave: keyof DatosDashboard; etiqueta: string; icono: string; alerta?: boolean; ruta: string; tono: 'info' | 'success' | 'warning' | 'violet' | 'danger' }[] = [
  { clave: 'casesOpen', etiqueta: 'Casos abiertos', icono: '▣', ruta: '/casos', tono: 'info' },
  { clave: 'casesClosed', etiqueta: 'Casos cerrados', icono: '✓', ruta: '/casos', tono: 'success' },
  { clave: 'casesPending', etiqueta: 'Casos pendientes', icono: '◷', ruta: '/casos', tono: 'warning' },
  { clave: 'upcomingFollowUps', etiqueta: 'Seguimientos próximos', icono: '♟', ruta: '/casos', tono: 'violet' },
  { clave: 'overdueCommitments', etiqueta: 'Compromisos vencidos', icono: '!', alerta: true, ruta: '/casos', tono: 'danger' },
  { clave: 'pendingNews', etiqueta: 'Novedades pendientes', icono: '!', ruta: '/novedades', tono: 'warning' },
  { clave: 'toursCompleted', etiqueta: 'Recorridos realizados', icono: '↗', ruta: '/recorridos', tono: 'success' },
];

type ActivityItem = DashboardItem & {
  kind: 'pending' | 'follow-up' | 'overdue';
  title: string;
};

type QuickLink = {
  label: string;
  caption: string;
  icon: string;
  tone: 'blue' | 'green' | 'violet' | 'amber';
  to: string;
  state?: { newRecord: boolean };
};

function percentage(value: number, total: number): number {
  if (total <= 0) return 0;
  return Math.round((value / total) * 100);
}

function dashboardDate(value?: string): string {
  const parsed = value ? new Date(value) : new Date();
  const safeDate = Number.isNaN(parsed.getTime()) ? new Date() : parsed;
  const formatted = new Intl.DateTimeFormat('es-EC', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', timeZone: ECUADOR_TIME_ZONE,
  }).format(safeDate);
  return formatted.charAt(0).toUpperCase() + formatted.slice(1);
}

function activityLabel(kind: ActivityItem['kind']): string {
  if (kind === 'overdue') return 'Vencido';
  if (kind === 'follow-up') return 'Programado';
  return 'En proceso';
}

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
  const canReadCases = canAccess(usuario, 'CASOS', 'read');
  const canCreateCases = canReadCases
    && canAccess(usuario, 'CASOS', 'create')
    && canAccess(usuario, 'RESPUESTAS', 'create');
  const canReadActivities = canAccess(usuario, 'ACTIVIDADES', 'read');
  const canReadForms = canAccess(usuario, 'FORMULARIOS', 'read');

  const casesOpen = Number(datos?.casesOpen ?? 0);
  const casesClosed = Number(datos?.casesClosed ?? 0);
  const casesPending = Number(datos?.casesPending ?? 0);
  const caseTotal = casesOpen + casesClosed + casesPending;
  const openPct = percentage(casesOpen, caseTotal);
  const closedPct = percentage(casesClosed, caseTotal);
  const pendingPct = Math.max(0, 100 - openPct - closedPct);
  const donutStyle = {
    '--open-pct': `${openPct}%`,
    '--closed-stop': `${openPct + closedPct}%`,
  } as CSSProperties;

  const activityItems = useMemo<ActivityItem[]>(() => {
    if (!datos) return [];
    return [
      ...(datos.overdueCommitmentItems ?? []).map((item) => ({ ...item, kind: 'overdue' as const, title: 'Compromiso vencido' })),
      ...(datos.upcomingFollowUpItems ?? []).map((item) => ({ ...item, kind: 'follow-up' as const, title: 'Seguimiento agendado' })),
      ...(datos.pendingCases ?? []).map((item) => ({ ...item, kind: 'pending' as const, title: 'Caso pendiente' })),
    ].slice(0, 5);
  }, [datos]);

  const quickLinks = useMemo<QuickLink[]>(() => {
    const links: QuickLink[] = [];
    if (canCreateCases) links.push({ label: 'Registrar caso', caption: 'Crear un nuevo caso', icon: '▤', tone: 'blue', to: '/casos', state: { newRecord: true } });
    if (canReadActivities) links.push({ label: 'Gestionar actividades', caption: 'Ver agenda y tareas', icon: '♣', tone: 'green', to: '/trabajo-social/actividades' });
    links.push({ label: 'Buscar persona', caption: 'Consulta consolidada', icon: '⌕', tone: 'violet', to: '/busqueda' });
    if (canReadForms) links.push({ label: 'Formularios', caption: 'Repositorio documental', icon: '▤', tone: 'amber', to: '/formularios' });
    return links;
  }, [canCreateCases, canReadActivities, canReadForms]);

  return (
    <section className="dashboard-page dashboard-v2">
      <section className="dashboard-hero-v2">
        <div className="dashboard-hero-copy">
          <p className="dashboard-kicker">Bienvenido al sistema</p>
          <h1>Hola, {usuario?.nombre}.</h1>
          <p>Aquí tienes un resumen de la gestión de Trabajo Social.</p>
          <blockquote>“Personas, historias, oportunidades.”</blockquote>
        </div>
        <div className="dashboard-hero-art" aria-hidden="true">
          <svg viewBox="0 0 230 145" role="presentation">
            <circle cx="84" cy="47" r="14" />
            <circle cx="145" cy="52" r="12" />
            <circle cx="114" cy="73" r="11" />
            <path d="M58 118c6-31 15-49 27-52 15-4 27 14 29 49M164 118c-3-30-10-46-20-49-14-4-24 12-27 46M92 119c2-22 9-36 21-38 13-2 22 12 25 38" />
            <path d="M44 112c25 7 45 4 62-10M185 112c-24 6-44 3-60-10" />
          </svg>
        </div>
        <div className="dashboard-hero-side">
          <div className="dashboard-date-card">
            <span className="dashboard-date-icon" aria-hidden="true">▦</span>
            <div><strong>{dashboardDate(datos?.generatedAt)}</strong><small>Seguimos generando bienestar.</small></div>
          </div>
          {canCreateCases
            ? <Link className="dashboard-new-case" to="/casos" state={{ newRecord: true }}><span>＋</span>Nuevo caso</Link>
            : canReadCases ? <Link className="dashboard-new-case" to="/casos">Ver casos</Link> : null}
        </div>
      </section>

      <div className="dashboard-section-title">
        <div>
          <h2>Resumen operativo</h2>
          <p>Indicadores clave de la gestión actual. Datos actualizados en tiempo real.</p>
        </div>
        <span className="dashboard-period">▦&nbsp;&nbsp;Estado actual</span>
      </div>

      {error && <p className="form-error" role="alert">{error}</p>}

      {cargando ? (
        <div className="dashboard-loading">Cargando indicadores…</div>
      ) : tarjetasVisibles.length === 0 ? (
        <p className="footnote">No tiene indicadores habilitados para su rol.</p>
      ) : (
        <div className="kpi-grid dashboard-kpi-grid">
          {tarjetasVisibles.map((tarjeta) => {
            const valor = Number(datos?.[tarjeta.clave] ?? 0);
            const enAlerta = Boolean(tarjeta.alerta) && valor > 0;
            return (
              <Link key={tarjeta.clave} to={tarjeta.ruta} className={`kpi-card dashboard-kpi-card kpi-card--${tarjeta.tono}${enAlerta ? ' is-alert' : ''}`}>
                <div className="dashboard-kpi-top">
                  <span className="dashboard-kpi-icon" aria-hidden="true">{tarjeta.icono}</span>
                  <span className="dashboard-kpi-label">{tarjeta.etiqueta}</span>
                </div>
                <div className="dashboard-kpi-bottom">
                  <strong className="dashboard-kpi-value">{valor}</strong>
                  <span className="dashboard-kpi-spark" aria-hidden="true"><i /><i /><i /><i /></span>
                </div>
                <span className="dashboard-kpi-link">Ver detalle&nbsp; →</span>
              </Link>
            );
          })}
        </div>
      )}

      {!cargando && datos && (
        <>
          <div className="dashboard-insights-grid">
            <section className="dashboard-card-v2 dashboard-status-panel">
              <div className="dashboard-card-heading">
                <div><span className="dashboard-heading-icon">▥</span><div><h3>Estado de casos</h3><p>Distribución actual de casos registrados.</p></div></div>
                {canReadCases && <Link to="/casos">Ver todos&nbsp; →</Link>}
              </div>
              <div className="dashboard-bars">
                <div className="dashboard-bar-row">
                  <div><strong>Casos abiertos</strong><span>{casesOpen}</span></div>
                  <div className="dashboard-bar-track"><span className="bar-open" style={{ width: `${openPct}%` }} /></div>
                  <small>{openPct}% del total</small>
                </div>
                <div className="dashboard-bar-row">
                  <div><strong>Casos cerrados</strong><span>{casesClosed}</span></div>
                  <div className="dashboard-bar-track"><span className="bar-closed" style={{ width: `${closedPct}%` }} /></div>
                  <small>{closedPct}% del total</small>
                </div>
                <div className="dashboard-bar-row">
                  <div><strong>Casos pendientes</strong><span>{casesPending}</span></div>
                  <div className="dashboard-bar-track"><span className="bar-pending" style={{ width: `${pendingPct}%` }} /></div>
                  <small>{pendingPct}% del total</small>
                </div>
              </div>
            </section>

            <section className="dashboard-card-v2 dashboard-donut-panel">
              <div className="dashboard-card-heading compact">
                <div><span className="dashboard-heading-icon">⊕</span><div><h3>Distribución de casos</h3><p>Composición del estado actual.</p></div></div>
              </div>
              <div className="dashboard-donut-content">
                <div className={`dashboard-donut${caseTotal === 0 ? ' is-empty' : ''}`} style={donutStyle}>
                  <div><span>Total</span><strong>{caseTotal}</strong></div>
                </div>
                <ul className="dashboard-donut-legend">
                  <li><span className="legend-dot legend-open" /><strong>Abiertos</strong><b>{casesOpen} ({openPct}%)</b></li>
                  <li><span className="legend-dot legend-closed" /><strong>Cerrados</strong><b>{casesClosed} ({closedPct}%)</b></li>
                  <li><span className="legend-dot legend-pending" /><strong>Pendientes</strong><b>{casesPending} ({pendingPct}%)</b></li>
                </ul>
              </div>
            </section>
          </div>

          <div className="dashboard-lower-grid">
            <section className="dashboard-card-v2 dashboard-activity-panel">
              <div className="dashboard-card-heading">
                <div><span className="dashboard-heading-icon">☷</span><div><h3>Gestión prioritaria</h3><p>Casos, seguimientos y compromisos que requieren atención.</p></div></div>
                {canReadCases && <Link to="/casos">Ver todos&nbsp; →</Link>}
              </div>
              {activityItems.length === 0 ? (
                <div className="dashboard-empty-state"><span>✓</span><p>No hay elementos prioritarios en este momento.</p></div>
              ) : (
                <ul className="dashboard-activity-list">
                  {activityItems.map((item, index) => (
                    <li key={`${item.kind}-${item.caseId}-${item.date}-${index}`}>
                      <span className={`activity-symbol activity-symbol--${item.kind}`} aria-hidden="true">{item.kind === 'overdue' ? '!' : item.kind === 'follow-up' ? '▦' : '▤'}</span>
                      <Link to={`/casos/${item.caseId}`}>
                        <strong>{item.title}</strong>
                        <small>{item.caseCode} · {item.description ?? item.owner ?? humanizeCode(item.status)}</small>
                      </Link>
                      <div className="activity-meta"><span>{formatDate(item.date)}</span><b className={`activity-status activity-status--${item.kind}`}>{activityLabel(item.kind)}</b></div>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="dashboard-card-v2 dashboard-quick-panel">
              <div className="dashboard-card-heading compact">
                <div><span className="dashboard-heading-icon">ϟ</span><div><h3>Accesos rápidos</h3><p>Funciones de uso frecuente.</p></div></div>
              </div>
              <div className="dashboard-quick-grid">
                {quickLinks.map((item) => (
                  <Link key={item.label} to={item.to} state={item.state} className={`quick-access quick-access--${item.tone}`}>
                    <span aria-hidden="true">{item.icon}</span><div><strong>{item.label}</strong><small>{item.caption}</small></div>
                  </Link>
                ))}
              </div>
            </section>
          </div>
        </>
      )}
    </section>
  );
}
