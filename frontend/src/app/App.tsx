import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './AuthContext';
import { RequireAuth } from './RequireAuth';
import { Layout } from './Layout';
import { LoginPage } from '../features/auth/LoginPage';
import { DashboardPage } from '../features/dashboard/DashboardPage';
import { CasosListPage } from '../features/casos/CasosListPage';
import { CasoDetailPage } from '../features/casos/CasoDetailPage';
import { FormulariosListPage } from '../features/formularios/FormulariosListPage';
import { FormularioDetailPage } from '../features/formularios/FormularioDetailPage';
import { ResponderFormularioPage } from '../features/formularios/ResponderFormularioPage';
import { BusquedaPage } from '../features/busqueda/BusquedaPage';
import { EntityListPage } from '../features/entities/EntityListPage';
import { EntityDetailPage } from '../features/entities/EntityDetailPage';
import { atencionesConfig, novedadesConfig, personasConfig, recorridosConfig } from '../features/entities/EntityConfig';
import { AdminUsuariosPage } from '../features/admin/AdminUsuariosPage';
import { AdminPermisosPage } from '../features/admin/AdminPermisosPage';

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<RequireAuth />}>
            <Route element={<Layout />}>
              <Route path="/" element={<DashboardPage />} />

              <Route path="/casos" element={<CasosListPage />} />
              <Route path="/casos/:id" element={<CasoDetailPage />} />

              <Route path="/atenciones" element={<EntityListPage config={atencionesConfig} />} />
              <Route path="/atenciones/:id" element={<EntityDetailPage config={atencionesConfig} />} />

              <Route path="/novedades" element={<EntityListPage config={novedadesConfig} />} />
              <Route path="/novedades/:id" element={<EntityDetailPage config={novedadesConfig} />} />

              <Route path="/recorridos" element={<EntityListPage config={recorridosConfig} />} />
              <Route path="/recorridos/:id" element={<EntityDetailPage config={recorridosConfig} />} />

              <Route path="/personas" element={<EntityListPage config={personasConfig} />} />
              <Route path="/personas/:id" element={<EntityDetailPage config={personasConfig} />} />

              <Route path="/formularios" element={<FormulariosListPage />} />
              <Route path="/formularios/:id" element={<FormularioDetailPage />} />
              <Route path="/formularios/:id/responder" element={<ResponderFormularioPage />} />

              <Route path="/busqueda" element={<BusquedaPage />} />

              <Route path="/admin/usuarios" element={<AdminUsuariosPage />} />
              <Route path="/admin/permisos" element={<AdminPermisosPage />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
