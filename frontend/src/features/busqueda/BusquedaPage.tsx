import { useState, type FormEvent } from 'react';
import { buscar, exportar, type ResultadoBusqueda } from '../../api/busqueda';
import { HttpError } from '../../api/client';

const TABLAS_DISPONIBLES = [
  'casos', 'atenciones', 'novedades', 'recorridos', 'seguimientos', 'derivaciones', 'compromisos',
];

export function BusquedaPage() {
  const [q, setQ] = useState('');
  const [resultados, setResultados] = useState<ResultadoBusqueda[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [buscando, setBuscando] = useState(false);
  const [exportando, setExportando] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBuscando(true);
    setError(null);
    try {
      const respuesta = await buscar(q);
      setResultados(respuesta.items);
      setTotal(respuesta.total);
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible completar la búsqueda.');
    } finally {
      setBuscando(false);
    }
  }

  async function handleExportar() {
    setExportando(true);
    setError(null);
    try {
      const blob = await exportar(q, TABLAS_DISPONIBLES);
      const url = URL.createObjectURL(blob);
      const enlace = document.createElement('a');
      enlace.href = url;
      enlace.download = 'exportacion.csv';
      enlace.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible exportar los resultados.');
    } finally {
      setExportando(false);
    }
  }

  return (
    <section className="panel wide-panel">
      <h2>Búsqueda</h2>
      <form onSubmit={handleSubmit} className="search-form">
        <label htmlFor="q" className="visually-hidden">Buscar</label>
        <input id="q" placeholder="Buscar por responsable, código, descripción…" value={q}
               onChange={(e) => setQ(e.target.value)} />
        <button type="submit" disabled={buscando}>{buscando ? 'Buscando…' : 'Buscar'}</button>
        <button type="button" onClick={handleExportar} disabled={exportando || resultados.length === 0}>
          {exportando ? 'Exportando…' : 'Exportar CSV'}
        </button>
      </form>
      {error && <p className="form-error" role="alert">{error}</p>}
      {total !== null && <p className="footnote">{total} resultado(s)</p>}
      {resultados.length > 0 && (
        <div className="table-scroll"><table className="data-table">
          <thead><tr><th>Tabla</th><th>ID</th><th>Fecha</th><th>Sensible</th></tr></thead>
          <tbody>
            {resultados.map((item) => (
              <tr key={`${item.tabla}-${item.id}`} className={item.restringido ? 'row-restricted' : undefined}>
                <td>{item.tabla}</td>
                <td>{item.id}</td>
                <td>{item.fecha ?? '—'}</td>
                <td>{item.sensible ? (item.restringido ? 'Sí (restringido)' : 'Sí') : 'No'}</td>
              </tr>
            ))}
          </tbody>
        </table></div>
      )}
    </section>
  );
}
