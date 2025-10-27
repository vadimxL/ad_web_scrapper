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
export const fetchDeletedTasks = () => api.get('/deleted_tasks').then(r => r.data);

// Recreate a deleted task converting its params back to UITask shape
export const recreateTaskFromHistory = (deletedTask, email) => {
  const p = deletedTask.params || {};
  // Extract ranges with fallbacks
  const parseRange = (val) => {
    if (!val || typeof val !== 'string') return { start: 0, end: 0 };
    const parts = val.split('-').filter(Boolean);
    if (parts.length < 2) return { start: 0, end: 0 };
    const [start, end] = parts.map(v => parseInt(v, 10));
    return { start: start || 0, end: end || 0 };
  };
  const yearR = parseRange(p.year);
  const kmR = parseRange(p.km);
  const engineR = parseRange(p.engineval);
  const payload = {
    email,
    manufacturer: p.manufacturer || '',
    model: p.model || '',
    year_start: yearR.start,
    year_end: yearR.end,
    km_start: kmR.start,
    km_end: kmR.end,
    engine_vol_start: engineR.start,
    engine_vol_end: engineR.end,
  };
  return createTaskV2(payload);
};
