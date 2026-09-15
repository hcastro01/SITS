import { get, patch, post } from './client';

export type RiesgoEstado = 'ABIERTO' | 'EN_SEGUIMIENTO' | 'CERRADO';

export interface RiesgoTrabajo {
  id_caso: string;
  codigo_caso: string;
  tipo_caso: 'RIESGOS_TRABAJO';
  persona_id: string;
  persona: string | null;
  cedula: string | null;
  area: string | null;
  fecha_apertura: string | null;
  responsable: string | null;
  estado_caso: RiesgoEstado;
  prioridad: string | null;
  resultado: string | null;
  resumen: string | null;
  ultimo_seguimiento: string | null;
  fecha_creacion: string | null;
  fecha_actualizacion: string | null;
  fecha_cierre: string | null;
  motivo_cierre: string | null;
  registrado_por: string | null;
  version: number;
}

export interface RiesgoCreate {
  persona_id: string;
  fecha_apertura: string;
  responsable?: string;
  estado_caso: RiesgoEstado;
  prioridad?: string;
  resultado: string;
}

export interface RiesgoUpdate {
  expected_version: number;
  responsable?: string;
  estado_caso?: RiesgoEstado;
  prioridad?: string;
  resultado?: string;
}

export function listarRiesgos(params: URLSearchParams) {
  return get<{ items: RiesgoTrabajo[]; total: number; limite: number; offset: number }>(`/riesgos-trabajo?${params}`);
}

export const obtenerRiesgo = (id: string) => get<RiesgoTrabajo>(`/riesgos-trabajo/${id}`);
export const crearRiesgo = (payload: RiesgoCreate) => post<RiesgoTrabajo>('/riesgos-trabajo', payload);
export const actualizarRiesgo = (id: string, payload: RiesgoUpdate) => patch<RiesgoTrabajo>(`/riesgos-trabajo/${id}`, payload);
export const cerrarRiesgo = (id: string, payload: { expected_version: number; fecha_cierre_caso?: string; responsable?: string; motivo_cierre: string; resultado_final?: string }) =>
  post(`/riesgos-trabajo/${id}/cierres`, payload);
