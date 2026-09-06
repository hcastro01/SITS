import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  cambiarEstadoFormulario, crearPregunta, obtenerFormulario, type Formulario, type Pregunta,
} from '../../api/formularios';
import { HttpError } from '../../api/client';

type FormularioConPreguntas = Formulario & { preguntas: Pregunta[] };

export function FormularioDetailPage() {
  const { id = '' } = useParams();
  const [formulario, setFormulario] = useState<FormularioConPreguntas | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [etiquetaPregunta, setEtiquetaPregunta] = useState('');
  const [agregando, setAgregando] = useState(false);
  const [publicando, setPublicando] = useState(false);

  const cargar = useCallback(async () => {
    setError(null);
    try {
      setFormulario(await obtenerFormulario(id));
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible cargar el formulario.');
    } finally {
      setCargando(false);
    }
  }, [id]);

  useEffect(() => { cargar(); }, [cargar]);

  async function handleAgregarPregunta(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAgregando(true);
    setError(null);
    try {
      await crearPregunta(id, { etiqueta: etiquetaPregunta });
      setEtiquetaPregunta('');
      await cargar();
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible agregar la pregunta.');
    } finally {
      setAgregando(false);
    }
  }

  async function handlePublicar() {
    if (!formulario) return;
    setPublicando(true);
    setError(null);
    try {
      await cambiarEstadoFormulario(id, 'PUBLICADO', formulario.version);
      await cargar();
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible publicar el formulario.');
    } finally {
      setPublicando(false);
    }
  }

  if (cargando) return <p>Cargando…</p>;
  if (!formulario) return <p className="form-error">Formulario no encontrado.</p>;

  const publicado = formulario.estado === 'PUBLICADO';

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>{formulario.nombre}</h2>
        <span>Estado: {formulario.estado}</span>
      </div>
      {publicado && <Link className="button-link" to={`/formularios/${id}/responder`}>Responder</Link>}
      {error && <p className="form-error" role="alert">{error}</p>}

      <h3>Preguntas</h3>
      {formulario.preguntas.length === 0 ? (
        <p className="footnote">Sin preguntas todavía. Agregue al menos una para poder publicar.</p>
      ) : (
        <ol className="question-list">
          {formulario.preguntas.map((pregunta) => <li key={pregunta.id_pregunta}>{pregunta.etiqueta}</li>)}
        </ol>
      )}

      {!publicado && (
        <>
          <form onSubmit={handleAgregarPregunta}>
            <label htmlFor="etiqueta-pregunta">Nueva pregunta</label>
            <input id="etiqueta-pregunta" required value={etiquetaPregunta}
                   onChange={(e) => setEtiquetaPregunta(e.target.value)} />
            <button type="submit" disabled={agregando}>{agregando ? 'Agregando…' : 'Agregar pregunta'}</button>
          </form>

          <button onClick={handlePublicar} disabled={publicando || formulario.preguntas.length === 0}>
            {publicando ? 'Publicando…' : 'Publicar formulario'}
          </button>
        </>
      )}
    </section>
  );
}
