import { useEffect, useState } from 'react';
import { actualizarUsuario, listarAdministracion, type DatosAdministracion } from '../../api/admin';
import { HttpError } from '../../api/client';

export function AdminUsuariosPage() {
  const [datos, setDatos] = useState<DatosAdministracion | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [guardando, setGuardando] = useState<string | null>(null);

  async function cargar() {
    setError(null);
    try {
      setDatos(await listarAdministracion());
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible cargar la administración.');
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => { cargar(); }, []);

  async function handleGuardar(idUsuario: string, rolId: string, estado: string, version: number) {
    setGuardando(idUsuario);
    setError(null);
    try {
      await actualizarUsuario(idUsuario, rolId, estado, version);
      await cargar();
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible guardar los cambios.');
    } finally {
      setGuardando(null);
    }
  }

  if (cargando) return <p>Cargando…</p>;
  if (!datos) return <p className="form-error">{error ?? 'No fue posible cargar la administración.'}</p>;

  return (
    <section className="panel wide-panel">
      <h2>Usuarios y roles</h2>
      {error && <p className="form-error" role="alert">{error}</p>}
      <table className="data-table">
        <thead><tr><th>Correo</th><th>Nombre</th><th>Rol</th><th>Estado</th><th></th></tr></thead>
        <tbody>
          {datos.usuarios.map((usuario) => (
            <FilaUsuario
              key={usuario.id_usuario}
              usuario={usuario}
              roles={datos.roles}
              guardando={guardando === usuario.id_usuario}
              onGuardar={handleGuardar}
            />
          ))}
        </tbody>
      </table>
    </section>
  );
}

function FilaUsuario({
  usuario, roles, guardando, onGuardar,
}: {
  usuario: DatosAdministracion['usuarios'][number];
  roles: DatosAdministracion['roles'];
  guardando: boolean;
  onGuardar: (idUsuario: string, rolId: string, estado: string, version: number) => void;
}) {
  const [rolId, setRolId] = useState(usuario.rol_id);
  const [estado, setEstado] = useState(usuario.estado);
  const cambiado = rolId !== usuario.rol_id || estado !== usuario.estado;

  return (
    <tr>
      <td>{usuario.correo}</td>
      <td>{usuario.nombre}</td>
      <td>
        <select value={rolId} onChange={(event) => setRolId(event.target.value)}>
          {roles.map((rol) => <option key={rol.id_rol} value={rol.id_rol}>{rol.nombre}</option>)}
        </select>
      </td>
      <td>
        <select value={estado} onChange={(event) => setEstado(event.target.value)}>
          <option value="ACTIVO">Activo</option>
          <option value="INACTIVO">Inactivo</option>
        </select>
      </td>
      <td>
        {cambiado && (
          <button onClick={() => onGuardar(usuario.id_usuario, rolId, estado, usuario.version)} disabled={guardando}>
            {guardando ? 'Guardando…' : 'Guardar'}
          </button>
        )}
      </td>
    </tr>
  );
}
