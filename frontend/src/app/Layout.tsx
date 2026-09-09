import { useEffect, useState } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { SongaBrand } from '../components/SongaBrand';
import { useAuth } from './AuthContext';

const gestion = [
  ['/', 'Inicio', '⌂'], ['/casos', 'Casos', '◇'], ['/atenciones', 'Atenciones', '+'],
  ['/novedades', 'Novedades', '!'], ['/recorridos', 'Recorridos', '↗'],
  ['/personas', 'Personas', '♙'], ['/formularios', 'Formularios', '▤'], ['/busqueda', 'Búsqueda', '⌕'],
] as const;

export function Layout() {
  const { usuario, logout } = useAuth();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => { setMobileOpen(false); }, [location.pathname]);

  function navItem([to, label, icon]: readonly [string, string, string]) {
    return (
      <NavLink key={to} to={to} end={to === '/'} title={collapsed ? label : undefined}>
        <span className="nav-icon" aria-hidden="true">{icon}</span><span className="nav-label">{label}</span>
      </NavLink>
    );
  }

  return (
    <div className={`page app-shell${collapsed ? ' sidebar-collapsed' : ''}${mobileOpen ? ' mobile-nav-open' : ''}`}>
      <header className="topbar">
        <button type="button" className="mobile-menu-button" aria-label="Abrir menú" aria-expanded={mobileOpen}
                aria-controls="sidebar-navigation" onClick={() => setMobileOpen((open) => !open)}>☰</button>
        <Link to="/" className="brand">
          <SongaBrand compact />
        </Link>
        <div className="header-user">
          <span><strong>{usuario?.nombre}</strong><small>{usuario?.rol_nombre}</small></span>
          <button className="logout-button" onClick={() => logout()} title="Cerrar sesión">Salir</button>
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
          {gestion.map(navItem)}
          {usuario?.rol_id === 'ROLE_ADMIN' && (
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
