import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from './AuthContext';

export function Layout() {
  const { usuario, logout } = useAuth();

  return (
    <div className="page app-shell">
      <header>
        <a href="/" className="brand">
          <span className="mark" aria-hidden="true">TS</span>
          <span>Trabajo Social<small>Sistema integral de gestión</small></span>
        </a>
        <nav className="main-nav">
          <NavLink to="/" end>Inicio</NavLink>
          <NavLink to="/casos">Casos</NavLink>
          <NavLink to="/formularios">Formularios</NavLink>
          <NavLink to="/busqueda">Búsqueda</NavLink>
        </nav>
        <div className="header-user">
          <span>{usuario?.nombre} · {usuario?.rol_nombre}</span>
          <button className="logout-button" onClick={() => logout()}>Cerrar sesión</button>
        </div>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
      <footer>
        Sistema Integral de Gestión de Trabajo Social<span>Inicio de la migración</span>
      </footer>
    </div>
  );
}
