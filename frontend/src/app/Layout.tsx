import { useEffect, useState, type CSSProperties, type ReactNode } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { SongaBrand } from '../components/SongaBrand';
import { useFeedback } from '../components/FeedbackProvider';
import { canAccess } from '../api/auth';
import { useAuth } from './AuthContext';

type NavigationNode = {
  id: string;
  label: string;
  icon: string;
  permission?: string;
  to?: string;
  active?: boolean;
  children?: readonly NavigationNode[];
};

export const navigation: readonly NavigationNode[] = [
  { id: 'trabajo-social', label: 'Trabajo Social', icon: '⌂', children: [
    { id: 'inicio', label: 'Inicio', icon: '⌂', permission: 'DASHBOARD', to: '/trabajo-social/inicio' },
    { id: 'actividades', label: 'Actividades', icon: '✓', children: [
      { id: 'actividades-tabla', label: 'Tabla de actividades', icon: '☷', permission: 'ACTIVIDADES', to: '/trabajo-social/actividades' },
      { id: 'actividades-registrar', label: 'Registrar actividad', icon: '+', permission: 'ACTIVIDADES', to: '/trabajo-social/actividades/registrar' },
      { id: 'actividades-formularios', label: 'Formularios', icon: '▤', permission: 'FORMULARIOS', to: '/trabajo-social/actividades/formularios' },
    ] },
    { id: 'correos', label: 'Correos y seguimiento', icon: '✉', permission: 'CORREOS', to: '/trabajo-social/correos' },
    { id: 'departamento-medico', label: 'Departamento Médico', icon: '✚', children: [
      { id: 'medico-atenciones', label: 'Atenciones', icon: '+', permission: 'ATENCIONES', to: '/trabajo-social/departamento-medico/atenciones' },
      { id: 'riesgos', label: 'Riesgos de trabajo', icon: '!', permission: 'RIESGOS_TRABAJO', to: '/trabajo-social/departamento-medico/riesgos' },
      { id: 'ausentismos', label: 'Ausentismos', icon: '◷', permission: 'AUSENTISMO', to: '/trabajo-social/departamento-medico/ausentismos' },
      { id: 'accidentes', label: 'Accidentes', icon: '⚠', permission: 'ACCIDENTES', to: '/trabajo-social/departamento-medico/accidentes' },
      { id: 'medico-formularios', label: 'Formularios', icon: '▤', permission: 'FORMULARIOS', to: '/trabajo-social/departamento-medico/formularios' },
    ] },
    { id: 'produccion', label: 'Producción', icon: '▥', children: [
      { id: 'produccion-atenciones', label: 'Atenciones', icon: '+', permission: 'ATENCIONES', to: '/trabajo-social/produccion/atenciones' },
      { id: 'produccion-recorridos', label: 'Recorridos', icon: '↗', permission: 'RECORRIDOS', to: '/trabajo-social/produccion/recorridos' },
      { id: 'produccion-novedades', label: 'Novedades de planta', icon: '!', permission: 'NOVEDADES', to: '/trabajo-social/produccion/novedades' },
      { id: 'produccion-formularios', label: 'Formularios', icon: '▤', permission: 'FORMULARIOS', to: '/trabajo-social/produccion/formularios' },
    ] },
    { id: 'oficina', label: 'Oficina', icon: '▣', children: [
      { id: 'beneficios', label: 'Beneficios', icon: '★', permission: 'BENEFICIOS', to: '/trabajo-social/oficina/beneficios' },
      { id: 'oficina-atenciones', label: 'Atenciones', icon: '+', permission: 'ATENCIONES', to: '/trabajo-social/oficina/atenciones' },
      { id: 'prestamos', label: 'Préstamos', icon: '$', permission: 'PRESTAMOS', to: '/trabajo-social/oficina/prestamos' },
      { id: 'seguro', label: 'Seguro', icon: '◈', permission: 'SEGUROS', to: '/trabajo-social/oficina/seguro' },
      { id: 'oficina-formularios', label: 'Formularios', icon: '▤', permission: 'FORMULARIOS', to: '/trabajo-social/oficina/formularios' },
    ] },
  ] },
  { id: 'repositorio-formularios', label: 'Repositorio de formularios', icon: '▤', permission: 'FORMULARIOS', to: '/formularios' },
  { id: 'administracion', label: 'Administración', icon: '⚙', permission: 'ADMINISTRACION', children: [
    { id: 'admin-usuarios', label: 'Usuarios', icon: '♙', permission: 'ADMINISTRACION', to: '/admin/usuarios' },
    { id: 'admin-permisos', label: 'Roles y permisos', icon: '⚙', permission: 'ADMINISTRACION', to: '/admin/permisos' },
  ] },
];

