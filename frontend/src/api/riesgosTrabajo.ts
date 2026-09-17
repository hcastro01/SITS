import { get, getForBlob, patch, post, postForm, type BlobResponse } from './client';
import type { ContextForm, FormResponse } from './formBuilder';
import type { Documento } from './documentos';

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
export interface RiesgoSeguimiento { id_seguimiento: string; fecha: string | null; responsable: string | null; descripcion: string | null; resultado: string | null; proxima_accion: string | null; fecha_proxima_accion: string | null; estado: string | null; creado_por: string | null; }
export interface RiesgoCompromiso { id_compromiso: string; responsable: string | null; descripcion: string | null; fecha_limite: string | null; estado: string | null; observacion: string | null; creado_por: string | null; }
export interface RiesgoHistorial { campo: string; accion: string; valor_anterior: string | null; valor_nuevo: string | null; usuario: string; fecha_hora: string; motivo: string | null; }

export function listarRiesgos(params: URLSearchParams) {
  return get<{ items: RiesgoTrabajo[]; total: number; limite: number; offset: number }>(`/riesgos-trabajo?${params}`);
}

export const obtenerRiesgo = (id: string) => get<RiesgoTrabajo>(`/riesgos-trabajo/${id}`);
export const crearRiesgo = (payload: RiesgoCreate) => post<RiesgoTrabajo>('/riesgos-trabajo', payload);
export const actualizarRiesgo = (id: string, payload: RiesgoUpdate) => patch<RiesgoTrabajo>(`/riesgos-trabajo/${id}`, payload);
export const cerrarRiesgo = (id: string, payload: { expected_version: number; fecha_cierre_caso?: string; responsable?: string; motivo_cierre: string; resultado_final?: string }) =>
  post(`/riesgos-trabajo/${id}/cierres`, payload);
export const listarSeguimientosRiesgo = (id: string) => get<RiesgoSeguimiento[]>(`/riesgos-trabajo/${id}/seguimientos`);
export const crearSeguimientoRiesgo = (id: string, payload: { fecha: string; descripcion: string; responsable?: string; resultado?: string; proxima_accion?: string; fecha_proxima_accion?: string; estado?: string }) => post<RiesgoSeguimiento>(`/riesgos-trabajo/${id}/seguimientos`, payload);
export const listarCompromisosRiesgo = (id: string) => get<RiesgoCompromiso[]>(`/riesgos-trabajo/${id}/compromisos`);
export const crearCompromisoRiesgo = (id: string, payload: { responsable?: string; descripcion: string; fecha_limite?: string; estado?: string; observacion?: string }) => post<RiesgoCompromiso>(`/riesgos-trabajo/${id}/compromisos`, payload);
export const historialRiesgo = (id: string) => get<RiesgoHistorial[]>(`/riesgos-trabajo/${id}/historial`);
export const listarFormulariosRiesgo = (id: string) => get<ContextForm[]>(`/riesgos-trabajo/${id}/formularios`);
export const responderFormularioRiesgo = (riesgoId: string, formId: string, payload: Record<string, unknown>) =>
  post<FormResponse>(`/riesgos-trabajo/${riesgoId}/formularios/${formId}/respuestas`, payload);
export const listarDocumentosRiesgo = (id: string) => get<Documento[]>(`/riesgos-trabajo/${id}/documentos`);
export function subirDocumentoRiesgo(id: string, archivo: File, categoriaDocumento?: string): Promise<Documento> {
  const formData = new FormData(); if (categoriaDocumento) formData.append('categoria_documento', categoriaDocumento);
  formData.append('archivo', archivo); return postForm<Documento>(`/riesgos-trabajo/${id}/documentos`, formData);
}
export const eliminarDocumentoRiesgo = (riesgoId: string, idArchivo: string, datos: { expected_version: number; motivo: string }) =>
  post<Documento>(`/riesgos-trabajo/${riesgoId}/documentos/${idArchivo}/eliminacion`, datos);
export const descargarDocumentoRiesgo = (riesgoId: string, idArchivo: string): Promise<BlobResponse> =>
  getForBlob(`/riesgos-trabajo/${encodeURIComponent(riesgoId)}/documentos/${encodeURIComponent(idArchivo)}/contenido`);
