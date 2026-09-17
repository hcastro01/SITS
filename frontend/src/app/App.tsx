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
import { ContextualFormsPage, CONTEXTUAL_FORM_BRANCHES } from '../features/formularios/ContextualFormsPage';
import { BusquedaPage } from '../features/busqueda/BusquedaPage';
import { EntityListPage } from '../features/entities/EntityListPage';
import { EntityDetailPage } from '../features/entities/EntityDetailPage';
import { atencionesConfig, beneficiosConfig, medicoAtencionesConfig, novedadesConfig, oficinaAtencionesConfig, personasConfig, prestamosConfig, produccionAtencionesConfig, produccionNovedadesConfig, produccionRecorridosConfig, recorridosConfig, segurosConfig } from '../features/entities/EntityConfig';
import { AdminUsuariosPage } from '../features/admin/AdminUsuariosPage';
import { AdminPermisosPage } from '../features/admin/AdminPermisosPage';
import { ActividadesPage } from '../features/actividades/ActividadesPage';
import { AusentismosPage } from '../features/ausentismos/AusentismosPage';
import { AccidentesPage } from '../features/accidentes/AccidentesPage';
import { RiesgosTrabajoPage } from '../features/riesgos/RiesgosTrabajoPage';
import { RiesgoDetailPage } from '../features/riesgos/RiesgoDetailPage';

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
        { path: 'trabajo-social/actividades/formularios', element: <ContextualFormsPage config={CONTEXTUAL_FORM_BRANCHES.activities} /> },
        { path: 'trabajo-social/departamento-medico/riesgos', element: <RiesgosTrabajoPage /> },
        { path: 'trabajo-social/departamento-medico/riesgos/:id', element: <RiesgoDetailPage /> },
        { path: 'trabajo-social/departamento-medico/ausentismos', element: <AusentismosPage /> },
        { path: 'trabajo-social/departamento-medico/accidentes', element: <AccidentesPage /> },
        { path: 'trabajo-social/departamento-medico/formularios', element: <ContextualFormsPage config={CONTEXTUAL_FORM_BRANCHES.medical} /> },
        { path: 'trabajo-social/departamento-medico/atenciones', element: <EntityListPage config={medicoAtencionesConfig} /> },
        { path: 'trabajo-social/departamento-medico/atenciones/:id', element: <EntityDetailPage config={medicoAtencionesConfig} /> },
        { path: 'casos', element: <CasosListPage /> },
        { path: 'casos/:id', element: <CasoDetailProductionPage /> },
        { path: 'atenciones', element: <EntityListPage config={atencionesConfig} /> },
        { path: 'trabajo-social/produccion/atenciones', element: <EntityListPage config={produccionAtencionesConfig} /> },
        { path: 'trabajo-social/produccion/atenciones/:id', element: <EntityDetailPage config={produccionAtencionesConfig} /> },
        { path: 'atenciones/:id', element: <EntityDetailPage config={atencionesConfig} /> },
        { path: 'novedades', element: <EntityListPage config={novedadesConfig} /> },
        { path: 'trabajo-social/produccion/novedades', element: <EntityListPage config={produccionNovedadesConfig} /> },
        { path: 'trabajo-social/produccion/novedades/:id', element: <EntityDetailPage config={produccionNovedadesConfig} /> },
        { path: 'trabajo-social/produccion/formularios', element: <ContextualFormsPage config={CONTEXTUAL_FORM_BRANCHES.production} /> },
        { path: 'novedades/:id', element: <EntityDetailPage config={novedadesConfig} /> },
        { path: 'recorridos', element: <EntityListPage config={recorridosConfig} /> },
        { path: 'trabajo-social/produccion/recorridos', element: <EntityListPage config={produccionRecorridosConfig} /> },
        { path: 'trabajo-social/produccion/recorridos/:id', element: <EntityDetailPage config={produccionRecorridosConfig} /> },
        { path: 'recorridos/:id', element: <EntityDetailPage config={recorridosConfig} /> },
        { path: 'trabajo-social/oficina/beneficios', element: <EntityListPage config={beneficiosConfig} /> },
        { path: 'trabajo-social/oficina/beneficios/:id', element: <EntityDetailPage config={beneficiosConfig} /> },
        { path: 'trabajo-social/oficina/atenciones', element: <EntityListPage config={oficinaAtencionesConfig} /> },
        { path: 'trabajo-social/oficina/atenciones/:id', element: <EntityDetailPage config={oficinaAtencionesConfig} /> },
        { path: 'trabajo-social/oficina/prestamos', element: <EntityListPage config={prestamosConfig} /> },
        { path: 'trabajo-social/oficina/prestamos/:id', element: <EntityDetailPage config={prestamosConfig} /> },
        { path: 'trabajo-social/oficina/seguro', element: <EntityListPage config={segurosConfig} /> },
        { path: 'trabajo-social/oficina/seguro/:id', element: <EntityDetailPage config={segurosConfig} /> },
        { path: 'trabajo-social/oficina/formularios', element: <ContextualFormsPage config={CONTEXTUAL_FORM_BRANCHES.office} /> },
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
