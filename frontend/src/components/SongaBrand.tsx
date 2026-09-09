import songaLogo from '../assets/songa-logo.jpg';

export function SongaBrand({ compact = false, inverse = false }: { compact?: boolean; inverse?: boolean }) {
  return (
    <span className={`songa-brand${compact ? ' songa-brand--compact' : ''}${inverse ? ' songa-brand--inverse' : ''}`}>
      <span className="songa-logo-frame">
        <img src={songaLogo} alt="SONGA" className="songa-logo" />
      </span>
      <span className="songa-brand-copy">
        <strong>Trabajo Social</strong>
        <small>Sistema Integral de Gestión</small>
      </span>
    </span>
  );
}

export { songaLogo };
