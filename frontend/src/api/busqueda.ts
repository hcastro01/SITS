import { get, postForBlob } from './client';
import type { ResponseActions } from './formBuilder';

export interface ResultadoBusqueda {
  tabla: string;
  id: string;
  fecha: string | null;
  sensible: boolean;
  restringido: boolean;
  registro: Record<string, unknown>;
  acciones: { ver: boolean; editar: boolean; eliminar: boolean; historial: boolean };
}

export interface RespuestaBusqueda {
  items: ResultadoBusqueda[];
  total: number;
  pagina: number;
  tamano_pagina: number;
  total_paginas: number;
}

export interface ConsolidatedRecord {
  tipo_registro: 'FORMULARIO' | 'REGISTRO_BASE';
  contexto_tipo: string;
  contexto_id: string;
  codigo_respuesta: string | null;
  formulario: string | null;
  estado: string | null;
  fecha_respuesta: string | null;
  responsable: string | null;
  id_persona: string | null;
  persona: string | null;
  version: number;
  acciones: ResponseActions;
  id_respuesta?: string;
  id_formulario?: string;
}

export interface PersonRecordsResponse {
  persona: { id_persona: string; nombre: string; codigo_empleado: string | null; cedula: string | null };
  items: ConsolidatedRecord[];
  total: number;
  pagina: number;
  tamano_pagina: number;
  total_paginas: number;
}

export function buscar(q: string, tablas?: string[]): Promise<RespuestaBusqueda> {
  const params = new URLSearchParams();
  if (q) params.set('q', q);
  if (tablas?.length) params.set('tablas', tablas.join(','));
  const query = params.toString();
  return get<RespuestaBusqueda>(`/busqueda${query ? `?${query}` : ''}`);
}

export function exportar(q: string, tablas?: string[]): Promise<Blob> {
  return postForBlob('/exportaciones', { q, tablas });
}

export function buscarRegistrosPersona(idPersona: string, page = 1, module = '', state = '') {
  const params = new URLSearchParams({ pagina: String(page), tamano_pagina: '20' });
  if (module) params.set('modulo', module);
  if (state) params.set('estado', state);
  return get<PersonRecordsResponse>(`/busqueda/personas/${encodeURIComponent(idPersona)}/registros?${params}`);
}

export function buscarPorCodigo(code: string) {
  return get<ConsolidatedRecord>(`/busqueda/codigo/${encodeURIComponent(code.trim().toUpperCase())}`);
}
