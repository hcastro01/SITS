import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { HttpError } from '../../api/client';
import {
  descargarDocumento, descargarDocumentoOficina, descargarDocumentoProduccion, eliminarDocumento, eliminarDocumentoOficina, eliminarDocumentoProduccion, listarDocumentos, listarDocumentosOficina, listarDocumentosProduccion, subirDocumento, subirDocumentoOficina, subirDocumentoProduccion, type Documento,
} from '../../api/documentos';
import { descargarDocumentoRiesgo, eliminarDocumentoRiesgo, listarDocumentosRiesgo, subirDocumentoRiesgo } from '../../api/riesgosTrabajo';
import { Modal } from '../../components/Modal';
import { useFeedback } from '../../components/FeedbackProvider';
import { formatDateTime } from '../../utils/dates';
import { useAuth } from '../../app/AuthContext';
import { canAccess } from '../../api/auth';

const CATEGORIAS = [
  { valor: '', etiqueta: 'Sin categoría' },
  { valor: 'CEDULA', etiqueta: 'Cédula' },
  { valor: 'CERTIFICADO_MEDICO', etiqueta: 'Certificado médico' },
  { valor: 'EVIDENCIA', etiqueta: 'Evidencia' },
  { valor: 'OTRO', etiqueta: 'Otro' },
];

export const MAX_DOCUMENT_BYTES = 10 * 1024 * 1024;
export const MAX_DOCUMENTS_PER_RECORD = 10;
const MIME_BY_EXTENSION: Record<string, string> = {
  jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png', webp: 'image/webp', pdf: 'application/pdf',
};
const FILE_ACCEPT = '.pdf,.jpg,.jpeg,.png,.webp';

export function fileValidationError(file: File, currentCount: number): string | null {
  const extension = file.name.split('.').pop()?.toLowerCase() ?? '';
  const expectedMime = MIME_BY_EXTENSION[extension];
  if (!expectedMime) return 'Solo se permiten archivos PDF, JPEG, PNG o WEBP.';
  if (file.type && file.type !== expectedMime) return 'El tipo informado por el navegador no coincide con la extensión del archivo.';
  if (file.size > MAX_DOCUMENT_BYTES) return 'El archivo supera el límite de 10 MB.';
  if (currentCount >= MAX_DOCUMENTS_PER_RECORD) return 'Este registro ya alcanzó el máximo de 10 documentos activos.';
  return null;
}

function previewable(documento: Documento): boolean {
  return Object.values(MIME_BY_EXTENSION).includes(documento.mime_type);
}

