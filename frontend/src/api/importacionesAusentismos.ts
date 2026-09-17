import { get, post, postForm } from './client';

export interface LoteAusentismo {
  id_lote: string; nombre_archivo: string; usuario_id: string; estado: 'ANALIZADO' | 'CONFIRMADO';
  total_filas: number; filas_validas: number; filas_con_error: number; filas_duplicadas: number;
  filas_importadas: number; fecha_creacion: string | null; fecha_actualizacion: string | null; version: number;
}
export interface FilaPrevisualizacion {
  fila: number; cedula: string | null; persona_id: string | null; fecha_inicio: string | null; fecha_fin: string | null;
  tipo_ausentismo: string | null; motivo: string | null; observacion: string | null;
  estado: 'VALIDA' | 'DUPLICADA' | 'ERROR'; errores: string[];
}
export interface ErrorLoteAusentismo { id_error: string; numero_fila: number; codigo: string; mensaje: string; datos_fila: string | null; }
export interface Pagina<T> { items: T[]; total: number; limite: number; offset: number; }
export interface AnalisisAusentismo { lote: LoteAusentismo; puede_confirmarse: boolean; previsualizacion: FilaPrevisualizacion[]; }

const root = '/importaciones/ausentismos';
export function analizarAusentismos(archivo: File): Promise<AnalisisAusentismo> {
  const body = new FormData(); body.append('archivo', archivo); return postForm(`${root}/analizar`, body);
}
export const confirmarLoteAusentismos = (id: string): Promise<LoteAusentismo> => post(`${root}/${id}/confirmar`);
export const listarLotesAusentismos = (params: URLSearchParams): Promise<Pagina<LoteAusentismo>> => get(`${root}?${params}`);
export const obtenerLoteAusentismos = (id: string): Promise<LoteAusentismo> => get(`${root}/${id}`);
export const listarErroresLoteAusentismos = (id: string, params: URLSearchParams): Promise<Pagina<ErrorLoteAusentismo>> => get(`${root}/${id}/errores?${params}`);
