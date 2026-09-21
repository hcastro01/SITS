import { get, post, postForBlobResponse, postForm, type BlobResponse } from './client';

export type EstadoRequerimiento = 'PENDIENTE' | 'EN_PROCESO' | 'EN_ESPERA' | 'RESUELTO' | 'CERRADO';
export type EstadoClasificacion = 'CLASIFICADO' | 'REVISION';

export interface CorreoResumen {
  id_correo: string;
  id_externo_correo: string;
  asunto: string;
  remitente: string | null;
  destinatarios: string | null;
  cc: string | null;
  fecha_recibido: string | null;
  importancia: string | null;
  tiene_adjuntos: boolean;
  leido: boolean;
  categoria_macro: string | null;
  categoria_nombre: string | null;
  estado_categoria: 'VALIDA' | 'SIN_CATEGORIA' | 'DESCONOCIDA' | 'OTROS';
  regla_disparadora: string | null;
  estado_clasificacion: EstadoClasificacion;
  estado_requerimiento: EstadoRequerimiento;
  responsable_seguimiento: string | null;
  origen: string | null;
  fecha_creacion: string | null;
  fecha_actualizacion: string | null;
  version: number;
}

export interface SeguimientoCorreo {
  id_seguimiento: string;
  fecha_seguimiento: string | null;
  detalle_seguimiento: string;
  seguimiento_por: string | null;
  estado_requerimiento: EstadoRequerimiento;
}

export interface CorreoDetalle extends CorreoResumen { cuerpo: string | null; }
export interface DetalleCorreoRespuesta { correo: CorreoDetalle; seguimientos: SeguimientoCorreo[]; }
export interface PaginaCorreos { items: CorreoResumen[]; total: number; limite: number; offset: number; }
export interface ResumenCorreos { total: number; pendientes: number; en_seguimiento: number; sin_clasificar: number; por_categoria: { valor: string; total: number }[]; por_origen: { valor: string; total: number }[]; principales_remitentes: { valor: string; total: number }[]; }
export interface LoteCorreo { id_lote: string; nombre_archivo: string; estado: string; origen: string; total_filas: number; filas_procesadas: number; filas_clasificadas: number; filas_revision: number; filas_importadas: number; filas_duplicadas: number; filas_omitidas: number; filas_error: number; duracion_ms: number | null; fecha_creacion: string | null; version: number; }
export interface CorreoPrevisualizacion { id_externo_correo: string; asunto: string; remitente: string | null; fecha_recibido: string | null; categoria_macro: string | null; categoria_nombre: string | null; estado_categoria: CorreoResumen['estado_categoria']; estado_clasificacion: EstadoClasificacion; }
export interface ErrorImportacionCorreo { fila: number | null; message_id: string | null; codigo: string; detalle: string; }
export interface AnalisisCorreos { lote: LoteCorreo; ultimos_100: CorreoPrevisualizacion[]; }

export const obtenerResumenCorreos = () => get<ResumenCorreos>('/correos/resumen');
export const listarCorreos = (params: URLSearchParams) => get<PaginaCorreos>(`/correos?${params}`);
export const obtenerCorreo = (id: string) => get<DetalleCorreoRespuesta>(`/correos/${id}`);
export const obtenerHistorialImportacionesCorreos = () => get<{ items: LoteCorreo[] }>('/correos/importar/lotes');
export const obtenerErroresImportacionCorreos = (id: string) => get<{ items: ErrorImportacionCorreo[] }>(`/correos/importar/${id}/errores`);
export function analizarCorreos(archivo: File): Promise<AnalisisCorreos> { const body = new FormData(); body.append('archivo', archivo); return postForm('/correos/importar/analizar', body); }
export const confirmarImportacionCorreos = (id: string, incluirSinClasificar: boolean) => post<{ lote: LoteCorreo; filas_seleccionadas: number; filas_importadas: number; filas_duplicadas: number }>(`/correos/importar/${id}/confirmar`, { incluir_sin_clasificar: incluirSinClasificar });
export const crearSeguimientoCorreo = (id: string, payload: { expected_version: number; detalle_seguimiento: string; seguimiento_por?: string; estado_requerimiento: EstadoRequerimiento }) => post<{ correo: CorreoResumen; seguimiento: SeguimientoCorreo }>(`/correos/${id}/seguimientos`, payload);
export interface ExportCorreosPayload { alcance: 'filtered' | 'all'; filtros: Record<string, string | boolean>; incluir_cuerpo: boolean; incluir_seguimientos: boolean; }
export const exportarCorreos = (payload: ExportCorreosPayload): Promise<BlobResponse> => postForBlobResponse('/correos/exportar', payload);
