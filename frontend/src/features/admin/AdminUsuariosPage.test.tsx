import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { DatosAdministracion, UsuarioAdmin } from '../../api/admin';
import { HttpError } from '../../api/client';
import { FeedbackProvider } from '../../components/FeedbackProvider';
import { AdminUsuariosPage } from './AdminUsuariosPage';

const api = vi.hoisted(() => ({
  actualizarUsuario: vi.fn(),
  crearUsuario: vi.fn(),
  listarAdministracion: vi.fn(),
  restablecerPasswordUsuario: vi.fn(),
}));

vi.mock('../../api/admin', async () => ({
  ...await vi.importActual<typeof import('../../api/admin')>('../../api/admin'),
  ...api,
}));

const usuario: UsuarioAdmin = {
  id_usuario: 'u-1', correo: 'ana@example.com', nombre: 'Ana Pérez', rol_id: 'ROLE_CONSULTA',
  estado: 'ACTIVO', activo: true, eliminado: false, version: 3,
};

const datos: DatosAdministracion = {
  usuarios: [usuario],
  roles: [
    { id_rol: 'ROLE_CONSULTA', nombre: 'Consulta', descripcion: null },
    { id_rol: 'ROLE_ADMIN', nombre: 'Administrador', descripcion: null },
  ],
  permisos: [],
};

async function renderPage() {
  api.listarAdministracion.mockResolvedValue(datos);
  const user = userEvent.setup();
  render(<FeedbackProvider><AdminUsuariosPage /></FeedbackProvider>);
  await screen.findByText(usuario.correo);
  return user;
}

async function abrirEditor() {
  const user = await renderPage();
  await user.click(screen.getByRole('button', { name: 'Editar' }));
  const dialog = await screen.findByRole('dialog', { name: 'Editar usuario' });
  return { user, dialog };
}

describe('AdminUsuariosPage: edición y restablecimiento seguro', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    document.body.style.overflow = '';
  });

  afterEach(() => cleanup());

  it('muestra Editar y precarga únicamente los datos permitidos con contraseña vacía', async () => {
    const { dialog } = await abrirEditor();
    expect(screen.getByRole('columnheader', { name: 'Acciones' })).toBeInTheDocument();
    expect(within(dialog).getByLabelText('Nombre completo')).toHaveValue('Ana Pérez');
    expect(within(dialog).getByLabelText('Correo electrónico')).toHaveValue('ana@example.com');
    expect(within(dialog).getByLabelText('Rol')).toHaveValue('ROLE_CONSULTA');
    expect(within(dialog).getByLabelText('Estado')).toHaveValue('ACTIVO');
    expect(within(dialog).getByLabelText('Nueva contraseña')).toHaveValue('');
    expect(within(dialog).getByLabelText('Confirmar nueva contraseña')).toHaveValue('');
    expect(dialog).not.toHaveTextContent('password_hash');
  });

  it('muestra y oculta sólo la nueva contraseña escrita', async () => {
    const { user, dialog } = await abrirEditor();
    const password = within(dialog).getByLabelText('Nueva contraseña');
    await user.type(password, 'ClaveNueva456');
    expect(password).toHaveAttribute('type', 'password');
    await user.click(within(dialog).getByLabelText('Mostrar contraseña'));
    expect(password).toHaveAttribute('type', 'text');
    await user.click(within(dialog).getByLabelText('Mostrar contraseña'));
    expect(password).toHaveAttribute('type', 'password');
  });

  it('bloquea el envío si la confirmación no coincide', async () => {
    const { user, dialog } = await abrirEditor();
    await user.type(within(dialog).getByLabelText('Nueva contraseña'), 'ClaveNueva456');
    await user.type(within(dialog).getByLabelText('Confirmar nueva contraseña'), 'OtraClave456');
    await user.click(within(dialog).getByRole('button', { name: 'Guardar cambios' }));
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('Las contraseñas no coinciden.');
    expect(api.actualizarUsuario).not.toHaveBeenCalled();
    expect(api.restablecerPasswordUsuario).not.toHaveBeenCalled();
  });

  it('guarda los datos y no llama al restablecimiento si las contraseñas quedan vacías', async () => {
    api.actualizarUsuario.mockResolvedValue({ ...usuario, nombre: 'Ana Actualizada', version: 4 });
    const { user, dialog } = await abrirEditor();
    await user.clear(within(dialog).getByLabelText('Nombre completo'));
    await user.type(within(dialog).getByLabelText('Nombre completo'), 'Ana Actualizada');
    await user.click(within(dialog).getByRole('button', { name: 'Guardar cambios' }));
    await waitFor(() => expect(api.actualizarUsuario).toHaveBeenCalledWith('u-1', {
      nombre: 'Ana Actualizada', correo: 'ana@example.com', rol_id: 'ROLE_CONSULTA', estado: 'ACTIVO', expected_version: 3,
    }));
    expect(api.restablecerPasswordUsuario).not.toHaveBeenCalled();
  });

  it('restablece la contraseña mediante la acción separada y usa la versión actual', async () => {
    api.restablecerPasswordUsuario.mockResolvedValue({ ...usuario, version: 4 });
    const { user, dialog } = await abrirEditor();
    await user.type(within(dialog).getByLabelText('Nueva contraseña'), 'ClaveNueva456');
    await user.type(within(dialog).getByLabelText('Confirmar nueva contraseña'), 'ClaveNueva456');
    await user.click(within(dialog).getByRole('button', { name: 'Guardar cambios' }));
    await waitFor(() => expect(api.restablecerPasswordUsuario).toHaveBeenCalledWith('u-1', 'ClaveNueva456', 3));
    expect(api.actualizarUsuario).not.toHaveBeenCalled();
  });

  it('presenta el error del backend y evita el doble envío mientras guarda', async () => {
    let resolver: ((value: UsuarioAdmin) => void) | undefined;
    api.actualizarUsuario.mockImplementation(() => new Promise<UsuarioAdmin>((resolve) => { resolver = resolve; }));
    const { user, dialog } = await abrirEditor();
    await user.clear(within(dialog).getByLabelText('Nombre completo'));
    await user.type(within(dialog).getByLabelText('Nombre completo'), 'Ana Dos');
    const submit = within(dialog).getByRole('button', { name: 'Guardar cambios' });
    await user.click(submit);
    await user.click(submit);
    expect(api.actualizarUsuario).toHaveBeenCalledTimes(1);
    resolver?.({ ...usuario, nombre: 'Ana Dos', version: 4 });
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Editar usuario' })).not.toBeInTheDocument());

    cleanup();
    const retry = await abrirEditor();
    api.actualizarUsuario.mockRejectedValueOnce(new HttpError(409, {
      ok: false, code: 'VERSION_CONFLICT', message: 'El registro fue modificado por otro usuario.', correlationId: 'c-1',
    }));
    await retry.user.clear(within(retry.dialog).getByLabelText('Nombre completo'));
    await retry.user.type(within(retry.dialog).getByLabelText('Nombre completo'), 'Ana Tres');
    await retry.user.click(within(retry.dialog).getByRole('button', { name: 'Guardar cambios' }));
    expect(await within(retry.dialog).findByRole('alert')).toHaveTextContent('El registro fue modificado por otro usuario.');
  });

});
