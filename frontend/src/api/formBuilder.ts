import { get, patch, post, put } from './client';

export const FORM_DESTINATIONS = ['GENERAL', 'CASOS', 'ATENCIONES', 'NOVEDADES', 'RECORRIDOS', 'PERSONAS'] as const;
export type FormDestination = typeof FORM_DESTINATIONS[number];

export interface FormOption {
  id_opcion: string;
  id_pregunta?: string;
  valor: string;
  etiqueta: string;
  orden: number;
  id_catalogo?: string | null;
  id_opcion_padre?: string | null;
}

export interface FormQuestion {
  id_pregunta: string;
  id_formulario?: string;
  id_seccion: string | null;
  etiqueta: string;
  descripcion: string | null;
  tipo: string;
  obligatoria: boolean;
  orden: number;
  texto_ayuda: string | null;
  valor_predeterminado: string | null;
  visible: boolean;
  solo_lectura: boolean;
  longitud_maxima: number | null;
  validacion: Record<string, unknown>;
  configuracion: Record<string, unknown>;
  fuente_datos: string | null;
  mapping: Record<string, string>;
  opciones: FormOption[];
  version?: number;
}

export interface FormSection {
  id_seccion: string;
  titulo: string;
  descripcion: string | null;
  orden: number;
}

export interface FormRule {
  id_regla: string;
  id_pregunta_origen: string;
  operador: string;
  valor_comparacion: string | null;
  id_pregunta_destino: string | null;
  id_seccion_destino: string | null;
  accion: string;
  grupo: 'TODAS' | 'CUALQUIERA';
  mensaje?: string | null;
  orden: number;
}

export interface FormDefinition {
  id_formulario: string;
  nombre: string;
  descripcion: string | null;
  responsable: string | null;
  estado: 'BORRADOR' | 'PUBLICADO' | 'INACTIVO' | 'ARCHIVADO';
  fecha_publicacion: string | null;
  fecha_actualizacion: string | null;
  actualizado_por: string | null;
  permite_multiples_respuestas: boolean;
  version_publicada: number;
  version: number;
  activo: boolean;
  eliminado: boolean;
  destinos: FormDestination[];
  total_preguntas: number;
  total_respuestas: number;
  secciones: FormSection[];
  preguntas: FormQuestion[];
  reglas: FormRule[];
}

export interface FormAnswer {
  id_pregunta: string;
  valor_texto?: string;
  valor_numero?: number;
  valor_fecha?: string;
  valor_booleano?: boolean;
  valor_opcion?: string;
}

export interface FormResponse {
  id_respuesta: string;
  id_formulario: string;
  numero_secuencial: number | null;
  codigo_respuesta: string | null;
  estado: 'BORRADOR' | 'REGISTRADO';
  fecha_respuesta: string | null;
  usuario_respuesta: string;
  contexto_tipo: string | null;
  contexto_id: string | null;
  version: number;
  id_version_formulario?: string | null;
  contexto_creado_dinamicamente?: boolean;
  id_persona?: string | null;
  persona?: string | null;
  acciones?: ResponseActions;
  definicion?: FormDefinition;
  respuestas?: FormAnswer[];
}

export interface ResponseActions {
  ver: boolean;
  continuar: boolean;
  editar: boolean;
  eliminar: boolean;
}

export interface ContextForm {
  id_formulario: string;
  nombre: string;
  descripcion: string | null;
  estado_respuesta: 'PENDIENTE' | 'BORRADOR' | 'REGISTRADO';
  total_preguntas: number;
  id_respuesta?: string;
  codigo_respuesta?: string | null;
  fecha_respuesta?: string | null;
  usuario_respuesta?: string;
  version?: number;
  permite_multiples_respuestas?: boolean;
  puede_crear?: boolean;
  acciones?: ResponseActions;
}

export interface AvailableForm {
  id_formulario: string;
  nombre: string;
  descripcion: string | null;
  total_preguntas: number;
  permite_multiples_respuestas: boolean;
}

export interface ModuleFormRecord extends FormResponse {
  tipo_registro: 'FORMULARIO';
  formulario: string;
  id_persona: string | null;
  persona: string | null;
  responsable: string | null;
}

export interface PaginatedModuleResponses {
  items: ModuleFormRecord[];
  pagina: number;
  tamano_pagina: number;
  total: number;
  total_paginas: number;
}

export interface SearchSource {
  codigo: string;
  label: string;
  search_fields: string[];
  mapping_fields: string[];
}

export interface SearchResult {
  id: string;
  label: string;
  data: Record<string, string | null>;
}

export const listFormDefinitions = () => get<FormDefinition[]>('/formularios');
export const getFormDefinition = (id: string) => get<FormDefinition>(`/formularios/${id}`);
export const createFormDefinition = (data: Record<string, unknown>) => post<FormDefinition>('/formularios', data);
export const saveFormDefinition = (id: string, data: Record<string, unknown>) =>
  put<FormDefinition>(`/formularios/${id}/definicion`, data);
export const duplicateFormDefinition = (id: string) => post<FormDefinition>(`/formularios/${id}/duplicar`, {});
export const setFormStatus = (id: string, estado: string, expectedVersion: number) =>
  patch<FormDefinition>(`/formularios/${id}/estado`, { estado, expected_version: expectedVersion });
export const listSearchSources = () => get<SearchSource[]>('/formularios/fuentes-busqueda');
export const searchFormOptions = (source: string, query: string, catalogType?: string) =>
  get<SearchResult[]>(`/formularios/search-options?source=${encodeURIComponent(source)}&q=${encodeURIComponent(query)}&limit=15${catalogType ? `&tipo_catalogo=${encodeURIComponent(catalogType)}` : ''}`);
export const listContextForms = (type: string, id: string) =>
  get<ContextForm[]>(`/formularios/contexto/${encodeURIComponent(type)}/${encodeURIComponent(id)}`);
export const listFormResponses = (id: string, query = '') => get<FormResponse[]>(`/formularios/${id}/respuestas${query ? `?q=${encodeURIComponent(query)}` : ''}`);
export const getFormResponse = (id: string) => get<FormResponse>(`/formularios/respuestas/${id}`);
export const saveFormResponse = (id: string, data: Record<string, unknown>) =>
  post<FormResponse>(`/formularios/${id}/respuestas`, data);
export const deleteFormResponse = (id: string, expectedVersion: number, motivo: string) =>
  post<FormResponse>(`/formularios/respuestas/${id}/eliminacion`, { expected_version: expectedVersion, motivo });
export const listAvailableForms = (module: string) =>
  get<AvailableForm[]>(`/formularios/disponibles/${encodeURIComponent(module)}`);
export const listModuleFormResponses = (module: string, page = 1, state = '') => {
  const params = new URLSearchParams({ pagina: String(page), tamano_pagina: '20' });
  if (state) params.set('estado', state);
  return get<PaginatedModuleResponses>(`/formularios/modulo/${encodeURIComponent(module)}/respuestas?${params}`);
};
