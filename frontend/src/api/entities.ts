import { get, patch, post } from './client';

export interface EntityRecord {
  version: number;
  activo: boolean;
  eliminado: boolean;
  [key: string]: unknown;
}

export interface EventoHistorial {
  campo: string;
  accion: string;
  valor_anterior: string | null;
  valor_nuevo: string | null;
  usuario: string;
  fecha_hora: string;
  motivo: string | null;
}

/**
 * Cliente genérico para las entidades que comparten forma en el backend
 * (app/api/simple_entity_router.py y app/api/atenciones.py): listar, crear, obtener,
 * editar, eliminar lógicamente, restaurar e historial.
 */
export function createEntityClient(basePath: string, idField: string) {
  return {
    idField,
    basePath,
    list: (incluirEliminados = false): Promise<EntityRecord[]> =>
      get<EntityRecord[]>(`${basePath}?incluir_eliminados=${incluirEliminados}`),
    get: (id: string): Promise<EntityRecord> => get<EntityRecord>(`${basePath}/${id}`),
    create: (datos: Record<string, unknown>): Promise<EntityRecord> => post<EntityRecord>(basePath, datos),
    update: (id: string, datos: Record<string, unknown>): Promise<EntityRecord> =>
      patch<EntityRecord>(`${basePath}/${id}`, datos),
    softDelete: (id: string, datos: Record<string, unknown>): Promise<EntityRecord> =>
      post<EntityRecord>(`${basePath}/${id}/eliminacion`, datos),
    restore: (id: string): Promise<EntityRecord> => post<EntityRecord>(`${basePath}/${id}/restauracion`, {}),
    history: (id: string): Promise<EventoHistorial[]> => get<EventoHistorial[]>(`${basePath}/${id}/historial`),
  };
}

export type EntityClient = ReturnType<typeof createEntityClient>;

export const atencionesApi = createEntityClient('/atenciones', 'id_atencion');
export const novedadesApi = createEntityClient('/novedades', 'id_novedad');
export const recorridosApi = createEntityClient('/recorridos', 'id_recorrido');
export const personasApi = createEntityClient('/personas', 'id_persona');
