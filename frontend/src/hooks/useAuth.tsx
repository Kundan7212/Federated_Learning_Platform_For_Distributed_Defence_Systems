import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { authApi } from '../api/client';
import type { User } from '../types';

interface AuthState {
  user:     User | null;
  token:    string | null;
  loading:  boolean;
}

interface AuthContextType extends AuthState {
  login:    (email: string, password: string) => Promise<void>;
  demoLogin: () => Promise<void>;
  register: (email: string, username: string, password: string) => Promise<void>;
  logout:   () => void;
  isAuth:   boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user:    null,
    token:   null,
    loading: true,
  });

  useEffect(() => {
    const token = localStorage.getItem('token');
    const raw   = localStorage.getItem('user');
    if (token && raw) {
      try {
        const user = JSON.parse(raw) as User;
        setState({ user, token, loading: false });
      } catch {
        localStorage.clear();
        setState({ user: null, token: null, loading: false });
      }
    } else {
      setState(s => ({ ...s, loading: false }));
    }
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { data } = await authApi.login(email, password);
    const user: User = {
      id:        data.user_id,
      email:     data.email,
      username:  data.username,
      is_active: true,
      is_admin:  false,
    };
    localStorage.setItem('token', data.access_token);
    localStorage.setItem('user', JSON.stringify(user));
    setState({ user, token: data.access_token, loading: false });
  }, []);

  const demoLogin = useCallback(async () => {
    const { data } = await authApi.demo();
    const user: User = {
      id:        data.user_id,
      email:     data.email,
      username:  data.username,
      is_active: true,
      is_admin:  false,
    };
    localStorage.setItem('token', data.access_token);
    localStorage.setItem('user', JSON.stringify(user));
    setState({ user, token: data.access_token, loading: false });
  }, []);

  const register = useCallback(async (email: string, username: string, password: string) => {
    const { data } = await authApi.register(email, username, password);
    const user: User = {
      id:        data.user_id,
      email:     data.email,
      username:  data.username,
      is_active: true,
      is_admin:  false,
    };
    localStorage.setItem('token', data.access_token);
    localStorage.setItem('user', JSON.stringify(user));
    setState({ user, token: data.access_token, loading: false });
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setState({ user: null, token: null, loading: false });
    window.location.href = '/login';
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, demoLogin, register, logout, isAuth: !!state.token }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
