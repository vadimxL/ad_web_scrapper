import React, { createContext, useContext, useEffect, useMemo, useState, useCallback } from 'react';
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

  const refresh = useCallback(async () => {
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
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = useCallback(
    async ({ email, password }) => {
      await apiLogin({ email, password });
      await refresh();
    },
    [refresh]
  );

  const register = useCallback(
    async ({ email, password }) => {
      await apiRegister({ email, password });
      await refresh();
    },
    [refresh]
  );

  const logout = useCallback(async () => {
    await apiLogout();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, error, refresh, login, register, logout }),
    [user, loading, error, refresh, login, register, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => useContext(AuthContext);
