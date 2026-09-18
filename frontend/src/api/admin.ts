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
  puede_eliminar_usuarios?: boolean;
}

export interface CrearUsuarioPayload {
  correo: string;
  nombre: string;
  rol_id: string;
  password: string;
}

export interface ActualizarUsuarioPayload {
  nombre: string;
  correo: string;
  rol_id: string;
  estado: 'ACTIVO' | 'INACTIVO';
  expected_version: number;
}

export function listarAdministracion(incluirEliminados = false): Promise<DatosAdministracion> {
  return get<DatosAdministracion>(`/admin/usuarios${incluirEliminados ? '?incluir_eliminados=true' : ''}`);
}

export function crearUsuario(payload: CrearUsuarioPayload): Promise<UsuarioAdmin> {
  return post<UsuarioAdmin>('/admin/usuarios', payload);
}

export function actualizarUsuario(idUsuario: string, payload: ActualizarUsuarioPayload): Promise<UsuarioAdmin> {
  return patch<UsuarioAdmin>(`/admin/usuarios/${idUsuario}`, payload);
}

export function restablecerPasswordUsuario(
  idUsuario: string, password: string, expectedVersion: number,
): Promise<UsuarioAdmin> {
  return put<UsuarioAdmin>(`/admin/usuarios/${idUsuario}/password`, { password, expected_version: expectedVersion });
}

export function eliminarUsuario(idUsuario: string, expectedVersion: number, motivo: string): Promise<UsuarioAdmin> {
  return post<UsuarioAdmin>(`/admin/usuarios/${idUsuario}/eliminacion`, {
    expected_version: expectedVersion, motivo,
  });
}

export function restaurarUsuario(idUsuario: string, expectedVersion: number): Promise<UsuarioAdmin> {
  return post<UsuarioAdmin>(`/admin/usuarios/${idUsuario}/restauracion`, { expected_version: expectedVersion });
}

export function actualizarPermiso(
  rolId: string, modulo: string, derechos: Partial<Record<string, boolean>>, expectedVersion: number,
): Promise<PermisoAdmin> {
  return put<PermisoAdmin>(`/admin/roles/${rolId}/permisos/${modulo}`, { derechos, expected_version: expectedVersion });
}
