import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './AuthContext';
import { RequireAuth } from './RequireAuth';
import { Layout } from './Layout';
import { LoginPage } from '../features/auth/LoginPage';
import { DashboardPage } from '../features/dashboard/DashboardPage';
import { CasosListPage } from '../features/casos/CasosListPage';
import { CasoFormPage } from '../features/casos/CasoFormPage';
import { CasoDetailPage } from '../features/casos/CasoDetailPage';
import { FormulariosListPage } from '../features/formularios/FormulariosListPage';
import { FormularioDetailPage } from '../features/formularios/FormularioDetailPage';
import { BusquedaPage } from '../features/busqueda/BusquedaPage';

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
              <Route path="/casos/nuevo" element={<CasoFormPage />} />
              <Route path="/casos/:id" element={<CasoDetailPage />} />
              <Route path="/formularios" element={<FormulariosListPage />} />
              <Route path="/formularios/:id" element={<FormularioDetailPage />} />
              <Route path="/busqueda" element={<BusquedaPage />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
