import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from './AuthContext';

/**
 * Solo oculta rutas para la experiencia de usuario; la autorización real ocurre siempre
 * en el servidor (cada endpoint valida sesión y permisos por su cuenta).
 */
export function RequireAuth() {
  const { usuario, cargando } = useAuth();
  if (cargando) return <p className="loading-message">Cargando…</p>;
  if (!usuario) return <Navigate to="/login" replace />;
  return <Outlet />;
}
