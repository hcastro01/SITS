import { get, getForBlob, post, postForm, type BlobResponse } from './client';

export interface Documento {
  id_archivo: string;
  tipo_registro: string;
  id_registro: string;
  nombre_archivo: string;
  mime_type: string;
  extension: string;
  tamano_bytes: number;
  tamano_comprimido_bytes: number;
  sha256: string;
  categoria_documento: string | null;
  version: number;
  activo: boolean;
  eliminado: boolean;
  fecha_creacion: string | null;
  creado_por: string | null;
}

export function listarDocumentos(tipoRegistro: string, idRegistro: string): Promise<Documento[]> {
  return get<Documento[]>(`/documentos?tipo_registro=${tipoRegistro}&id_registro=${idRegistro}`);
}

export function subirDocumento(
  tipoRegistro: string, idRegistro: string, archivo: File, categoriaDocumento?: string,
): Promise<Documento> {
  const formData = new FormData();
  formData.append('tipo_registro', tipoRegistro);
  formData.append('id_registro', idRegistro);
  if (categoriaDocumento) formData.append('categoria_documento', categoriaDocumento);
  formData.append('archivo', archivo);
  return postForm<Documento>('/documentos', formData);
}

export function eliminarDocumento(idArchivo: string, datos: { expected_version: number; motivo: string }): Promise<Documento> {
  return post<Documento>(`/documentos/${idArchivo}/eliminacion`, datos);
}

export const descargarDocumento = (idArchivo: string): Promise<BlobResponse> =>
  getForBlob(`/documentos/${encodeURIComponent(idArchivo)}/contenido`);

type ProduccionKind = 'atenciones' | 'recorridos' | 'novedades';
const productionDocumentsPath = (kind: ProduccionKind, recordId: string) => `/produccion/${kind}/${encodeURIComponent(recordId)}/documentos`;
export const listarDocumentosProduccion = (kind: ProduccionKind, recordId: string) => get<Documento[]>(productionDocumentsPath(kind, recordId));
export function subirDocumentoProduccion(kind: ProduccionKind, recordId: string, archivo: File, categoriaDocumento?: string): Promise<Documento> {
  const formData = new FormData();
  if (categoriaDocumento) formData.append('categoria_documento', categoriaDocumento);
  formData.append('archivo', archivo);
  return postForm<Documento>(productionDocumentsPath(kind, recordId), formData);
}
export const eliminarDocumentoProduccion = (kind: ProduccionKind, recordId: string, idArchivo: string, datos: { expected_version: number; motivo: string }) =>
  post<Documento>(`${productionDocumentsPath(kind, recordId)}/${encodeURIComponent(idArchivo)}/eliminacion`, datos);
export const descargarDocumentoProduccion = (kind: ProduccionKind, recordId: string, idArchivo: string): Promise<BlobResponse> =>
  getForBlob(`${productionDocumentsPath(kind, recordId)}/${encodeURIComponent(idArchivo)}/contenido`);

type OfficeKind = 'atenciones' | 'beneficios' | 'prestamos' | 'seguro';
const officeDocumentsPath = (kind: OfficeKind, recordId: string) => `/oficina/${kind}/${encodeURIComponent(recordId)}/documentos`;
export const listarDocumentosOficina = (kind: OfficeKind, recordId: string) => get<Documento[]>(officeDocumentsPath(kind, recordId));
export function subirDocumentoOficina(kind: OfficeKind, recordId: string, archivo: File, categoriaDocumento?: string): Promise<Documento> {
  const formData = new FormData();
  if (categoriaDocumento) formData.append('categoria_documento', categoriaDocumento);
  formData.append('archivo', archivo);
  return postForm<Documento>(officeDocumentsPath(kind, recordId), formData);
}
export const eliminarDocumentoOficina = (kind: OfficeKind, recordId: string, idArchivo: string, datos: { expected_version: number; motivo: string }) =>
  post<Documento>(`${officeDocumentsPath(kind, recordId)}/${encodeURIComponent(idArchivo)}/eliminacion`, datos);
export const descargarDocumentoOficina = (kind: OfficeKind, recordId: string, idArchivo: string): Promise<BlobResponse> =>
  getForBlob(`${officeDocumentsPath(kind, recordId)}/${encodeURIComponent(idArchivo)}/contenido`);
