import { useAuth } from '../../app/AuthContext';

export function DashboardPage() {
  const { usuario } = useAuth();

  return (
    <section className="panel">
      <span className="panel-icon" aria-hidden="true">TS</span>
      <h2>Hola, {usuario?.nombre}</h2>
      <p>Rol: {usuario?.rol_nombre}</p>
      <p className="footnote">
        Use el menú superior para gestionar Casos, construir Formularios o buscar registros.
      </p>
    </section>
  );
}
