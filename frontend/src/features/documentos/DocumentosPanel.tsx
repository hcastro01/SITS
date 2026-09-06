import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { HttpError } from '../../api/client';
import {
  eliminarDocumento, listarDocumentos, subirDocumento, urlDescargaDocumento, type Documento,
} from '../../api/documentos';

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
  const [documentos, setDocumentos] = useState<Documento[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [subiendo, setSubiendo] = useState(false);
  const [categoria, setCategoria] = useState('');
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
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible subir el archivo.');
    } finally {
      setSubiendo(false);
    }
  }

  async function handleEliminar(documento: Documento) {
    const motivo = window.prompt(`Motivo de eliminación de "${documento.nombre_archivo}":`);
    if (!motivo) return;
    setError(null);
    try {
      await eliminarDocumento(documento.id_archivo, { expected_version: documento.version, motivo });
      await cargar();
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible eliminar el documento.');
    }
  }

  return (
    <section className="panel">
      <h2>Documentos</h2>
      {error && <p className="form-error" role="alert">{error}</p>}

      <form onSubmit={handleSubir} className="upload-form">
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
      </form>

      {cargando ? (
        <p className="footnote">Cargando documentos…</p>
      ) : documentos.length === 0 ? (
        <p className="footnote">Sin documentos adjuntos.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr><th>Nombre</th><th>Categoría</th><th>Tamaño</th><th>Cargado</th><th></th></tr>
          </thead>
          <tbody>
            {documentos.map((documento) => (
              <tr key={documento.id_archivo}>
                <td>{documento.nombre_archivo}</td>
                <td>{documento.categoria_documento ?? '—'}</td>
                <td>{formatoTamano(documento.tamano_bytes)}</td>
                <td>{documento.creado_por ?? '—'}</td>
                <td className="doc-actions">
                  <a className="button-link" href={urlDescargaDocumento(documento.id_archivo)} download={documento.nombre_archivo}>
                    Descargar
                  </a>
                  <button type="button" onClick={() => handleEliminar(documento)}>Eliminar</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
