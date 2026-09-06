import type { EntityClient } from '../../api/entities';
import { atencionesApi, novedadesApi, personasApi, recorridosApi } from '../../api/entities';

export interface CampoConfig {
  nombre: string;
  etiqueta: string;
  tipo?: 'texto' | 'booleano';
  enLista?: boolean;
  enFormulario?: boolean;
  requerido?: boolean;
}

export interface EntityPageConfig {
  titulo: string;
  tituloSingular: string;
  rutaBase: string;
  api: EntityClient;
  campos: CampoConfig[];
  /** Valor de tipo_registro en app/services/documentos.py::TIPO_REGISTRO_MODELOS. */
  tipoRegistro: string;
}

export const atencionesConfig: EntityPageConfig = {
  titulo: 'Atenciones',
  tituloSingular: 'atención',
  rutaBase: '/atenciones',
  api: atencionesApi,
  tipoRegistro: 'ATENCIONES',
  campos: [
    { nombre: 'fecha', etiqueta: 'Fecha' },
    { nombre: 'responsable', etiqueta: 'Responsable' },
    { nombre: 'tipo_atencion', etiqueta: 'Tipo' },
    { nombre: 'motivo', etiqueta: 'Motivo' },
    { nombre: 'canal', etiqueta: 'Canal', enLista: false },
    { nombre: 'gestion', etiqueta: 'Gestión', enLista: false },
    { nombre: 'resultado', etiqueta: 'Resultado', enLista: false },
    { nombre: 'observaciones', etiqueta: 'Observaciones', enLista: false },
    { nombre: 'estado', etiqueta: 'Estado' },
  ],
};

export const novedadesConfig: EntityPageConfig = {
  titulo: 'Novedades',
  tituloSingular: 'novedad',
  rutaBase: '/novedades',
  api: novedadesApi,
  tipoRegistro: 'NOVEDADES',
  campos: [
    { nombre: 'fecha', etiqueta: 'Fecha' },
    { nombre: 'responsable', etiqueta: 'Responsable' },
    { nombre: 'tipo', etiqueta: 'Tipo' },
    { nombre: 'descripcion', etiqueta: 'Descripción', requerido: true },
    { nombre: 'area', etiqueta: 'Área', enLista: false },
    { nombre: 'impacto', etiqueta: 'Impacto', enLista: false },
    { nombre: 'prioridad', etiqueta: 'Prioridad', enLista: false },
    { nombre: 'estado', etiqueta: 'Estado' },
  ],
};

export const recorridosConfig: EntityPageConfig = {
  titulo: 'Recorridos',
  tituloSingular: 'recorrido',
  rutaBase: '/recorridos',
  api: recorridosApi,
  tipoRegistro: 'RECORRIDOS',
  campos: [
    { nombre: 'fecha', etiqueta: 'Fecha' },
    { nombre: 'responsable', etiqueta: 'Responsable' },
    { nombre: 'planta', etiqueta: 'Planta' },
    { nombre: 'area', etiqueta: 'Área' },
    { nombre: 'objetivo', etiqueta: 'Objetivo', enLista: false },
    { nombre: 'observaciones', etiqueta: 'Observaciones', enLista: false },
  ],
};

export const personasConfig: EntityPageConfig = {
  titulo: 'Personas',
  tituloSingular: 'persona',
  rutaBase: '/personas',
  api: personasApi,
  tipoRegistro: 'PERSONAS',
  campos: [
    { nombre: 'nombre', etiqueta: 'Nombre', requerido: true },
    { nombre: 'codigo_empleado', etiqueta: 'Código de empleado' },
    { nombre: 'cedula', etiqueta: 'Cédula' },
    { nombre: 'cargo', etiqueta: 'Cargo' },
    { nombre: 'area', etiqueta: 'Área', enLista: false },
    { nombre: 'departamento', etiqueta: 'Departamento', enLista: false },
    { nombre: 'estado_laboral', etiqueta: 'Estado laboral' },
  ],
};
