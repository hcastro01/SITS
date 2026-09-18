import { useEffect, useMemo, useState } from 'react';
import { actualizarPermiso, listarAdministracion, type DatosAdministracion, type PermisoAdmin } from '../../api/admin';
import { HttpError } from '../../api/client';
import { useFeedback } from '../../components/FeedbackProvider';

const ACCIONES: Array<keyof Pick<PermisoAdmin, 'create' | 'read' | 'edit' | 'delete' | 'sensitive' | 'export'>> = [
  'create', 'read', 'edit', 'delete', 'sensitive', 'export',
];
const ETIQUETAS_ACCION: Record<string, string> = {
  create: 'Crear', read: 'Leer', edit: 'Editar', delete: 'Eliminar', sensitive: 'Sensible', export: 'Exportar',
};

export function AdminPermisosPage() {
  const { notify } = useFeedback();
  const [datos, setDatos] = useState<DatosAdministracion | null>(null);
  const [rolSeleccionado, setRolSeleccionado] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [guardandoModulo, setGuardandoModulo] = useState<string | null>(null);

  async function cargar() {
    setError(null);
    try {
      const respuesta = await listarAdministracion();
      setDatos(respuesta);
      setRolSeleccionado((actual) => actual || respuesta.roles[0]?.id_rol || '');
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible cargar los permisos.');
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => { cargar(); }, []);

  const permisosDelRol = useMemo(
    () => (datos ? datos.permisos.filter((permiso) => permiso.rol_id === rolSeleccionado) : []),
    [datos, rolSeleccionado],
  );

  async function handleGuardarModulo(permiso: PermisoAdmin, derechos: Record<string, boolean>) {
    setGuardandoModulo(permiso.modulo);
    setError(null);
    try {
      await actualizarPermiso(permiso.rol_id, permiso.modulo, derechos, permiso.version);
      await cargar();
      notify('Permisos actualizados correctamente.');
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible guardar el permiso.');
    } finally {
      setGuardandoModulo(null);
    }
  }

  if (cargando) return <div className="module-state" role="status">Cargando…</div>;
  if (!datos) return <p className="form-error">{error ?? 'No fue posible cargar los permisos.'}</p>;

  return (
    <section className="module-list-page admin-page admin-permissions-page">
      <header className="module-page-hero">
        <div><p className="eyebrow">Administración</p><h2>Roles y permisos</h2><p>Revise los permisos del rol seleccionado antes de guardar cambios.</p></div>
        <label className="admin-role-selector">Rol<select value={rolSeleccionado} onChange={(event) => setRolSeleccionado(event.target.value)}>
          {datos.roles.map((rol) => <option key={rol.id_rol} value={rol.id_rol}>{rol.nombre}</option>)}
        </select></label>
      </header>
      {error && <p className="form-error" role="alert">{error}</p>}
      <section className="module-table-card"><div className="module-table-card-heading"><div><h3>Matriz de permisos</h3><p>Seleccione únicamente los derechos autorizados para este rol.</p></div><span className="badge">{permisosDelRol.length} módulos</span></div><div className="table-scroll"><table className="data-table module-data-table admin-data-table permissions-table">
        <thead>
          <tr><th>Módulo</th>{ACCIONES.map((accion) => <th key={accion}>{ETIQUETAS_ACCION[accion]}</th>)}<th></th></tr>
        </thead>
        <tbody>
          {permisosDelRol.map((permiso) => (
            <FilaPermiso
              key={permiso.id_permiso}
              permiso={permiso}
              guardando={guardandoModulo === permiso.modulo}
              onGuardar={handleGuardarModulo}
            />
          ))}
        </tbody>
      </table></div></section>
    </section>
  );
}

function FilaPermiso({
  permiso, guardando, onGuardar,
}: {
  permiso: PermisoAdmin;
  guardando: boolean;
  onGuardar: (permiso: PermisoAdmin, derechos: Record<string, boolean>) => void;
}) {
  const [valores, setValores] = useState<Record<string, boolean>>(
    Object.fromEntries(ACCIONES.map((accion) => [accion, permiso[accion]])),
  );
  const cambiado = ACCIONES.some((accion) => valores[accion] !== permiso[accion]);

  return (
    <tr>
      <td>{permiso.modulo}</td>
      {ACCIONES.map((accion) => (
        <td key={accion}>
          <input
            type="checkbox"
            aria-label={`${ETIQUETAS_ACCION[accion]} en ${permiso.modulo}`}
            checked={valores[accion]}
            onChange={(event) => setValores((previo) => ({ ...previo, [accion]: event.target.checked }))}
          />
        </td>
      ))}
      <td>
        {cambiado && (
          <button onClick={() => onGuardar(permiso, valores)} disabled={guardando}>
            {guardando ? 'Guardando…' : 'Guardar'}
          </button>
        )}
      </td>
    </tr>
  );
}
