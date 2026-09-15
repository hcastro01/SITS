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
import { StructureBasePage } from '../components/StructureBasePage';
import { ActividadesPage } from '../features/actividades/ActividadesPage';
import { AusentismosPage } from '../features/ausentismos/AusentismosPage';
import { AccidentesPage } from '../features/accidentes/AccidentesPage';

const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    element: <RequireAuth />,
    children: [{
      element: <Layout />,
      children: [
        { index: true, element: <DashboardPage /> },
        { path: 'trabajo-social/inicio', element: <DashboardPage /> },
        { path: 'trabajo-social/actividades', element: <ActividadesPage /> },
        { path: 'trabajo-social/actividades/registrar', element: <ActividadesPage register /> },
        { path: 'trabajo-social/actividades/formularios', element: <FormulariosAdminPage /> },
        { path: 'trabajo-social/departamento-medico/riesgos', element: <StructureBasePage title="Riesgos de trabajo" /> },
        { path: 'trabajo-social/departamento-medico/ausentismos', element: <AusentismosPage /> },
        { path: 'trabajo-social/departamento-medico/accidentes', element: <AccidentesPage /> },
        { path: 'trabajo-social/departamento-medico/formularios', element: <FormulariosAdminPage /> },
        { path: 'casos', element: <CasosListPage /> },
        { path: 'casos/:id', element: <CasoDetailProductionPage /> },
        { path: 'atenciones', element: <EntityListPage config={atencionesConfig} /> },
        { path: 'trabajo-social/produccion/atenciones', element: <EntityListPage config={atencionesConfig} /> },
        { path: 'atenciones/:id', element: <EntityDetailPage config={atencionesConfig} /> },
        { path: 'novedades', element: <EntityListPage config={novedadesConfig} /> },
        { path: 'trabajo-social/produccion/novedades', element: <EntityListPage config={novedadesConfig} /> },
        { path: 'trabajo-social/produccion/formularios', element: <FormulariosAdminPage /> },
        { path: 'novedades/:id', element: <EntityDetailPage config={novedadesConfig} /> },
        { path: 'recorridos', element: <EntityListPage config={recorridosConfig} /> },
        { path: 'trabajo-social/produccion/recorridos', element: <EntityListPage config={recorridosConfig} /> },
        { path: 'recorridos/:id', element: <EntityDetailPage config={recorridosConfig} /> },
        { path: 'trabajo-social/oficina/beneficios', element: <StructureBasePage title="Beneficios" /> },
        { path: 'trabajo-social/oficina/atenciones', element: <StructureBasePage title="Atenciones de Oficina" /> },
        { path: 'trabajo-social/oficina/prestamos', element: <StructureBasePage title="Préstamos" /> },
        { path: 'trabajo-social/oficina/seguro', element: <StructureBasePage title="Seguro" /> },
        { path: 'trabajo-social/oficina/formularios', element: <FormulariosAdminPage /> },
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
