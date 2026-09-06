import { get, post } from './client';

export interface UsuarioActual {
  id_usuario: string;
  correo: string;
  nombre: string;
  rol_id: string;
  rol_nombre: string;
}

export function login(correo: string, password?: string): Promise<UsuarioActual> {
  return post<UsuarioActual>('/auth/login', { correo, password });
}

export function logout(): Promise<{ status: string }> {
  return post<{ status: string }>('/auth/logout');
}

export function fetchCurrentUser(): Promise<UsuarioActual> {
  return get<UsuarioActual>('/auth/me');
}
