import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { LoginPage } from './LoginPage';
import { HttpError } from '../../api/client';

const { fetchCurrentUser, login: loginRequest, logout: logoutRequest } = vi.hoisted(() => ({
  fetchCurrentUser: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
}));

vi.mock('../../api/auth', () => ({ fetchCurrentUser, login: loginRequest, logout: logoutRequest }));

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
  });

  it('muestra el formulario de acceso temporal por correo', async () => {
    renderLoginPage();
    await waitFor(() => expect(screen.getByLabelText('Correo electrónico')).toBeInTheDocument());
    expect(screen.getByText(/Acceso temporal de desarrollo/)).toBeInTheDocument();
  });

  it('muestra el mensaje de error del servidor si el login falla', async () => {
    loginRequest.mockRejectedValue(new HttpError(403, { ok: false, code: 'USER_NOT_REGISTERED', message: 'Su usuario no está registrado.', correlationId: '' }));
    const usuarioEvento = userEvent.setup();
    renderLoginPage();
    await waitFor(() => screen.getByLabelText('Correo electrónico'));
    await usuarioEvento.type(screen.getByLabelText('Correo electrónico'), 'nadie@example.com');
    await usuarioEvento.click(screen.getByRole('button', { name: 'Ingresar' }));
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Su usuario no está registrado.'));
  });
});
