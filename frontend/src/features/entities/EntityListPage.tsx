import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { HttpError } from '../../api/client';
import type { EntityRecord } from '../../api/entities';
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
  const isPeople = config.tipoRegistro === 'PERSONAS';
  const canCreateBase = canAccess(usuario, config.tipoRegistro, 'create');
  const canCreateFromForm = canCreateBase && canAccess(usuario, 'RESPUESTAS', 'create');

  useEffect(() => {
    let activo = true;
    config.api.list()
      .then((datos) => { if (activo) setRegistros(datos); })
      .catch((err: unknown) => {
        if (activo) setError(err instanceof HttpError ? err.message : `No fue posible cargar ${config.titulo.toLowerCase()}.`);
      })
      .finally(() => { if (activo) setCargando(false); });
    return () => { activo = false; };
  }, [config]);

  const columnas = config.campos.filter((campo) => campo.enLista !== false).slice(0, 5);

  return (
    <section className="panel wide-panel">
      <div className="panel-header">
        <h2>{config.titulo}</h2>
        <div className="panel-header-actions">
          {isPeople && canCreateBase && <button type="button" className="secondary" onClick={() => setModalAbierto(true)}>Nueva persona</button>}
          {canCreateFromForm && <button type="button" className="button-link as-button" onClick={() => setSelectorAbierto(true)}>Nuevo registro</button>}
        </div>
      </div>
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

      <ModuleFormRecordsPanel module={config.tipoRegistro} />

      {isPeople && modalAbierto && (
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
