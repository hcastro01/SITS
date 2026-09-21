import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Link, MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Layout } from './Layout';

const auth = vi.hoisted(() => ({ usuario: { nombre: 'Admin', rol_nombre: 'Administrador', permisos: {} as Record<string, Record<string, boolean>> }, logout: vi.fn() }));
vi.mock('./AuthContext', () => ({ useAuth: () => auth }));
vi.mock('../components/FeedbackProvider', () => ({ useFeedback: () => ({ notify: vi.fn() }) }));

function renderLayout(initialEntry = '/') {
  return render(<MemoryRouter initialEntries={[initialEntry]}><Layout /></MemoryRouter>);
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

describe('visibilidad del alcance de reparación de catálogo', () => {
  it('muestra Actividades y las tres opciones de Oficina sólo con sus permisos de sidebar', async () => {
    auth.usuario.permisos = {
      ACTIVIDADES: { read: true }, BENEFICIOS: { read: true }, PRESTAMOS: { read: true }, SEGUROS: { read: true },
    };
    renderLayout();
    await userEvent.click(screen.getByRole('button', { name: /^actividades$/i }));
    expect(screen.getByRole('link', { name: 'Tabla de actividades' })).toHaveAttribute('href', '/trabajo-social/actividades');
    expect(screen.getByRole('link', { name: 'Registrar actividad' })).toHaveAttribute('href', '/trabajo-social/actividades/registrar');
    await userEvent.click(screen.getByRole('button', { name: /^oficina$/i }));
    expect(screen.getByRole('link', { name: 'Beneficios' })).toHaveAttribute('href', '/trabajo-social/oficina/beneficios');
    expect(screen.getByRole('link', { name: 'Préstamos' })).toHaveAttribute('href', '/trabajo-social/oficina/prestamos');
    expect(screen.getByRole('link', { name: 'Seguro' })).toHaveAttribute('href', '/trabajo-social/oficina/seguro');
  });
});

describe('expansión controlada del sidebar', () => {
  beforeEach(() => {
    auth.usuario.permisos = {
      ADMINISTRACION: { read: true }, ATENCIONES: { read: true }, RECORRIDOS: { read: true },
      RIESGOS_TRABAJO: { read: true }, AUSENTISMO: { read: true }, ACCIDENTES: { read: true }, FORMULARIOS: { read: true },
    };
  });

  it('abre Administración al entrar, permite contraerla y volver a expandirla', async () => {
    const user = userEvent.setup();
    renderLayout('/admin/usuarios');
    const admin = await screen.findByRole('button', { name: /^administración$/i });
    expect(admin).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByRole('link', { name: 'Usuarios' })).toBeInTheDocument();

    await user.click(admin);
    expect(admin).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByRole('link', { name: 'Usuarios' })).not.toBeInTheDocument();

    await user.click(admin);
    expect(admin).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByRole('link', { name: 'Usuarios' })).toBeInTheDocument();
  });

  it('abre los ancestros de la nueva ruta, incluyendo Producción y Departamento Médico', async () => {
    const user = userEvent.setup();
    render(<MemoryRouter initialEntries={['/admin/usuarios']}><Link to="/trabajo-social/produccion/atenciones">Ir a Producción</Link><Layout /></MemoryRouter>);
    const production = await screen.findByRole('button', { name: /^producción$/i });
    expect(production).toHaveAttribute('aria-expanded', 'false');

    await user.click(screen.getByRole('link', { name: 'Ir a Producción' }));
    expect(await screen.findByRole('link', { name: 'Atenciones' })).toHaveAttribute('href', '/trabajo-social/produccion/atenciones');
    expect(production).toHaveAttribute('aria-expanded', 'true');

    renderLayout('/trabajo-social/departamento-medico/riesgos');
    const medical = (await screen.findAllByRole('button', { name: /^departamento médico$/i })).at(-1)!;
    expect(medical).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getAllByRole('link', { name: 'Riesgos de trabajo' }).at(-1)).toBeInTheDocument();
  });
});
