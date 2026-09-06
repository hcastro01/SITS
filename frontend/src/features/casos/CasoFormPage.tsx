import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { crearCaso } from '../../api/casos';
import { HttpError } from '../../api/client';

export function CasoFormPage() {
  const navigate = useNavigate();
  const [responsable, setResponsable] = useState('');
  const [estadoCaso, setEstadoCaso] = useState('ABIERTO');
  const [tipoCaso, setTipoCaso] = useState('');
  const [prioridad, setPrioridad] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      const caso = await crearCaso({
        responsable: responsable || undefined,
        estado_caso: estadoCaso || undefined,
        tipo_caso: tipoCaso || undefined,
        prioridad: prioridad || undefined,
        motivo: 'Apertura desde el frontend',
      });
      navigate(`/casos/${caso.id_caso}`);
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible crear el caso.');
    } finally {
      setEnviando(false);
    }
  }

  return (
    <section className="panel">
      <h2>Nuevo caso</h2>
      <form onSubmit={handleSubmit}>
        <label htmlFor="responsable">Responsable</label>
        <input id="responsable" value={responsable} onChange={(e) => setResponsable(e.target.value)} />

        <label htmlFor="estado_caso">Estado</label>
        <input id="estado_caso" value={estadoCaso} onChange={(e) => setEstadoCaso(e.target.value)} />

        <label htmlFor="tipo_caso">Tipo de caso</label>
        <input id="tipo_caso" value={tipoCaso} onChange={(e) => setTipoCaso(e.target.value)} />

        <label htmlFor="prioridad">Prioridad</label>
        <input id="prioridad" value={prioridad} onChange={(e) => setPrioridad(e.target.value)} />

        {error && <p className="form-error" role="alert">{error}</p>}
        <button type="submit" disabled={enviando}>{enviando ? 'Guardando…' : 'Crear caso'}</button>
      </form>
    </section>
  );
}
