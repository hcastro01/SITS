import { useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { HttpError } from '../../api/client';
import type { EntityRecord, ContextualEntityClient, EntityClient } from '../../api/entities';
import { EntityFormModal } from './EntityFormModal';
import type { EntityPageConfig } from './EntityConfig';
import { useFeedback } from '../../components/FeedbackProvider';
import { ModuleFormRecordsPanel } from '../formularios/ModuleFormRecordsPanel';
import { ModuleFormSelector } from '../formularios/ModuleFormSelector';
import { useAuth } from '../../app/AuthContext';
import { canAccess } from '../../api/auth';

export function EntityListPage({ config }: { config: EntityPageConfig }) {
  const { notify } = useFeedback();
  const { usuario } = useAuth();
  const [registros, setRegistros] = useState<EntityRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [modalAbierto, setModalAbierto] = useState(false);
  const [selectorAbierto, setSelectorAbierto] = useState(false);
  const [filtros, setFiltros] = useState({ nombre: '', cedula: '', responsable: '', estado: '', desde: '', hasta: '' });
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [requestEpoch, setRequestEpoch] = useState(0);
  const isPeople = config.tipoRegistro === 'PERSONAS';
  const permissionModule = config.permissionModule ?? config.tipoRegistro;
  const canCreateBase = canAccess(usuario, permissionModule, 'create');
  const canCreateFromForm = canCreateBase && canAccess(usuario, 'RESPUESTAS', 'create');

  useEffect(() => {
    let activo = true;
    setCargando(true); setError(null);
    const request = config.contextual
      ? (config.api as ContextualEntityClient).list(new URLSearchParams({ ...filtros, limite: '25', offset: String(offset) }))
      : (config.api as EntityClient).list();
    request
      .then((datos) => {
        if (!activo) return;
        if (config.contextual) { const page = datos as { items: EntityRecord[]; total: number }; setRegistros(page.items); setTotal(page.total); }
        else setRegistros(datos as EntityRecord[]);
      })
      .catch((err: unknown) => {
        if (activo) setError(err instanceof HttpError ? err.message : `No fue posible cargar ${config.titulo.toLowerCase()}.`);
      })
      .finally(() => { if (activo) setCargando(false); });
    return () => { activo = false; };
  }, [config, filtros, offset, requestEpoch]);

  function applyFilters(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setOffset(0); setRequestEpoch((current) => current + 1); }
  function updateFilter(name: keyof typeof filtros, value: string) { setFiltros((current) => ({ ...current, [name]: value })); }
  function clearFilters() { setFiltros({ nombre: '', cedula: '', responsable: '', estado: '', desde: '', hasta: '' }); setOffset(0); }

  const columnas = config.campos.filter((campo) => campo.enLista !== false).slice(0, config.contextual ? 8 : 5);

  return (
    <section className="panel wide-panel">
      <div className="panel-header">
        <h2>{config.titulo}</h2>
        <div className="panel-header-actions">
          {(isPeople || config.contextual) && canCreateBase && <button type="button" className="secondary" onClick={() => setModalAbierto(true)}>Nuevo {config.tituloSingular}</button>}
          {!config.contextual && canCreateFromForm && <button type="button" className="button-link as-button" onClick={() => setSelectorAbierto(true)}>Nuevo registro</button>}
        </div>
      </div>
      {config.contextual && <form className="form-grid" onSubmit={applyFilters}>
        <label>Persona o nombre<input aria-label="Filtrar por nombre" value={filtros.nombre} onChange={(event) => updateFilter('nombre', event.target.value)} /></label>
        <label>Cédula<input aria-label="Filtrar por cédula" value={filtros.cedula} onChange={(event) => updateFilter('cedula', event.target.value)} /></label>
        <label>Responsable<input aria-label="Filtrar por responsable" value={filtros.responsable} onChange={(event) => updateFilter('responsable', event.target.value)} /></label>
        {config.campos.some((campo) => campo.nombre === 'estado') && <label>Estado<input aria-label="Filtrar por estado" value={filtros.estado} onChange={(event) => updateFilter('estado', event.target.value)} /></label>}
        <label>Fecha desde<input aria-label="Filtrar desde" type="date" value={filtros.desde} onChange={(event) => updateFilter('desde', event.target.value)} /></label>
        <label>Fecha hasta<input aria-label="Filtrar hasta" type="date" value={filtros.hasta} onChange={(event) => updateFilter('hasta', event.target.value)} /></label>
        <div className="button-row full-width"><button type="submit">Aplicar filtros</button><button type="button" className="secondary" onClick={clearFilters}>Limpiar filtros</button></div>
      </form>}
      {error && <p className="form-error" role="alert">{error}</p>}
      {cargando ? (
        <p>Cargando…</p>
      ) : registros.length === 0 ? (
        <p className="footnote">No hay registros todavía.</p>
      ) : (
        <div className="table-scroll"><table className="data-table">
          <thead>
            <tr>{columnas.map((campo) => <th key={campo.nombre}>{campo.etiqueta}</th>)}<th /></tr>
          </thead>
          <tbody>
            {registros.map((registro) => {
              const id = String(registro[config.api.idField]);
              return (
                <tr key={id}>
                  {columnas.map((campo) => (
                    <td key={campo.nombre}>{String(registro[campo.nombre] ?? '—')}</td>
                  ))}
                  <td><Link to={`${config.rutaBase}/${id}`}>Ver</Link></td>
                </tr>
              );
            })}
          </tbody>
        </table></div>
      )}

      {!config.contextual && <ModuleFormRecordsPanel module={config.tipoRegistro} />}

      {config.contextual && !cargando && !error && <div className="pagination-controls"><button type="button" className="secondary" disabled={!offset} onClick={() => setOffset(Math.max(0, offset - 25))}>Anterior</button><span>{total ? `Mostrando ${offset + 1}-${Math.min(offset + registros.length, total)} de ${total}` : '0 registros'}</span><button type="button" className="secondary" disabled={offset + registros.length >= total} onClick={() => setOffset(offset + 25)}>Siguiente</button></div>}

      {(isPeople || config.contextual) && modalAbierto && (
        <EntityFormModal
          config={config}
          onClose={() => setModalAbierto(false)}
          onSaved={(registro) => { setModalAbierto(false); setRegistros((previo) => [registro, ...previo]); notify('Registro guardado correctamente.'); }}
        />
      )}
      {selectorAbierto && <ModuleFormSelector module={config.tipoRegistro} moduleLabel={config.titulo}
                                              onClose={() => setSelectorAbierto(false)} />}
    </section>
  );
}
