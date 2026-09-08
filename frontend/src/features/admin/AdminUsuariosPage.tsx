import { useEffect, useState, type FormEvent } from 'react';
import { actualizarUsuario, crearUsuario, listarAdministracion, type DatosAdministracion } from '../../api/admin';
import { HttpError } from '../../api/client';
import { useFeedback } from '../../components/FeedbackProvider';
import { Modal } from '../../components/Modal';

const FORMULARIO_INICIAL = { nombre: '', correo: '', rolId: '', password: '', confirmarPassword: '' };
const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export function AdminUsuariosPage() {
  const { notify } = useFeedback();
  const [datos, setDatos] = useState<DatosAdministracion | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [guardando, setGuardando] = useState<string | null>(null);
  const [modalAbierto, setModalAbierto] = useState(false);
  const [formulario, setFormulario] = useState(FORMULARIO_INICIAL);
  const [creando, setCreando] = useState(false);
  const [errorCreacion, setErrorCreacion] = useState<string | null>(null);

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
      notify('Usuario actualizado correctamente.');
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible guardar los cambios.');
    } finally {
      setGuardando(null);
    }
  }

  function abrirModal() {
    setFormulario({ ...FORMULARIO_INICIAL, rolId: datos?.roles[0]?.id_rol ?? '' });
    setErrorCreacion(null);
    setModalAbierto(true);
  }

  function cerrarModal() {
    if (creando) return;
    setModalAbierto(false);
    setFormulario(FORMULARIO_INICIAL);
    setErrorCreacion(null);
  }

  async function handleCrear(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nombre = formulario.nombre.trim();
    const correo = formulario.correo.trim().toLowerCase();
    if (!nombre || !correo || !formulario.rolId) {
      setErrorCreacion('Complete todos los campos obligatorios.');
      return;
    }
    if (!EMAIL_PATTERN.test(correo)) {
      setErrorCreacion('Ingrese un correo electrónico válido.');
      return;
    }
    if (formulario.password.length < 12
      || formulario.password.toLowerCase() === formulario.password
      || formulario.password.toUpperCase() === formulario.password
      || !/\d/.test(formulario.password)) {
      setErrorCreacion('La contraseña debe tener al menos 12 caracteres y combinar mayúsculas, minúsculas y números.');
      return;
    }
    if (formulario.password !== formulario.confirmarPassword) {
      setErrorCreacion('Las contraseñas no coinciden.');
      return;
    }

    setCreando(true);
    setErrorCreacion(null);
    try {
      await crearUsuario({ nombre, correo, rol_id: formulario.rolId, password: formulario.password });
      setModalAbierto(false);
      setFormulario(FORMULARIO_INICIAL);
      await cargar();
      notify('Usuario creado correctamente.');
    } catch (err) {
      setErrorCreacion(err instanceof HttpError ? err.message : 'No fue posible crear el usuario.');
    } finally {
      setCreando(false);
    }
  }

  if (cargando) return <p>Cargando…</p>;
  if (!datos) return <p className="form-error">{error ?? 'No fue posible cargar la administración.'}</p>;

  return (
    <section className="panel wide-panel">
      <div className="panel-header">
        <h2>Usuarios y roles</h2>
        <button type="button" onClick={abrirModal}>+ Crear usuario</button>
      </div>
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="table-scroll"><table className="data-table">
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
      </table></div>
      {modalAbierto && (
        <Modal titulo="Crear usuario" onClose={cerrarModal} closeOnBackdrop={!creando}>
          <form className="admin-user-form" onSubmit={handleCrear} noValidate>
            {errorCreacion && <p className="form-error" role="alert">{errorCreacion}</p>}
            <label>
              Nombre completo
              <input
                data-autofocus type="text" required autoComplete="name" value={formulario.nombre}
                onChange={(event) => setFormulario({ ...formulario, nombre: event.target.value })}
              />
            </label>
            <label>
              Correo electrónico
              <input
                type="email" required autoComplete="email" value={formulario.correo}
                onChange={(event) => setFormulario({ ...formulario, correo: event.target.value.toLowerCase() })}
              />
            </label>
            <label>
              Rol
              <select
                required value={formulario.rolId}
                onChange={(event) => setFormulario({ ...formulario, rolId: event.target.value })}
              >
                {datos.roles.map((rol) => <option key={rol.id_rol} value={rol.id_rol}>{rol.nombre}</option>)}
              </select>
            </label>
            <label>
              Contraseña temporal
              <input
                type="password" required minLength={12} autoComplete="new-password" value={formulario.password}
                onChange={(event) => setFormulario({ ...formulario, password: event.target.value })}
              />
            </label>
            <p className="password-help">Mínimo 12 caracteres, con mayúsculas, minúsculas y números.</p>
            <label>
              Confirmar contraseña
              <input
                type="password" required minLength={12} autoComplete="new-password"
                value={formulario.confirmarPassword}
                onChange={(event) => setFormulario({ ...formulario, confirmarPassword: event.target.value })}
              />
            </label>
            <label>
              Estado
              <input type="text" value="Activo" disabled aria-describedby="estado-creacion-ayuda" />
            </label>
            <span id="estado-creacion-ayuda" className="visually-hidden">Los usuarios nuevos se crean activos.</span>
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={cerrarModal} disabled={creando}>Cancelar</button>
              <button type="submit" disabled={creando}>{creando ? 'Creando…' : 'Crear usuario'}</button>
            </div>
          </form>
        </Modal>
      )}
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
