import { get, patch, post, put } from './client';

export interface UsuarioAdmin {
  id_usuario: string;
  correo: string;
  nombre: string;
  rol_id: string;
  estado: string;
  activo: boolean;
  eliminado: boolean;
  version: number;
}

export interface RolAdmin {
  id_rol: string;
  nombre: string;
  descripcion: string | null;
}

export interface PermisoAdmin {
  id_permiso: string;
  rol_id: string;
  modulo: string;
  create: boolean;
  read: boolean;
  edit: boolean;
  delete: boolean;
  sensitive: boolean;
  export: boolean;
  version: number;
}

export interface DatosAdministracion {
  usuarios: UsuarioAdmin[];
  roles: RolAdmin[];
  permisos: PermisoAdmin[];
}

export interface CrearUsuarioPayload {
  correo: string;
  nombre: string;
  rol_id: string;
  password: string;
}

export function listarAdministracion(): Promise<DatosAdministracion> {
  return get<DatosAdministracion>('/admin/usuarios');
}

export function crearUsuario(payload: CrearUsuarioPayload): Promise<UsuarioAdmin> {
  return post<UsuarioAdmin>('/admin/usuarios', payload);
}

export function actualizarUsuario(
  idUsuario: string, rolId: string, estado: string, expectedVersion: number,
): Promise<UsuarioAdmin> {
  return patch<UsuarioAdmin>(`/admin/usuarios/${idUsuario}`, { rol_id: rolId, estado, expected_version: expectedVersion });
}

export function actualizarPermiso(
  rolId: string, modulo: string, derechos: Partial<Record<string, boolean>>, expectedVersion: number,
): Promise<PermisoAdmin> {
  return put<PermisoAdmin>(`/admin/roles/${rolId}/permisos/${modulo}`, { derechos, expected_version: expectedVersion });
}