function formatoTamano(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function DocumentosPanel({ tipoRegistro, idRegistro, riesgoId, produccionKind, oficinaKind }: { tipoRegistro: string; idRegistro: string; riesgoId?: string; produccionKind?: 'atenciones' | 'recorridos' | 'novedades'; oficinaKind?: 'atenciones' | 'beneficios' | 'prestamos' | 'seguro' }) {
  const { notify, confirm } = useFeedback();
  const { usuario } = useAuth();
  const parentModule = tipoRegistro === 'RESPUESTAS_FORMULARIO' ? 'RESPUESTAS'
    : tipoRegistro === 'HALLAZGOS_RECORRIDO' ? 'RECORRIDOS' : tipoRegistro;
  const scopedModule = riesgoId ? 'RIESGOS_TRABAJO' : produccionKind ? 'PRODUCCION' : oficinaKind ? 'OFICINA' : parentModule;
  const canUpload = canAccess(usuario, scopedModule, 'edit') && canAccess(usuario, 'DOCUMENTOS', 'create');
  const canDelete = canAccess(usuario, scopedModule, 'edit') && canAccess(usuario, 'DOCUMENTOS', 'delete');
  const [documentos, setDocumentos] = useState<Documento[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [subiendo, setSubiendo] = useState(false);
  const [categoria, setCategoria] = useState('');
  const [documentoEliminar, setDocumentoEliminar] = useState<Documento | null>(null);
  const [motivoEliminacion, setMotivoEliminacion] = useState('');
  const [eliminando, setEliminando] = useState(false);
  const [accionDocumento, setAccionDocumento] = useState<string | null>(null);
  const [preview, setPreview] = useState<{ documento: Documento; url: string } | null>(null);
  const inputArchivoRef = useRef<HTMLInputElement>(null);
  const previewUrlRef = useRef<string | null>(null);

  const revokePreviewUrl = useCallback(() => {
    if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
    previewUrlRef.current = null;
  }, []);

  const cargar = useCallback(async () => {
    setError(null);
    try {
      setDocumentos(await (riesgoId ? listarDocumentosRiesgo(riesgoId) : produccionKind ? listarDocumentosProduccion(produccionKind, idRegistro) : oficinaKind ? listarDocumentosOficina(oficinaKind, idRegistro) : listarDocumentos(tipoRegistro, idRegistro)));
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible cargar los documentos.');
    } finally {
      setCargando(false);
    }
  }, [tipoRegistro, idRegistro, riesgoId, produccionKind, oficinaKind]);

  useEffect(() => { cargar(); }, [cargar]);
  useEffect(() => () => revokePreviewUrl(), [revokePreviewUrl]);

  async function handleSubir(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const archivo = inputArchivoRef.current?.files?.[0];
    if (!archivo) return;
    const validationError = fileValidationError(archivo, documentos.length);
    if (validationError) { setError(validationError); return; }
    setSubiendo(true);
    setError(null);
    try {
      await (riesgoId ? subirDocumentoRiesgo(riesgoId, archivo, categoria || undefined) : produccionKind ? subirDocumentoProduccion(produccionKind, idRegistro, archivo, categoria || undefined) : oficinaKind ? subirDocumentoOficina(oficinaKind, idRegistro, archivo, categoria || undefined) : subirDocumento(tipoRegistro, idRegistro, archivo, categoria || undefined));
      if (inputArchivoRef.current) inputArchivoRef.current.value = '';
      setCategoria('');
      await cargar();
      notify('Documento cargado correctamente.');
    } catch (err) {
      const message = err instanceof HttpError ? err.message : 'No fue posible subir el archivo.';
      setError(message); notify(message, 'error');
    } finally {
      setSubiendo(false);
    }
  }

  async function obtenerContenido(documento: Documento) {
    return riesgoId ? descargarDocumentoRiesgo(riesgoId, documento.id_archivo)
      : produccionKind ? descargarDocumentoProduccion(produccionKind, idRegistro, documento.id_archivo)
      : oficinaKind ? descargarDocumentoOficina(oficinaKind, idRegistro, documento.id_archivo)
      : descargarDocumento(documento.id_archivo);
  }

  async function handleDescargar(documento: Documento) {
    setAccionDocumento(documento.id_archivo); setError(null);
    try {
      const { blob, filename } = await obtenerContenido(documento);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url; anchor.download = filename || documento.nombre_archivo;
      document.body.appendChild(anchor); anchor.click(); anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 0);
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible descargar el documento.');
    } finally { setAccionDocumento(null); }
  }

  async function handlePreview(documento: Documento) {
    setAccionDocumento(documento.id_archivo); setError(null);
    try {
      const { blob } = await obtenerContenido(documento);
      revokePreviewUrl();
      const url = URL.createObjectURL(blob);
      previewUrlRef.current = url;
      setPreview({ documento, url });
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible abrir la vista previa.');
    } finally { setAccionDocumento(null); }
  }

  function closePreview() {
    revokePreviewUrl(); setPreview(null);
  }

  async function handleEliminar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!documentoEliminar) return;
    setEliminando(true);
    setError(null);
    try {
      await (riesgoId ? eliminarDocumentoRiesgo(riesgoId, documentoEliminar.id_archivo, { expected_version: documentoEliminar.version, motivo: motivoEliminacion }) : produccionKind ? eliminarDocumentoProduccion(produccionKind, idRegistro, documentoEliminar.id_archivo, { expected_version: documentoEliminar.version, motivo: motivoEliminacion }) : oficinaKind ? eliminarDocumentoOficina(oficinaKind, idRegistro, documentoEliminar.id_archivo, { expected_version: documentoEliminar.version, motivo: motivoEliminacion }) : eliminarDocumento(documentoEliminar.id_archivo, { expected_version: documentoEliminar.version, motivo: motivoEliminacion }));
      setDocumentoEliminar(null); setMotivoEliminacion('');
      await cargar();
      notify('Documento eliminado correctamente.');
    } catch (err) {
      const message = err instanceof HttpError ? err.message : 'No fue posible eliminar el documento.';
      setError(message); notify(message, 'error');
    } finally { setEliminando(false); }
  }

  async function closeDeleteDialog() {
    if (!motivoEliminacion || await confirm({
      title: 'Cambios sin guardar', message: 'El motivo escrito todavía no se guardó.',
      confirmLabel: 'Salir sin guardar', cancelLabel: 'Continuar editando', danger: true,
    })) {
      setDocumentoEliminar(null); setMotivoEliminacion('');
    }
  }

  return (
    <section className="panel">
      <h2>Documentos</h2>
      {error && <p className="form-error" role="alert">{error}</p>}

      {canUpload && <form onSubmit={handleSubir} className="upload-form">
        <label htmlFor="documento-archivo">Archivo (PDF, JPEG, PNG o WEBP — máx. 10&nbsp;MB)</label>
        <input id="documento-archivo" ref={inputArchivoRef} type="file" required
               accept={FILE_ACCEPT} />
        <label htmlFor="documento-categoria">Categoría</label>
        <select id="documento-categoria" value={categoria} onChange={(e) => setCategoria(e.target.value)}>
          {CATEGORIAS.map((opcion) => (
            <option key={opcion.valor} value={opcion.valor}>{opcion.etiqueta}</option>
          ))}
        </select>
        <button type="submit" disabled={subiendo}>{subiendo ? 'Subiendo…' : 'Subir documento'}</button>
      </form>}

      {cargando ? (
        <p className="footnote">Cargando documentos…</p>
      ) : documentos.length === 0 ? (
        <p className="footnote">Sin documentos adjuntos.</p>
      ) : (
        <div className="table-scroll"><table className="data-table">
          <thead>
            <tr><th>Nombre</th><th>Tipo</th><th>Categoría</th><th>Tamaño</th><th>Cargado</th><th></th></tr>
          </thead>
          <tbody>
            {documentos.map((documento) => (
              <tr key={documento.id_archivo}>
                <td>{documento.nombre_archivo}</td>
                <td>{documento.mime_type}</td>
                <td>{documento.categoria_documento ?? '—'}</td>
                <td>{formatoTamano(documento.tamano_bytes)}</td>
                <td>{formatDateTime(documento.fecha_creacion)}<br /><small>{documento.creado_por ?? '—'}</small></td>
                <td className="doc-actions">
                  <button type="button" className="secondary" disabled={accionDocumento === documento.id_archivo} onClick={() => void handleDescargar(documento)}>{accionDocumento === documento.id_archivo ? 'Procesando…' : 'Descargar'}</button>
                  {previewable(documento) && <button type="button" className="secondary" disabled={accionDocumento === documento.id_archivo} onClick={() => void handlePreview(documento)}>Vista previa</button>}
                  {canDelete && <button type="button" className="danger" onClick={() => setDocumentoEliminar(documento)}>Eliminar</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table></div>
      )}
      {documentoEliminar && (
        <Modal titulo="Eliminar documento" onClose={() => void closeDeleteDialog()} closeOnBackdrop={!eliminando} size="small">
          <p>Se eliminará <strong>{documentoEliminar.nombre_archivo}</strong>. El archivo dejará de estar disponible, pero el evento permanecerá auditado.</p>
          <form onSubmit={handleEliminar}>
            <label htmlFor={`motivo-eliminacion-${documentoEliminar.id_archivo}`}>Motivo de eliminación</label>
            <textarea id={`motivo-eliminacion-${documentoEliminar.id_archivo}`} required data-autofocus value={motivoEliminacion} onChange={(event) => setMotivoEliminacion(event.target.value)} />
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={() => void closeDeleteDialog()}>Cancelar</button>
              <button type="submit" className="danger" disabled={eliminando}>{eliminando ? 'Eliminando…' : 'Eliminar documento'}</button>
            </div>
          </form>
        </Modal>
      )}
      {preview && (
        <Modal titulo={`Vista previa: ${preview.documento.nombre_archivo}`} onClose={closePreview} size="large">
          {preview.documento.mime_type === 'application/pdf'
            ? <iframe className="document-preview document-preview--pdf" src={preview.url} title={`Vista previa de ${preview.documento.nombre_archivo}`} />
            : <img className="document-preview document-preview--image" src={preview.url} alt={`Vista previa de ${preview.documento.nombre_archivo}`} />}
          <div className="modal-actions"><button type="button" className="secondary" onClick={closePreview}>Cerrar vista previa</button></div>
        </Modal>
      )}
    </section>
  );
}
