import { useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { crearFormulario, listarFormularios, type Formulario } from '../../api/formularios';
import { HttpError } from '../../api/client';

export function FormulariosListPage() {
  const [formularios, setFormularios] = useState<Formulario[]>([]);
  const [nombre, setNombre] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [creando, setCreando] = useState(false);

  async function cargar() {
    try {
      setFormularios(await listarFormularios());
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible cargar los formularios.');
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => { cargar(); }, []);

  async function handleCrear(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreando(true);
    setError(null);
    try {
      await crearFormulario({ nombre });
      setNombre('');
      await cargar();
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible crear el formulario.');
    } finally {
      setCreando(false);
    }
  }

  return (
    <section className="panel wide-panel">
      <h2>Formularios</h2>
      <form onSubmit={handleCrear} className="search-form">
        <label htmlFor="nombre-formulario" className="visually-hidden">Nombre</label>
        <input id="nombre-formulario" placeholder="Nombre del formulario" required value={nombre}
               onChange={(e) => setNombre(e.target.value)} />
        <button type="submit" disabled={creando}>{creando ? 'Creando…' : 'Crear formulario'}</button>
      </form>
      {error && <p className="form-error" role="alert">{error}</p>}
      {cargando ? (
        <p>Cargando…</p>
      ) : formularios.length === 0 ? (
        <p className="footnote">No hay formularios creados todavía.</p>
      ) : (
        <table className="data-table">
          <thead><tr><th>Nombre</th><th>Estado</th><th></th></tr></thead>
          <tbody>
            {formularios.map((formulario) => (
              <tr key={formulario.id_formulario}>
                <td>{formulario.nombre}</td>
                <td>{formulario.estado}</td>
                <td><Link to={`/formularios/${formulario.id_formulario}`}>Ver</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
