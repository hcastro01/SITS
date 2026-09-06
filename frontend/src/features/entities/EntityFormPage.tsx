import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { HttpError } from '../../api/client';
import type { EntityPageConfig } from './EntityConfig';

export function EntityFormPage({ config }: { config: EntityPageConfig }) {
  const navigate = useNavigate();
  const camposFormulario = config.campos.filter((campo) => campo.enFormulario !== false);
  const [valores, setValores] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      const datos: Record<string, unknown> = { motivo_auditoria: `Alta de ${config.tituloSingular} desde el frontend` };
      for (const campo of camposFormulario) {
        if (valores[campo.nombre]) datos[campo.nombre] = valores[campo.nombre];
      }
      const registro = await config.api.create(datos);
      navigate(`${config.rutaBase}/${registro[config.api.idField]}`);
    } catch (err) {
      setError(err instanceof HttpError ? err.message : `No fue posible crear ${config.tituloSingular}.`);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <section className="panel">
      <h2>Nueva {config.tituloSingular}</h2>
      <form onSubmit={handleSubmit}>
        {camposFormulario.map((campo) => (
          <div key={campo.nombre}>
            <label htmlFor={campo.nombre}>{campo.etiqueta}</label>
            <input
              id={campo.nombre}
              required={campo.requerido}
              value={valores[campo.nombre] ?? ''}
              onChange={(event) => setValores((previo) => ({ ...previo, [campo.nombre]: event.target.value }))}
            />
          </div>
        ))}
        {error && <p className="form-error" role="alert">{error}</p>}
        <button type="submit" disabled={enviando}>{enviando ? 'Guardando…' : `Crear ${config.tituloSingular}`}</button>
      </form>
    </section>
  );
}
