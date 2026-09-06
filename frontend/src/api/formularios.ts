import { get, patch, post } from './client';

export interface Formulario {
  id_formulario: string;
  nombre: string;
  descripcion: string | null;
  proceso: string | null;
  responsable: string | null;
  estado: string | null;
  fecha_publicacion: string | null;
  version: number;
  activo: boolean;
  eliminado: boolean;
}

export interface Pregunta {
  id_pregunta: string;
  id_formulario: string;
  etiqueta: string;
  tipo: string | null;
  obligatoria: boolean;
  orden: number;
  version: number;
}

export function crearFormulario(datos: Record<string, unknown>): Promise<Formulario> {
  return post<Formulario>('/formularios', datos);
}

export function actualizarFormulario(id: string, datos: Record<string, unknown>): Promise<Formulario> {
  return patch<Formulario>(`/formularios/${id}`, datos);
}

export function cambiarEstadoFormulario(id: string, estado: string, expectedVersion: number) {
  return patch<Formulario>(`/formularios/${id}/estado`, { estado, expected_version: expectedVersion });
}

export function crearPregunta(idFormulario: string, datos: Record<string, unknown>): Promise<Pregunta> {
  return post<Pregunta>(`/formularios/${idFormulario}/preguntas`, datos);
}

export function listarFormularios(): Promise<Formulario[]> {
  return get<Formulario[]>('/formularios');
}

export function obtenerFormulario(id: string): Promise<Formulario & { preguntas: Pregunta[] }> {
  return get<Formulario & { preguntas: Pregunta[] }>(`/formularios/${id}`);
}

export interface RespuestaEnviada {
  id_respuesta: string;
  estado: string;
  fecha_respuesta: string | null;
}

/**
 * Cada respuesta se envía como texto libre (valor_texto): el backend todavía no aplica
 * el motor de reglas de visibilidad/validación por tipo (documentado como fuera de
 * alcance en app/services/respuestas_formulario.py), así que la captura no distingue
 * tipos de pregunta todavía.
 */
export function responderFormulario(
  idFormulario: string, respuestas: Array<{ id_pregunta: string; valor_texto: string }>, borrador: boolean,
): Promise<RespuestaEnviada> {
  return post<RespuestaEnviada>(`/formularios/${idFormulario}/respuestas`, { respuestas, borrador });
}
