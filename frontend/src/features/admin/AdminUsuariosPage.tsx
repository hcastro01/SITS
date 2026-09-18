import { useEffect, useState, type FormEvent } from 'react';
import {
  actualizarUsuario, crearUsuario, eliminarUsuario, listarAdministracion, restaurarUsuario, restablecerPasswordUsuario,
  type DatosAdministracion, type UsuarioAdmin,
} from '../../api/admin';
import { HttpError } from '../../api/client';
import { useFeedback } from '../../components/FeedbackProvider';
import { Modal } from '../../components/Modal';

const FORMULARIO_INICIAL = { nombre: '', correo: '', rolId: '', password: '', confirmarPassword: '' };
const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const PASSWORD_ERROR = 'La contraseña debe tener al menos 12 caracteres y combinar mayúsculas, minúsculas y números.';

function passwordIsValid(password: string) {
  return password.length >= 12
    && password.toLowerCase() !== password
    && password.toUpperCase() !== password
    && /\d/.test(password);
}

export function AdminUsuariosPage() {
  const { notify } = useFeedback();
  const [datos, setDatos] = useState<DatosAdministracion | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [modalAbierto, setModalAbierto] = useState(false);
  const [usuarioEditando, setUsuarioEditando] = useState<UsuarioAdmin | null>(null);
  const [formulario, setFormulario] = useState(FORMULARIO_INICIAL);
  const [creando, setCreando] = useState(false);
  const [errorCreacion, setErrorCreacion] = useState<string | null>(null);
  const [incluirEliminados, setIncluirEliminados] = useState(false);
  const [usuarioEliminando, setUsuarioEliminando] = useState<UsuarioAdmin | null>(null);
  const [motivoEliminacion, setMotivoEliminacion] = useState('');
  const [eliminando, setEliminando] = useState(false);
  const [restaurandoId, setRestaurandoId] = useState<string | null>(null);
  const [errorEliminacion, setErrorEliminacion] = useState<string | null>(null);

  async function cargar(incluir = incluirEliminados) {
    setError(null);
    try {
      setDatos(await listarAdministracion(incluir));
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible cargar la administración.');
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => { cargar(); }, []);

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

  function abrirEliminacion(usuario: UsuarioAdmin) {
    setUsuarioEliminando(usuario);
    setMotivoEliminacion('');
    setErrorEliminacion(null);
  }

  function cerrarEliminacion() {
    if (eliminando) return;
    setUsuarioEliminando(null);
    setMotivoEliminacion('');
    setErrorEliminacion(null);
  }

  async function handleEliminar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!usuarioEliminando) return;
    const motivo = motivoEliminacion.trim();
    if (!motivo) {
      setErrorEliminacion('Indique el motivo de eliminación.');
      return;
    }
    setEliminando(true);
    setErrorEliminacion(null);
    try {
      await eliminarUsuario(usuarioEliminando.id_usuario, usuarioEliminando.version, motivo);
      await cargar();
      setUsuarioEliminando(null);
      setMotivoEliminacion('');
      notify('Usuario eliminado. Su historial y trazabilidad se conservaron.');
    } catch (err) {
      setErrorEliminacion(err instanceof HttpError ? err.message : 'No fue posible eliminar el usuario.');
    } finally {
      setEliminando(false);
    }
  }

  async function handleRestaurar(usuario: UsuarioAdmin) {
    setRestaurandoId(usuario.id_usuario);
    setError(null);
    try {
      await restaurarUsuario(usuario.id_usuario, usuario.version);
      await cargar();
      notify('Usuario restaurado correctamente.');
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible restaurar el usuario.');
    } finally {
      setRestaurandoId(null);
    }
  }

  async function cambiarIncluirEliminados(incluir: boolean) {
    setIncluirEliminados(incluir);
    setCargando(true);
    await cargar(incluir);
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
    if (!passwordIsValid(formulario.password)) {
      setErrorCreacion(PASSWORD_ERROR);
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

  if (cargando) return <div className="module-state" role="status">Cargando…</div>;
  if (!datos) return <p className="form-error">{error ?? 'No fue posible cargar la administración.'}</p>;

  return (
    <section className="module-list-page admin-page admin-users-page">
      <header className="module-page-hero">
        <div><p className="eyebrow">Administración</p><h2>Usuarios y roles</h2><p>Gestione las cuentas activas y sus roles asignados.</p></div>
        <button type="button" onClick={abrirModal}>+ Crear usuario</button>
      </header>
      {error && <p className="form-error" role="alert">{error}</p>}
      <section className="module-table-card"><div className="module-table-card-heading"><div><h3>Usuarios registrados</h3><p>Los cambios se guardan por usuario y conservan su trazabilidad.</p></div><div className="admin-user-list-controls">{datos.puede_eliminar_usuarios && <label className="checkbox-label"><input type="checkbox" checked={incluirEliminados} onChange={(event) => cambiarIncluirEliminados(event.target.checked)} />Ver usuarios eliminados</label>}<span className="badge">{datos.usuarios.length} usuarios</span></div></div><div className="table-scroll"><table className="data-table module-data-table admin-data-table">
        <thead><tr><th>Correo</th><th>Nombre</th><th>Rol</th><th>Estado</th><th>Acciones</th></tr></thead>
        <tbody>
          {datos.usuarios.map((usuario) => (
            <FilaUsuario key={usuario.id_usuario} usuario={usuario} roles={datos.roles}
              puedeEliminar={datos.puede_eliminar_usuarios}
              onEditar={() => setUsuarioEditando(usuario)} onEliminar={() => abrirEliminacion(usuario)}
              onRestaurar={() => handleRestaurar(usuario)} restaurando={restaurandoId === usuario.id_usuario} />
          ))}
        </tbody>
      </table></div></section>
      {modalAbierto && (
        <Modal titulo="Crear usuario" onClose={cerrarModal} closeOnBackdrop={!creando}>
          <form className="admin-user-form module-form" onSubmit={handleCrear} noValidate>
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
      {usuarioEditando && (
        <EditarUsuarioModal
          usuario={usuarioEditando}
          roles={datos.roles}
          onClose={() => setUsuarioEditando(null)}
          onSaved={async () => {
            await cargar();
            setUsuarioEditando(null);
          }}
        />
      )}
      {usuarioEliminando && (
        <Modal titulo="Eliminar usuario" onClose={cerrarEliminacion} closeOnBackdrop={!eliminando} size="small">
          <form className="admin-user-form module-form" onSubmit={handleEliminar} noValidate>
            {errorEliminacion && <p className="form-error" role="alert">{errorEliminacion}</p>}
            <p className="dialog-message">El usuario perderá acceso al sistema, pero su información histórica y trazabilidad se conservarán.</p>
            <dl className="admin-user-summary"><div><dt>Nombre</dt><dd>{usuarioEliminando.nombre}</dd></div><div><dt>Correo</dt><dd>{usuarioEliminando.correo}</dd></div><div><dt>Rol</dt><dd>{datos.roles.find((rol) => rol.id_rol === usuarioEliminando.rol_id)?.nombre ?? usuarioEliminando.rol_id}</dd></div></dl>
            <label>
              Motivo de eliminación
              <textarea data-autofocus required value={motivoEliminacion} onChange={(event) => setMotivoEliminacion(event.target.value)} />
            </label>
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={cerrarEliminacion} disabled={eliminando}>Cancelar</button>
              <button type="submit" className="danger" disabled={eliminando}>{eliminando ? 'Eliminando…' : 'Eliminar usuario'}</button>
            </div>
          </form>
        </Modal>
      )}
    </section>
  );
}

function FilaUsuario({ usuario, roles, puedeEliminar, onEditar, onEliminar, onRestaurar, restaurando }: {
  usuario: DatosAdministracion['usuarios'][number];
  roles: DatosAdministracion['roles'];
  puedeEliminar: boolean;
  onEditar: () => void;
  onEliminar: () => void;
  onRestaurar: () => void;
  restaurando: boolean;
}) {
  return (
    <tr>
      <td>{usuario.correo}</td>
      <td>{usuario.nombre}</td>
      <td>{roles.find((rol) => rol.id_rol === usuario.rol_id)?.nombre ?? usuario.rol_id}</td>
      <td><span className={`badge ${usuario.eliminado ? 'badge--danger' : usuario.estado === 'ACTIVO' ? '' : 'badge-muted'}`}>{usuario.eliminado ? 'ELIMINADO' : usuario.estado === 'ACTIVO' ? 'Activo' : 'Inactivo'}</span></td>
      <td><div className="admin-user-actions">{usuario.eliminado ? (
        puedeEliminar && <button type="button" className="secondary" onClick={onRestaurar} disabled={restaurando}>{restaurando ? 'Restaurando…' : 'Restaurar'}</button>
      ) : <><button type="button" className="secondary" onClick={onEditar}>Editar</button>{puedeEliminar && <button type="button" className="danger" onClick={onEliminar}>Eliminar</button>}</>}</div></td>
    </tr>
  );
}

function EditarUsuarioModal({
  usuario, roles, onClose, onSaved,
}: {
  usuario: UsuarioAdmin;
  roles: DatosAdministracion['roles'];
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const { notify } = useFeedback();
  const [nombre, setNombre] = useState(usuario.nombre);
  const [correo, setCorreo] = useState(usuario.correo);
  const [rolId, setRolId] = useState(usuario.rol_id);
  const [estado, setEstado] = useState<'ACTIVO' | 'INACTIVO'>(usuario.estado === 'INACTIVO' ? 'INACTIVO' : 'ACTIVO');
  const [password, setPassword] = useState('');
  const [confirmarPassword, setConfirmarPassword] = useState('');
  const [mostrarPassword, setMostrarPassword] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nombreNormalizado = nombre.trim();
    const correoNormalizado = correo.trim().toLowerCase();
    if (!nombreNormalizado || !correoNormalizado || !rolId) {
      setError('Complete todos los campos obligatorios.');
      return;
    }
    if (!EMAIL_PATTERN.test(correoNormalizado)) {
      setError('Ingrese un correo electrónico válido.');
      return;
    }
    if (password || confirmarPassword) {
      if (!passwordIsValid(password)) {
        setError(PASSWORD_ERROR);
        return;
      }
      if (password !== confirmarPassword) {
        setError('Las contraseñas no coinciden.');
        return;
      }
    }

    const datosCambiados = nombreNormalizado !== usuario.nombre
      || correoNormalizado !== usuario.correo
      || rolId !== usuario.rol_id
      || estado !== usuario.estado;
    if (!datosCambiados && !password) {
      onClose();
      return;
    }

    setGuardando(true);
    setError(null);
    try {
      let versionActual = usuario.version;
      if (datosCambiados) {
        const actualizado = await actualizarUsuario(usuario.id_usuario, {
          nombre: nombreNormalizado, correo: correoNormalizado, rol_id: rolId, estado, expected_version: versionActual,
        });
        versionActual = actualizado.version;
      }
      if (password) {
        await restablecerPasswordUsuario(usuario.id_usuario, password, versionActual);
      }
      await onSaved();
      notify(password ? 'Usuario y contraseña actualizados correctamente.' : 'Usuario actualizado correctamente.');
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible guardar los cambios.');
    } finally {
      setGuardando(false);
    }
  }

  return (
    <Modal titulo="Editar usuario" onClose={() => !guardando && onClose()} closeOnBackdrop={!guardando} size="medium">
      <form className="admin-user-form module-form" onSubmit={handleSubmit} noValidate>
        {error && <p className="form-error" role="alert">{error}</p>}
        <fieldset disabled={guardando}>
          <legend>Datos del usuario</legend>
          <label>
            Nombre completo
            <input data-autofocus type="text" required autoComplete="name" value={nombre} onChange={(event) => setNombre(event.target.value)} />
          </label>
          <label>
            Correo electrónico
            <input type="email" required autoComplete="email" value={correo} onChange={(event) => setCorreo(event.target.value)} />
          </label>
          <label>
            Rol
            <select required value={rolId} onChange={(event) => setRolId(event.target.value)}>
              {roles.map((rol) => <option key={rol.id_rol} value={rol.id_rol}>{rol.nombre}</option>)}
            </select>
          </label>
          <label>
            Estado
            <select value={estado} onChange={(event) => setEstado(event.target.value as 'ACTIVO' | 'INACTIVO')}>
              <option value="ACTIVO">Activo</option>
              <option value="INACTIVO">Inactivo</option>
            </select>
          </label>
        </fieldset>
        <fieldset disabled={guardando}>
          <legend>Seguridad</legend>
          <p className="password-help">La contraseña actual no puede visualizarse por motivos de seguridad. Puede establecer una nueva contraseña para este usuario.</p>
          <label>
            Nueva contraseña
            <input type={mostrarPassword ? 'text' : 'password'} autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} />
          </label>
          <label>
            Confirmar nueva contraseña
            <input type={mostrarPassword ? 'text' : 'password'} autoComplete="new-password" value={confirmarPassword} onChange={(event) => setConfirmarPassword(event.target.value)} />
          </label>
          <label className="checkbox-label">
            <input type="checkbox" checked={mostrarPassword} onChange={(event) => setMostrarPassword(event.target.checked)} />
            Mostrar contraseña
          </label>
          <p className="password-help">Si deja estos campos vacíos, la contraseña no se modifica. Mínimo 12 caracteres, con mayúsculas, minúsculas y números.</p>
        </fieldset>
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={onClose} disabled={guardando}>Cancelar</button>
          <button type="submit" disabled={guardando}>{guardando ? 'Guardando…' : 'Guardar cambios'}</button>
        </div>
      </form>
    </Modal>
  );
}
