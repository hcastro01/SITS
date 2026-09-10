import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { fetchCurrentUser, login as loginRequest, logout as logoutRequest, type UsuarioActual } from '../api/auth';
import { HttpError, SESSION_EXPIRED_EVENT } from '../api/client';

interface AuthState {
  usuario: UsuarioActual | null;
  cargando: boolean;
  login: (correo: string, password?: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<UsuarioActual | null>(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    let activo = true;
    const clearExpiredSession = () => { if (activo) setUsuario(null); };
    window.addEventListener(SESSION_EXPIRED_EVENT, clearExpiredSession);
    fetchCurrentUser()
      .then((perfil) => { if (activo) setUsuario(perfil); })
      .catch((error: unknown) => {
        // 401 es el caso normal de "todavía no inició sesión"; cualquier otro error se registra.
        if (!(error instanceof HttpError && error.status === 401)) console.error(error);
      })
      .finally(() => { if (activo) setCargando(false); });
    return () => {
      activo = false;
      window.removeEventListener(SESSION_EXPIRED_EVENT, clearExpiredSession);
    };
  }, []);

  async function login(correo: string, password?: string) {
    const perfil = await loginRequest(correo, password);
    setUsuario(perfil);
  }

  async function logout() {
    await logoutRequest();
    setUsuario(null);
  }

  return <AuthContext.Provider value={{ usuario, cargando, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth debe usarse dentro de <AuthProvider>.');
  return context;
}
