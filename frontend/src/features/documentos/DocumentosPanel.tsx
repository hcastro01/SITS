import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { HttpError } from '../../api/client';
import {
  eliminarDocumento, listarDocumentos, subirDocumento, urlDescargaDocumento, type Documento,
} from '../../api/documentos';
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

function formatoTamano(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function DocumentosPanel({ tipoRegistro, idRegistro }: { tipoRegistro: string; idRegistro: string }) {
  const { notify, confirm } = useFeedback();
  const { usuario } = useAuth();
  const parentModule = tipoRegistro === 'RESPUESTAS_FORMULARIO' ? 'RESPUESTAS'
    : tipoRegistro === 'HALLAZGOS_RECORRIDO' ? 'RECORRIDOS' : tipoRegistro;
  const canUpload = canAccess(usuario, parentModule, 'edit') && canAccess(usuario, 'DOCUMENTOS', 'create');
  const canDelete = canAccess(usuario, parentModule, 'edit') && canAccess(usuario, 'DOCUMENTOS', 'delete');
  const [documentos, setDocumentos] = useState<Documento[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [subiendo, setSubiendo] = useState(false);
  const [categoria, setCategoria] = useState('');
  const [documentoEliminar, setDocumentoEliminar] = useState<Documento | null>(null);
  const [motivoEliminacion, setMotivoEliminacion] = useState('');
  const [eliminando, setEliminando] = useState(false);
  const inputArchivoRef = useRef<HTMLInputElement>(null);

  const cargar = useCallback(async () => {
    setError(null);
    try {
      setDocumentos(await listarDocumentos(tipoRegistro, idRegistro));
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible cargar los documentos.');
    } finally {
      setCargando(false);
    }
  }, [tipoRegistro, idRegistro]);

  useEffect(() => { cargar(); }, [cargar]);

  async function handleSubir(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const archivo = inputArchivoRef.current?.files?.[0];
    if (!archivo) return;
    setSubiendo(true);
    setError(null);
    try {
      await subirDocumento(tipoRegistro, idRegistro, archivo, categoria || undefined);
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

  async function handleEliminar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!documentoEliminar) return;
    setEliminando(true);
    setError(null);
    try {
      await eliminarDocumento(documentoEliminar.id_archivo, { expected_version: documentoEliminar.version, motivo: motivoEliminacion });
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
        <label htmlFor="documento-archivo">Archivo (JPG, PNG, PDF, DOC, DOCX, XLS, XLSX — máx. 10&nbsp;MB)</label>
        <input id="documento-archivo" ref={inputArchivoRef} type="file" required
               accept=".jpg,.jpeg,.png,.pdf,.doc,.docx,.xls,.xlsx" />
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
            <tr><th>Nombre</th><th>Categoría</th><th>Tamaño</th><th>Cargado</th><th></th></tr>
          </thead>
          <tbody>
            {documentos.map((documento) => (
              <tr key={documento.id_archivo}>
                <td>{documento.nombre_archivo}</td>
                <td>{documento.categoria_documento ?? '—'}</td>
                <td>{formatoTamano(documento.tamano_bytes)}</td>
                <td>{formatDateTime(documento.fecha_creacion)}<br /><small>{documento.creado_por ?? '—'}</small></td>
                <td className="doc-actions">
                  <a className="button-link" href={urlDescargaDocumento(documento.id_archivo)} download={documento.nombre_archivo}>
                    Descargar
                  </a>
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
    </section>
  );
}
