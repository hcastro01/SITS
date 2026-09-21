import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { LoginPage } from './LoginPage';
import { HttpError } from '../../api/client';

const { fetchAuthenticationRequirements, fetchCurrentUser, login: loginRequest, logout: logoutRequest } = vi.hoisted(() => ({
  fetchAuthenticationRequirements: vi.fn(),
  fetchCurrentUser: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
}));

vi.mock('../../api/auth', () => ({
  fetchAuthenticationRequirements,
  fetchCurrentUser,
  login: loginRequest,
  logout: logoutRequest,
}));

// AuthProvider real (no mockeado): solo se reemplazan las llamadas HTTP de app/api/auth.
import { AuthProvider } from '../../app/AuthContext';

function renderLoginPage() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <AuthProvider><LoginPage /></AuthProvider>
    </MemoryRouter>,
  );
}

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchCurrentUser.mockRejectedValue(new HttpError(401, { ok: false, code: 'SESSION_REQUIRED', message: 'x', correlationId: '' }));
    fetchAuthenticationRequirements.mockResolvedValue({ password_required: true });
  });

  it('muestra el formulario de acceso con correo y contraseña', async () => {
    renderLoginPage();
    await waitFor(() => expect(screen.getByLabelText('Correo electrónico')).toBeInTheDocument());
    expect(screen.getByLabelText('Contraseña')).toBeInTheDocument();
    expect(screen.getByText(/credenciales asignadas/)).toBeInTheDocument();
  });

  it('muestra el mensaje de error del servidor si el login falla', async () => {
    loginRequest.mockRejectedValue(new HttpError(403, { ok: false, code: 'USER_NOT_REGISTERED', message: 'Su usuario no está registrado.', correlationId: '' }));
    const usuarioEvento = userEvent.setup();
    renderLoginPage();
    await waitFor(() => screen.getByLabelText('Correo electrónico'));
    await usuarioEvento.type(screen.getByLabelText('Correo electrónico'), 'nadie@example.com');
    await usuarioEvento.type(screen.getByLabelText('Contraseña'), 'ClaveSegura123');
    await usuarioEvento.click(screen.getByRole('button', { name: 'Ingresar' }));
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Su usuario no está registrado.'));
  });

  it('permite el acceso de desarrollo sin contraseña cuando el backend lo declara', async () => {
    fetchAuthenticationRequirements.mockResolvedValue({ password_required: false });
    loginRequest.mockResolvedValue({ id_usuario: 'qa', correo: 'qa@example.test', nombre: 'QA', rol_id: 'ROLE_ADMIN', rol_nombre: 'Admin', permisos: {} });
    const usuarioEvento = userEvent.setup();
    renderLoginPage();
    const correo = await screen.findByLabelText('Correo electrónico');
    const password = screen.getByLabelText('Contraseña (opcional en este entorno)');
    await waitFor(() => expect(password).not.toBeRequired());
    await usuarioEvento.type(correo, 'qa@example.test');
    await usuarioEvento.click(screen.getByRole('button', { name: 'Ingresar' }));
    await waitFor(() => expect(loginRequest).toHaveBeenCalledWith('qa@example.test', undefined));
  });
});
