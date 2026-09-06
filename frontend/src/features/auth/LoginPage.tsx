import { useState, type FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../app/AuthContext';
import { HttpError } from '../../api/client';

export function LoginPage() {
  const { usuario, cargando, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [correo, setCorreo] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  if (!cargando && usuario) {
    const destino = (location.state as { from?: string } | null)?.from ?? '/';
    return <Navigate to={destino} replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      await login(correo, password);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible iniciar sesión.');
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="page">
      <header>
        <a href="/" className="brand">
          <span className="mark" aria-hidden="true">TS</span>
          <span>Trabajo Social<small>Sistema integral de gestión</small></span>
        </a>
        <span className="environment">Acceso institucional</span>
      </header>
      <main className="login-main">
        <section className="panel login-panel" aria-labelledby="login-title">
          <span className="panel-icon" aria-hidden="true">TS</span>
          <h2 id="login-title">Iniciar sesión</h2>
          <p>Ingrese con las credenciales asignadas por la administración del sistema.</p>
          <form onSubmit={handleSubmit}>
            <label htmlFor="correo">Correo electrónico</label>
            <input
              id="correo"
              name="correo"
              type="email"
              autoComplete="email"
              required
              value={correo}
              onChange={(event) => setCorreo(event.target.value)}
            />
            <label htmlFor="password">Contraseña</label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              minLength={12}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
            {error && <p className="form-error" role="alert">{error}</p>}
            <button type="submit" disabled={enviando}>{enviando ? 'Ingresando…' : 'Ingresar'}</button>
          </form>
        </section>
      </main>
      <footer>
        Sistema Integral de Gestión de Trabajo Social<span>Gestión segura y trazable</span>
      </footer>
    </div>
  );
}
