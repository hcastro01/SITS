import { get, postForBlob } from './client';

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
