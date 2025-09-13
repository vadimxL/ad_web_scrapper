import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { getMe, login as apiLogin, register as apiRegister, logout as apiLogout } from '../api/auth';

export const AuthContext = createContext({
  user: null,
  loading: true,
  error: null,
  refresh: async () => {},
  login: async (_creds) => {},
  register: async (_creds) => {},
  logout: async () => {},
});

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = async () => {
    try {
      setLoading(true);
      const me = await getMe();
      setUser(me);
      setError(null);
    } catch (e) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const login = async ({ email, password }) => {
    await apiLogin({ email, password });
    await refresh();
  };

  const register = async ({ email, password }) => {
    await apiRegister({ email, password });
    await refresh();
  };

  const logout = async () => {
    await apiLogout();
    setUser(null);
  };

  const value = useMemo(
    () => ({ user, loading, error, refresh, login, register, logout }),
    [user, loading, error]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => useContext(AuthContext);
