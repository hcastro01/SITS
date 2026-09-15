import { get, patch, post } from './client';

export type ActivityStatus = 'PENDIENTE' | 'EN_PROCESO' | 'COMPLETADA';
export type ActivityDateType = 'PROGRAMADA' | 'LIMITE';
export interface Actividad { id_actividad: string; nombre: string; descripcion: string; responsable_id: string; responsable: string | null; tipo_fecha: ActivityDateType; fecha_objetivo: string; estado: ActivityStatus; persona_id: string | null; persona: string | null; cedula: string | null; area: string | null; registrado_por: string | null; fecha_creacion: string | null; fecha_finalizacion: string | null; vencida: boolean; version: number; }
export interface ActivityOptions { usuarios: { id: string; nombre: string }[]; personas: { id: string; nombre: string; cedula: string | null; area: string | null }[]; }
export interface ActivityPayload { nombre: string; descripcion: string; responsable_id: string; tipo_fecha: ActivityDateType; fecha_objetivo: string; estado: ActivityStatus; persona_id: string | null; }
export function listActivities(params: URLSearchParams): Promise<{ items: Actividad[]; total: number; limite: number; offset: number }> { return get(`/actividades?${params}`); }
export const activityOptions = (): Promise<ActivityOptions> => get('/actividades/opciones');
export const createActivity = (data: ActivityPayload): Promise<Actividad> => post('/actividades', data);
export const updateActivity = (id: string, data: ActivityPayload & { expected_version: number }): Promise<Actividad> => patch(`/actividades/${id}`, data);
export const archiveActivity = (id: string, expected_version: number, motivo: string): Promise<Actividad> => post(`/actividades/${id}/archivar`, { expected_version, motivo });
