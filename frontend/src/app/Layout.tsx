import { useEffect, useState } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { SongaBrand } from '../components/SongaBrand';
import { useFeedback } from '../components/FeedbackProvider';
import { canAccess } from '../api/auth';
import { useAuth } from './AuthContext';

const gestion = [
  ['/', 'Inicio', '⌂', 'DASHBOARD'], ['/casos', 'Casos', '◇', 'CASOS'], ['/atenciones', 'Atenciones', '+', 'ATENCIONES'],
  ['/novedades', 'Novedades', '!', 'NOVEDADES'], ['/recorridos', 'Recorridos', '↗', 'RECORRIDOS'],
  ['/personas', 'Personas', '♙', 'PERSONAS'], ['/formularios', 'Formularios', '▤', 'FORMULARIOS'],
  ['/busqueda', 'Búsqueda', '⌕', 'BUSQUEDA'],
] as const;

export function Layout() {
  const { usuario, logout } = useAuth();
  const { notify } = useFeedback();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);

  useEffect(() => { setMobileOpen(false); }, [location.pathname]);

  function navItem([to, label, icon]: readonly [string, string, string]) {
    return (
      <NavLink key={to} to={to} end={to === '/'} title={collapsed ? label : undefined}>
        <span className="nav-icon" aria-hidden="true">{icon}</span><span className="nav-label">{label}</span>
      </NavLink>
    );
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
    <div className={`page app-shell${collapsed ? ' sidebar-collapsed' : ''}${mobileOpen ? ' mobile-nav-open' : ''}`}>
      <header className="topbar">
        <button type="button" className="mobile-menu-button" aria-label={mobileOpen ? 'Cerrar menú' : 'Abrir menú'} aria-expanded={mobileOpen}
                aria-controls="sidebar-navigation" onClick={() => setMobileOpen((open) => !open)}>☰</button>
        <Link to="/" className="brand">
          <SongaBrand compact />
        </Link>
        <div className="header-user">
          <span><strong>{usuario?.nombre}</strong><small>{usuario?.rol_nombre}</small></span>
          <button className="logout-button" onClick={() => void handleLogout()} disabled={loggingOut} title="Cerrar sesión">
            {loggingOut ? 'Saliendo…' : 'Salir'}
          </button>
        </div>
      </header>
      <button className="sidebar-backdrop" type="button" aria-label="Cerrar menú" onClick={() => setMobileOpen(false)} />
      <aside id="sidebar-navigation" className="sidebar" aria-label="Navegación principal">
        <button type="button" className="sidebar-toggle" onClick={() => setCollapsed((value) => !value)}
                aria-label={collapsed ? 'Expandir menú' : 'Contraer menú'} aria-expanded={!collapsed}>
          <span aria-hidden="true">{collapsed ? '›' : '‹'}</span><span className="nav-label">Contraer menú</span>
        </button>
        <nav>
          <p className="nav-group-title">Gestión</p>
          {gestion.filter(([, , , module]) => canAccess(usuario, module, 'read')).map(([to, label, icon]) => navItem([to, label, icon]))}
          {canAccess(usuario, 'ADMINISTRACION', 'read') && (
            <>
              <p className="nav-group-title">Administración</p>
              {navItem(['/admin/usuarios', 'Usuarios', '♙'])}
              {navItem(['/admin/permisos', 'Roles y permisos', '⚙'])}
            </>
          )}
        </nav>
      </aside>
      <main className="app-main">
        <Outlet />
      </main>
      <footer className="app-footer">
        <span>SONGA · Sistema Integral de Gestión de Trabajo Social</span><span>Hora oficial: Ecuador continental</span>
      </footer>
    </div>
  );
}
