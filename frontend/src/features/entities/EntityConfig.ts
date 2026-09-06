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
}

export const atencionesConfig: EntityPageConfig = {
  titulo: 'Atenciones',
  tituloSingular: 'atención',
  rutaBase: '/atenciones',
  api: atencionesApi,
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
