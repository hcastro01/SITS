import { get, post } from './client';
export type AccidenteEstado = 'ABIERTO' | 'EN_SEGUIMIENTO' | 'CERRADO';
export interface Accidente { id_accidente: string; persona_id: string; persona: string; cedula: string | null; area: string | null; fecha_accidente: string; clasificacion: string; estado: AccidenteEstado; descripcion: string; observacion: string | null; fecha_registro: string | null; origen: string; lote_id: string | null; lote_nombre_archivo: string | null; registrado_por: string | null; version: number; }
export interface LoteAccidente { id_lote: string; nombre_archivo: string; usuario_id: string; estado: string; total_filas: number; filas_validas: number; filas_con_error: number; filas_duplicadas: number; filas_importadas: number; fecha_creacion: string | null; }
export interface IncidenciaAccidente { id_error: string; numero_fila: number; codigo: string; mensaje: string; datos_fila: string | null; }
export const listarAccidentes = (params: URLSearchParams) => get<{items: Accidente[]; total: number; limite: number; offset: number}>(`/accidentes?${params}`);
export const obtenerAccidente = (id: string) => get<Accidente>(`/accidentes/${id}`);
export const crearAccidente = (data: {persona_id: string; fecha_accidente: string; clasificacion: string; descripcion: string; estado: AccidenteEstado; observacion: string | null}) => post<Accidente>('/accidentes', data);
export async function analizarArchivoAccidentes(file: File): Promise<{lote: LoteAccidente; puede_confirmarse: boolean; previsualizacion: unknown[]}> { const response = await fetch('/api/v1/importaciones/accidentes/analizar', { method: 'POST', credentials: 'include', body: (() => { const body = new FormData(); body.append('archivo', file); return body; })() }); if (!response.ok) throw new Error((await response.json()).message ?? 'No fue posible analizar el archivo.'); return response.json(); }
export const confirmarLoteAccidentes = (id: string) => post<LoteAccidente>(`/importaciones/accidentes/${id}/confirmar`, {});
export const listarLotesAccidentes = (params: URLSearchParams) => get<{items: LoteAccidente[]; total: number}>(`/importaciones/accidentes?${params}`);
export const listarIncidenciasAccidente = (id: string) => get<{items: IncidenciaAccidente[]; total: number}>(`/importaciones/accidentes/${id}/errores`);
