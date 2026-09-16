import type { ContextualEntityClient, EntityClient } from '../../api/entities';
import { atencionesApi, novedadesApi, personasApi, produccionAtencionesApi, produccionNovedadesApi, produccionRecorridosApi, recorridosApi } from '../../api/entities';

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
  api: EntityClient | ContextualEntityClient;
  campos: CampoConfig[];
  /** Valor de tipo_registro en app/services/documentos.py::TIPO_REGISTRO_MODELOS. */
  tipoRegistro: string;
  contextual?: boolean;
  permissionModule?: string;
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

export const produccionAtencionesConfig: EntityPageConfig = {
  ...atencionesConfig, titulo: 'Atenciones de Producción', tituloSingular: 'atención de Producción',
  rutaBase: '/trabajo-social/produccion/atenciones', api: produccionAtencionesApi, contextual: true, permissionModule: 'PRODUCCION',
  campos: [
    { nombre: 'id_atencion', etiqueta: 'ID', enFormulario: false }, { nombre: 'fecha', etiqueta: 'Fecha' },
    { nombre: 'persona', etiqueta: 'Persona', enFormulario: false }, { nombre: 'cedula', etiqueta: 'Cédula', enFormulario: false },
    { nombre: 'area_persona', etiqueta: 'Área actual', enFormulario: false }, { nombre: 'motivo', etiqueta: 'Motivo' },
    { nombre: 'responsable', etiqueta: 'Responsable' }, { nombre: 'registrado_por', etiqueta: 'Registrado por', enFormulario: false },
    { nombre: 'estado', etiqueta: 'Estado' }, { nombre: 'tipo_atencion', etiqueta: 'Tipo', enLista: false },
    { nombre: 'canal', etiqueta: 'Canal', enLista: false }, { nombre: 'gestion', etiqueta: 'Gestión', enLista: false },
    { nombre: 'resultado', etiqueta: 'Resultado', enLista: false }, { nombre: 'observaciones', etiqueta: 'Observaciones', enLista: false },
  ],
};

export const produccionRecorridosConfig: EntityPageConfig = {
  ...recorridosConfig, rutaBase: '/trabajo-social/produccion/recorridos', api: produccionRecorridosApi, contextual: true, permissionModule: 'PRODUCCION',
  campos: [
    { nombre: 'id_recorrido', etiqueta: 'ID', enFormulario: false }, { nombre: 'fecha', etiqueta: 'Fecha' },
    { nombre: 'persona', etiqueta: 'Persona', enFormulario: false }, { nombre: 'cedula', etiqueta: 'Cédula', enFormulario: false },
    { nombre: 'area_persona', etiqueta: 'Área actual', enFormulario: false }, { nombre: 'objetivo', etiqueta: 'Objetivo' },
    { nombre: 'responsable', etiqueta: 'Responsable' }, { nombre: 'registrado_por', etiqueta: 'Registrado por', enFormulario: false },
    { nombre: 'planta', etiqueta: 'Planta', enLista: false }, { nombre: 'area', etiqueta: 'Área', enLista: false }, { nombre: 'observaciones', etiqueta: 'Observaciones', enLista: false },
  ],
};

export const produccionNovedadesConfig: EntityPageConfig = {
  ...novedadesConfig, titulo: 'Novedades de planta', tituloSingular: 'novedad de planta',
  rutaBase: '/trabajo-social/produccion/novedades', api: produccionNovedadesApi, contextual: true, permissionModule: 'PRODUCCION',
  campos: [
    { nombre: 'id_novedad', etiqueta: 'ID', enFormulario: false }, { nombre: 'fecha', etiqueta: 'Fecha' },
    { nombre: 'persona', etiqueta: 'Persona', enFormulario: false }, { nombre: 'cedula', etiqueta: 'Cédula', enFormulario: false },
    { nombre: 'area_persona', etiqueta: 'Área actual', enFormulario: false }, { nombre: 'descripcion', etiqueta: 'Descripción', requerido: true },
    { nombre: 'responsable', etiqueta: 'Responsable' }, { nombre: 'registrado_por', etiqueta: 'Registrado por', enFormulario: false },
    { nombre: 'estado', etiqueta: 'Estado' }, { nombre: 'tipo', etiqueta: 'Tipo', enLista: false }, { nombre: 'area', etiqueta: 'Área', enLista: false },
    { nombre: 'impacto', etiqueta: 'Impacto', enLista: false }, { nombre: 'prioridad', etiqueta: 'Prioridad', enLista: false },
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
