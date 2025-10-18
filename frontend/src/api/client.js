import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE;

export const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Helper wrappers
export const fetchTasks = () => api.get('/tasks').then(r => r.data);
export const createTaskV2 = (payload) => api.post('/v2/tasks', payload).then(r => r.data);
