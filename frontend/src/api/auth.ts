import { get, post } from './client';

export interface UsuarioActual {
  id_usuario: string;
  correo: string;
  nombre: string;
  rol_id: string;
  rol_nombre: string;
}

/**
 * POST /auth/login es el login temporal de desarrollo (app/api/auth.py): solo correo, sin
 * contraseña ni Google OAuth. Se reemplaza cuando se cierre MIGRACION_FASE_1.md §10.
 */
export function login(correo: string): Promise<UsuarioActual> {
  return post<UsuarioActual>('/auth/login', { correo });
}

export function logout(): Promise<{ status: string }> {
  return post<{ status: string }>('/auth/logout');
}

export function fetchCurrentUser(): Promise<UsuarioActual> {
  return get<UsuarioActual>('/auth/me');
}
