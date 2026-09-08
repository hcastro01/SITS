import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom';
import { AuthProvider } from './AuthContext';
import { RequireAuth } from './RequireAuth';
import { Layout } from './Layout';
import { FeedbackProvider } from '../components/FeedbackProvider';
import { LoginPage } from '../features/auth/LoginPage';
import { DashboardPage } from '../features/dashboard/DashboardPage';
import { CasosListPage } from '../features/casos/CasosListPage';
import { CasoDetailProductionPage } from '../features/casos/CasoDetailProductionPage';
import { FormulariosAdminPage } from '../features/formularios/FormulariosAdminPage';
import { FormBuilderPage } from '../features/formularios/FormBuilderPage';
import { DynamicResponsePage } from '../features/formularios/DynamicResponsePage';
import { BusquedaPage } from '../features/busqueda/BusquedaPage';
import { EntityListPage } from '../features/entities/EntityListPage';
import { EntityDetailPage } from '../features/entities/EntityDetailPage';
import { atencionesConfig, novedadesConfig, personasConfig, recorridosConfig } from '../features/entities/EntityConfig';
import { AdminUsuariosPage } from '../features/admin/AdminUsuariosPage';
import { AdminPermisosPage } from '../features/admin/AdminPermisosPage';

const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    element: <RequireAuth />,
    children: [{
      element: <Layout />,
      children: [
        { index: true, element: <DashboardPage /> },
        { path: 'casos', element: <CasosListPage /> },
        { path: 'casos/:id', element: <CasoDetailProductionPage /> },
        { path: 'atenciones', element: <EntityListPage config={atencionesConfig} /> },
        { path: 'atenciones/:id', element: <EntityDetailPage config={atencionesConfig} /> },
        { path: 'novedades', element: <EntityListPage config={novedadesConfig} /> },
        { path: 'novedades/:id', element: <EntityDetailPage config={novedadesConfig} /> },
        { path: 'recorridos', element: <EntityListPage config={recorridosConfig} /> },
        { path: 'recorridos/:id', element: <EntityDetailPage config={recorridosConfig} /> },
        { path: 'personas', element: <EntityListPage config={personasConfig} /> },
        { path: 'personas/:id', element: <EntityDetailPage config={personasConfig} /> },
        { path: 'formularios', element: <FormulariosAdminPage /> },
        { path: 'formularios/:id', element: <FormBuilderPage /> },
        { path: 'formularios/:id/responder', element: <DynamicResponsePage /> },
        { path: 'busqueda', element: <BusquedaPage /> },
        { path: 'admin/usuarios', element: <AdminUsuariosPage /> },
        { path: 'admin/permisos', element: <AdminPermisosPage /> },
      ],
    }],
  },
  { path: '*', element: <Navigate to="/" replace /> },
]);

export function App() {
  return (
    <AuthProvider>
      <FeedbackProvider>
        <RouterProvider router={router} />
      </FeedbackProvider>
    </AuthProvider>
  );
}
