import { useEffect, useState } from 'react';
import { checkService } from '../api/client';

export function App() {
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 8000);
    let active = true;
    setStatus('loading');
    checkService(controller.signal)
      .then(() => { if (active) setStatus('ready'); })
      .catch(() => { if (active) setStatus('error'); })
      .finally(() => window.clearTimeout(timeout));
    return () => { active = false; controller.abort(); window.clearTimeout(timeout); };
  }, [attempt]);

  return <div className="page">
    <header><a href="/" className="brand"><span className="mark" aria-hidden="true">TS</span><span>Trabajo Social<small>Sistema integral de gestión</small></span></a><span className="environment">Entorno de migración</span></header>
    <main>
      <section className="intro"><p className="eyebrow">GESTIÓN Y ACOMPAÑAMIENTO</p><h1>Un espacio para<br />cuidar cada proceso.</h1><p className="description">Personas, atención y seguimiento social en un mismo lugar.</p><div className="line" /><p className="footnote">La nueva plataforma se está preparando para conservar los registros, roles y permisos de la aplicación actual.</p></section>
      <section className="panel" aria-labelledby="panel-title"><span className="panel-icon" aria-hidden="true">TS</span><h2 id="panel-title">Preparación de la plataforma</h2><p>La conexión con el servicio está lista para su verificación. El acceso de usuarios se habilitará en la siguiente etapa.</p>
        <div className={`status ${status}`} role="status" aria-live="polite"><span className="dot" /><span>{status === 'loading' ? 'Comprobando conexión…' : status === 'ready' ? 'Conexión disponible' : 'No se pudo conectar'}</span></div>
        <button onClick={() => setAttempt(value => value + 1)} disabled={status === 'loading'}>{status === 'loading' ? 'Comprobando…' : 'Volver a comprobar'}</button>
        <div className="access-note"><strong>Acceso administrado</strong><p>Los usuarios se darán de alta únicamente desde la administración de la aplicación, con sus roles y permisos autorizados.</p></div>
      </section>
    </main>
    <footer>Sistema Integral de Gestión de Trabajo Social<span>Inicio de la migración</span></footer>
  </div>;
}

