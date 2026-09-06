import { get, patch, post } from './client';

export interface Caso {
  id_caso: string;
  codigo_caso: string;
  fecha_apertura: string | null;
  id_persona: string | null;
  colaborador: string | null;
  responsable: string | null;
  tipo_caso: string | null;
  subtipo_caso: string | null;
  prioridad: string | null;
  nivel_sensibilidad: string | null;
  estado_caso: string | null;
  tipo_gestion: string | null;
  tipo_evento: string | null;
  area: string | null;
  turno: string | null;
  condicion_laboral: string | null;
  restriccion: boolean;
  fecha_inicio_restriccion: string | null;
  fecha_cierre: string | null;
  motivo_cierre: string | null;
  resultado: string | null;
  evidencias: string | null;
  version: number;
  activo: boolean;
  eliminado: boolean;
  sensible: boolean;
}

export interface Seguimiento {
  id_seguimiento: string;
  fecha: string | null;
  responsable: string | null;
  descripcion: string | null;
  hora: string | null;
  tipo_seguimiento: string | null;
  canal: string | null;
  tecnica: string | null;
  resultado: string | null;
  proxima_accion: string | null;
  fecha_proxima_accion: string | null;
  estado: string | null;
  version: number;
}

export interface Compromiso {
  id_compromiso: string;
  id_seguimiento: string | null;
  fecha_creacion_compromiso: string | null;
  responsable: string | null;
  descripcion: string | null;
  fecha_limite: string | null;
  estado: string | null;
  fecha_cumplimiento: string | null;
  observacion: string | null;
  version: number;
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

export function listarCasos(): Promise<Caso[]> {
  return get<Caso[]>('/casos');
}

export function obtenerCaso(idCaso: string): Promise<Caso> {
  return get<Caso>(`/casos/${idCaso}`);
}

export function crearCaso(datos: Record<string, unknown>): Promise<Caso> {
  return post<Caso>('/casos', datos);
}

export function actualizarCaso(idCaso: string, datos: Record<string, unknown>): Promise<Caso> {
  return patch<Caso>(`/casos/${idCaso}`, datos);
}

export function historialCaso(idCaso: string): Promise<EventoHistorial[]> {
  return get<EventoHistorial[]>(`/casos/${idCaso}/historial`);
}

export function agregarSeguimiento(idCaso: string, datos: Record<string, unknown>): Promise<Seguimiento> {
  return post<Seguimiento>(`/casos/${idCaso}/seguimientos`, datos);
}

export function listarSeguimientos(idCaso: string): Promise<Seguimiento[]> {
  return get<Seguimiento[]>(`/casos/${idCaso}/seguimientos`);
}

export function listarCompromisos(idCaso: string): Promise<Compromiso[]> {
  return get<Compromiso[]>(`/casos/${idCaso}/compromisos`);
}

export function agregarDerivacion(idCaso: string, datos: Record<string, unknown>) {
  return post(`/casos/${idCaso}/derivaciones`, datos);
}

export function agregarCompromiso(idCaso: string, datos: Record<string, unknown>) {
  return post(`/casos/${idCaso}/compromisos`, datos);
}

export function cerrarCaso(idCaso: string, datos: Record<string, unknown>) {
  return post(`/casos/${idCaso}/cierres`, datos);
}
