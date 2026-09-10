import { get, post } from './client';

export type PermissionAction = 'create' | 'read' | 'edit' | 'delete' | 'sensitive' | 'export';
export type PermissionMatrix = Record<string, Partial<Record<PermissionAction, boolean>>>;

export interface UsuarioActual {
  id_usuario: string;
  correo: string;
  nombre: string;
  rol_id: string;
  rol_nombre: string;
  permisos: PermissionMatrix;
}

export function canAccess(
  usuario: UsuarioActual | null | undefined, module: string, action: PermissionAction,
): boolean {
  return Boolean(usuario?.permisos?.[module]?.[action]);
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
