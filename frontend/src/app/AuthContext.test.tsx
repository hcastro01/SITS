import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthProvider, useAuth } from './AuthContext';
import { HttpError } from '../api/client';

const { fetchCurrentUser, login: loginRequest, logout: logoutRequest } = vi.hoisted(() => ({
  fetchCurrentUser: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
}));

vi.mock('../api/auth', () => ({ fetchCurrentUser, login: loginRequest, logout: logoutRequest }));

const PERFIL = { id_usuario: 'u1', correo: 'ana@example.com', nombre: 'Ana', rol_id: 'ROLE_ADMIN', rol_nombre: 'Administrador' };

function Consumidor() {
  const { usuario, cargando, login, logout } = useAuth();
  if (cargando) return <p>Cargando…</p>;
  return (
    <div>
      <p>{usuario ? `Hola, ${usuario.nombre}` : 'Sin sesión'}</p>
      <button onClick={() => login('ana@example.com')}>Entrar</button>
      <button onClick={() => logout()}>Salir</button>
    </div>
  );
}

describe('AuthContext', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('resuelve el usuario vigente al montar', async () => {
    fetchCurrentUser.mockResolvedValue(PERFIL);
    render(<AuthProvider><Consumidor /></AuthProvider>);
    await waitFor(() => expect(screen.getByText('Hola, Ana')).toBeInTheDocument());
  });

  it('no reporta error cuando fetchCurrentUser devuelve 401 (sin sesión aún)', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    fetchCurrentUser.mockRejectedValue(new HttpError(401, { ok: false, code: 'SESSION_REQUIRED', message: 'x', correlationId: '' }));
    render(<AuthProvider><Consumidor /></AuthProvider>);
    await waitFor(() => expect(screen.getByText('Sin sesión')).toBeInTheDocument());
    expect(consoleError).not.toHaveBeenCalled();
  });

  it('login actualiza el usuario en contexto', async () => {
    fetchCurrentUser.mockRejectedValue(new HttpError(401, { ok: false, code: 'SESSION_REQUIRED', message: 'x', correlationId: '' }));
    loginRequest.mockResolvedValue(PERFIL);
    const usuarioEvento = userEvent.setup();
    render(<AuthProvider><Consumidor /></AuthProvider>);
    await waitFor(() => expect(screen.getByText('Sin sesión')).toBeInTheDocument());
    await usuarioEvento.click(screen.getByText('Entrar'));
    await waitFor(() => expect(screen.getByText('Hola, Ana')).toBeInTheDocument());
  });

  it('logout limpia el usuario del contexto', async () => {
    fetchCurrentUser.mockResolvedValue(PERFIL);
    logoutRequest.mockResolvedValue({ status: 'ok' });
    const usuarioEvento = userEvent.setup();
    render(<AuthProvider><Consumidor /></AuthProvider>);
    await waitFor(() => expect(screen.getByText('Hola, Ana')).toBeInTheDocument());
    await usuarioEvento.click(screen.getByText('Salir'));
    await waitFor(() => expect(screen.getByText('Sin sesión')).toBeInTheDocument());
  });
});
