import { get } from './client';
import type { Pagina } from './importacionesAusentismos';

export interface AusentismoOperativo {
  id_ausentismo: string;
  persona_id: string;
  persona: string;
  cedula: string | null;
  area: string | null;
  fecha_inicio: string;
  fecha_fin: string;
  tipo_ausentismo: string;
  motivo: string;
  observacion: string | null;
  fecha_registro: string | null;
  registrado_por_id: string | null;
  registrado_por: string | null;
  origen: string | null;
  lote_id: string | null;
  lote_nombre_archivo: string | null;
}

export interface FiltrosAusentismos {
  nombre: string;
  cedula: string;
  area: string;
  tipo_ausentismo: string;
  desde: string;
  hasta: string;
  origen: string;
  lote_id: string;
}

const root = '/ausentismos';
export const listarAusentismos = (params: URLSearchParams): Promise<Pagina<AusentismoOperativo>> => get(`${root}?${params}`);
export const obtenerAusentismo = (id: string): Promise<AusentismoOperativo> => get(`${root}/${id}`);
