import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Layout } from './Layout';

const auth = vi.hoisted(() => ({ usuario: { nombre: 'Admin', rol_nombre: 'Administrador', permisos: {} as Record<string, Record<string, boolean>> }, logout: vi.fn() }));
vi.mock('./AuthContext', () => ({ useAuth: () => auth }));
vi.mock('../components/FeedbackProvider', () => ({ useFeedback: () => ({ notify: vi.fn() }) }));

function renderLayout() {
  return render(<MemoryRouter><Layout /></MemoryRouter>);
}

beforeEach(() => { auth.usuario.permisos = {}; });

describe('navegación de Departamento Médico', () => {
  it('muestra los cinco hijos a ROLE_ADMIN cuando la matriz los habilita', async () => {
    auth.usuario.permisos = {
      ATENCIONES: { read: true }, RIESGOS_TRABAJO: { read: true }, AUSENTISMO: { read: true }, ACCIDENTES: { read: true }, FORMULARIOS: { read: true },
    };
    renderLayout();
    await userEvent.click(screen.getByRole('button', { name: /departamento médico/i }));
    expect(screen.getByRole('link', { name: 'Atenciones' })).toHaveAttribute('href', '/trabajo-social/departamento-medico/atenciones');
    expect(screen.getByRole('link', { name: 'Riesgos de trabajo' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ausentismos' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Accidentes' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Formularios' })).toBeInTheDocument();
  });

  it('no muestra Atenciones ni los otros hijos sin su permiso de lectura', async () => {
    renderLayout();
    expect(screen.queryByRole('button', { name: /departamento médico/i })).not.toBeInTheDocument();
  });
});
