import { fileUrl, get, post, postForm } from './client';

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

export function urlDescargaDocumento(idArchivo: string): string {
  return fileUrl(`/documentos/${idArchivo}/contenido`);
}
