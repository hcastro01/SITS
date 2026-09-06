import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { obtenerFormulario, responderFormulario, type Formulario, type Pregunta } from '../../api/formularios';
import { HttpError } from '../../api/client';
import { useFeedback } from '../../components/FeedbackProvider';
import { useUnsavedChanges } from '../../components/useUnsavedChanges';

export function ResponderFormularioPage() {
  const { notify } = useFeedback();
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const [formulario, setFormulario] = useState<(Formulario & { preguntas: Pregunta[] }) | null>(null);
  const [valores, setValores] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [enviando, setEnviando] = useState(false);
  useUnsavedChanges(Object.values(valores).some(Boolean) && !enviando);

  useEffect(() => {
    let activo = true;
    obtenerFormulario(id)
      .then((datos) => { if (activo) setFormulario(datos); })
      .catch((err: unknown) => { if (activo) setError(err instanceof HttpError ? err.message : 'No fue posible cargar el formulario.'); })
      .finally(() => { if (activo) setCargando(false); });
    return () => { activo = false; };
  }, [id]);

  async function enviar(borrador: boolean) {
    if (!formulario) return;
    setEnviando(true);
    setError(null);
    try {
      const respuestas = formulario.preguntas
        .filter((pregunta) => valores[pregunta.id_pregunta])
        .map((pregunta) => ({ id_pregunta: pregunta.id_pregunta, valor_texto: valores[pregunta.id_pregunta] }));
      await responderFormulario(id, respuestas, borrador);
      setValores({});
      notify(borrador ? 'Borrador guardado correctamente.' : 'Respuesta enviada correctamente.');
      navigate(`/formularios/${id}`);
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible guardar la respuesta.');
    } finally {
      setEnviando(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void enviar(false);
  }

  if (cargando) return <p>Cargando…</p>;
  if (!formulario) return <p className="form-error">{error ?? 'Formulario no encontrado.'}</p>;
  if (formulario.estado !== 'PUBLICADO') {
    return <p className="footnote">Este formulario todavía no está publicado.</p>;
  }

  return (
    <section className="panel">
      <h2>{formulario.nombre}</h2>
      <p className="footnote">Complete los campos obligatorios antes de enviar. Puede guardar un borrador para continuar después.</p>
      <form onSubmit={handleSubmit}>
        {formulario.preguntas.map((pregunta) => (
          <div key={pregunta.id_pregunta}>
            <label htmlFor={pregunta.id_pregunta}>{pregunta.etiqueta}{pregunta.obligatoria ? ' *' : ''}</label>
            <input
              id={pregunta.id_pregunta}
              required={pregunta.obligatoria}
              value={valores[pregunta.id_pregunta] ?? ''}
              onChange={(event) => setValores((previo) => ({ ...previo, [pregunta.id_pregunta]: event.target.value }))}
            />
          </div>
        ))}
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="button-row">
          <button type="button" disabled={enviando} onClick={() => enviar(true)}>Guardar borrador</button>
          <button type="submit" disabled={enviando}>{enviando ? 'Enviando…' : 'Enviar respuesta'}</button>
        </div>
      </form>
    </section>
  );
}
