import { useState, type FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../app/AuthContext';
import { HttpError } from '../../api/client';
import { SongaBrand, songaLogo } from '../../components/SongaBrand';

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
    <div className="page login-page">
      <header>
        <a href="/" className="brand">
          <SongaBrand compact />
        </a>
        <span className="environment">Acceso institucional</span>
      </header>
      <main className="login-main">
        <section className="login-brand-panel" aria-labelledby="system-title">
          <img src={songaLogo} alt="SONGA" className="login-hero-logo" />
          <p className="login-overline">Talento Humano · Trabajo Social</p>
          <h1 id="system-title">Sistema Integral de Gestión</h1>
          <p>Información social organizada, segura y trazable para acompañar a nuestra gente.</p>
        </section>
        <section className="panel login-panel" aria-labelledby="login-title">
          <p className="login-card-kicker">Acceso seguro</p>
          <h2 id="login-title">Iniciar sesión</h2>
          <p>Ingrese con las credenciales asignadas por la administración del sistema.</p>
          <form className="login-form" onSubmit={handleSubmit}>
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
        <span>SONGA · Sistema Integral de Gestión de Trabajo Social</span><span>Gestión segura y trazable</span>
      </footer>
    </div>
  );
}
