import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000';
axios.defaults.withCredentials = true;

export const getMe = async () => {
  const { data } = await axios.get(`${API_BASE}/auth/me`);
  return data;
};

export const login = async ({ email, password }) => {
  const { data } = await axios.post(`${API_BASE}/auth/login`, { email, password });
  return data;
};

export const register = async ({ email, password }) => {
  const { data } = await axios.post(`${API_BASE}/auth/register`, { email, password });
  return data;
};

export const logout = async () => {
  const { data } = await axios.post(`${API_BASE}/auth/logout`);
  return data;
};