function isCurrentPath(pathname: string, to: string): boolean {
  return to === '/' ? pathname === '/' : pathname === to || pathname.startsWith(`${to}/`);
}

export function activeAncestorIds(nodes: readonly NavigationNode[], pathname: string): Set<string> {
  const ancestors = new Set<string>();
  function visit(node: NavigationNode, parentIds: string[]) {
    if (node.to && node.active !== false && isCurrentPath(pathname, node.to)) parentIds.forEach((id) => ancestors.add(id));
    node.children?.forEach((child) => visit(child, [...parentIds, node.id]));
  }
  nodes.forEach((node) => visit(node, []));
  return ancestors;
}

function isVisible(node: NavigationNode, usuario: ReturnType<typeof useAuth>['usuario']): boolean {
  if (node.children?.some((child) => isVisible(child, usuario))) return true;
  return !node.children && Boolean(node.permission && canAccess(usuario, node.permission, 'read'));
}

function SearchIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6.5" /><path d="m16 16 4 4" /></svg>;
}

function BellIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" /><path d="M10 21h4" /></svg>;
}

export function Layout() {
  const { usuario, logout } = useAuth();
  const { notify } = useFeedback();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
  const [loggingOut, setLoggingOut] = useState(false);
  const showNestedNavigation = !collapsed || mobileOpen;
  const userInitial = usuario?.nombre?.trim().charAt(0).toUpperCase() || 'U';
  const trabajoSocial = navigation[0];
  const inicio = trabajoSocial.children?.find((node) => node.id === 'inicio');
  const trabajoSocialGroups = trabajoSocial.children?.filter((node) => node.id !== 'inicio') ?? [];

  useEffect(() => {
    setMobileOpen(false);
    const routeAncestors = activeAncestorIds(navigation, location.pathname);
    setExpanded((current) => {
      const next = new Set(current);
      routeAncestors.forEach((id) => next.add(id));
      return next;
    });
  }, [location.pathname]);

  function toggleNode(id: string) {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  function renderNode(node: NavigationNode, depth = 0): ReactNode {
    if (!isVisible(node, usuario)) return null;
    const hasChildren = Boolean(node.children?.some((child) => isVisible(child, usuario)));
    const isExpanded = expanded.has(node.id);
    const indent = { '--nav-depth': depth } as CSSProperties;

    if (hasChildren) {
      return <li key={node.id} className="nav-tree-item">
        <button type="button" className="sidebar-tree-toggle" style={indent} onClick={() => toggleNode(node.id)}
                aria-expanded={isExpanded} aria-controls={`nav-group-${node.id}`}>
          <span className="nav-icon" aria-hidden="true">{node.icon}</span><span className="nav-label">{node.label}</span>
          <span className="nav-disclosure" aria-hidden="true">{isExpanded ? '⌄' : '›'}</span>
        </button>
        {showNestedNavigation && isExpanded && <ul id={`nav-group-${node.id}`} className="sidebar-tree sidebar-tree-nested">
          {node.children?.map((child) => renderNode(child, depth + 1))}
        </ul>}
      </li>;
    }

    if (!node.to) return <li key={node.id}><span className="sidebar-tree-unavailable" style={indent} aria-disabled="true">
      <span className="nav-icon" aria-hidden="true">{node.icon}</span><span className="nav-label">{node.label}</span>
    </span></li>;

    const content = <><span className="nav-icon" aria-hidden="true">{node.icon}</span><span className="nav-label">{node.label}</span></>;
    return <li key={node.id}>{node.active === false
      ? <Link className="sidebar-tree-link" style={indent} to={node.to}>{content}</Link>
      : <NavLink className="sidebar-tree-link" style={indent} to={node.to} end={node.to === '/'}>{content}</NavLink>}
    </li>;
  }

  async function handleLogout() {
    setLoggingOut(true);
    try {
      await logout();
    } catch {
      notify('No fue posible cerrar la sesión. Intente nuevamente.', 'error');
    } finally {
      setLoggingOut(false);
    }
  }

  return (
    <div className={`page app-shell ui-shell-v2${collapsed ? ' sidebar-collapsed' : ''}${mobileOpen ? ' mobile-nav-open' : ''}`}>
      <header className="topbar">
        <button type="button" className="mobile-menu-button" aria-label={mobileOpen ? 'Cerrar menú' : 'Abrir menú'} aria-expanded={mobileOpen}
                aria-controls="sidebar-navigation" onClick={() => setMobileOpen((open) => !open)}>☰</button>
        <Link to="/busqueda" className="topbar-search" aria-label="Abrir búsqueda consolidada">
          <SearchIcon />
          <span>Buscar personas, casos, actividades...</span>
        </Link>
        <div className="topbar-actions">
          <span className="topbar-notification" aria-label="Centro de notificaciones"><BellIcon /></span>
          <span className="topbar-divider" aria-hidden="true" />
          <span className="user-avatar" aria-hidden="true">{userInitial}</span>
          <div className="header-user">
            <span><strong>{usuario?.nombre}</strong><small>{usuario?.rol_nombre}</small></span>
            <button className="logout-button" onClick={() => void handleLogout()} disabled={loggingOut} title="Cerrar sesión">
              {loggingOut ? 'Saliendo…' : 'Salir'}
            </button>
          </div>
        </div>
      </header>

      <button className="sidebar-backdrop" type="button" aria-label="Cerrar menú" onClick={() => setMobileOpen(false)} />

      <aside id="sidebar-navigation" className="sidebar" aria-label="Navegación principal">
        <div className="sidebar-brand-block">
          <Link to="/" className="sidebar-brand-link"><SongaBrand inverse /></Link>
        </div>
        <nav>
          <ul className="sidebar-tree sidebar-tree-root">
            {inicio ? renderNode(inicio) : null}
            {isVisible(trabajoSocial, usuario) && (
              <li className="sidebar-section-heading" aria-hidden={collapsed && !mobileOpen}>
                <span className="nav-icon" aria-hidden="true">⌂</span>
                <span className="nav-label">Trabajo Social</span>
                <span className="nav-disclosure" aria-hidden="true">⌄</span>
              </li>
            )}
            {trabajoSocialGroups.map((node) => renderNode(node))}
            {navigation.slice(1).map((node) => renderNode(node))}
          </ul>
        </nav>
        <div className="sidebar-purpose">
          <p>“Juntos transformamos vidas”</p>
          <span />
          <strong>SONGA</strong>
          <small>Trabajo con propósito</small>
        </div>
        <button type="button" className="sidebar-toggle" onClick={() => setCollapsed((value) => !value)}
                aria-label={collapsed ? 'Expandir menú' : 'Contraer menú'} aria-expanded={!collapsed}>
          <span aria-hidden="true">{collapsed ? '›' : '‹'}</span><span className="nav-label">Contraer menú</span>
        </button>
      </aside>

      <main className="app-main">
        <Outlet />
      </main>
      <footer className="app-footer">
        <span>SONGA · Trabajo Social · Sistema Integral de Gestión</span><span>Hora oficial: Ecuador continental</span>
      </footer>
    </div>
  );
}
