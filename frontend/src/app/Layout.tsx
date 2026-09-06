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
          <NavLink to="/atenciones">Atenciones</NavLink>
          <NavLink to="/novedades">Novedades</NavLink>
          <NavLink to="/recorridos">Recorridos</NavLink>
          <NavLink to="/personas">Personas</NavLink>
          <NavLink to="/formularios">Formularios</NavLink>
          <NavLink to="/busqueda">Búsqueda</NavLink>
          {usuario?.rol_id === 'ROLE_ADMIN' && (
            <>
              <NavLink to="/admin/usuarios">Usuarios</NavLink>
              <NavLink to="/admin/permisos">Permisos</NavLink>
            </>
          )}
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
