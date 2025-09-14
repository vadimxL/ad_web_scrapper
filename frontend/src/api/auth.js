import { api } from './client';

export const getMe = async () => {
  const { data } = await api.get('/auth/me');
  return data;
};

export const login = async ({ email, password }) => {
  const { data } = await api.post('/auth/login', { email, password });
  return data;
};

export const register = async ({ email, password }) => {
  const { data } = await api.post('/auth/register', { email, password });
  return data;
};

export const logout = async () => {
  const { data } = await api.post('/auth/logout');
  return data;
};
