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
  /**
   * deletedTask.params structure example:
   * {
   *   manufacturer: '48',
   *   model: '3866,2829',
   *   year: '2019-2024',
   *   km: '0-80000',
   *   engineval: '1000-2000',
   *   seller_type: 'private'
   * }
   */
  const taskParams = deletedTask.params || {};
  // Extract ranges with fallbacks
  const parseRange = (val) => {
    if (!val || typeof val !== 'string') return { start: 0, end: 0 };
    const parts = val.split('-').filter(Boolean);
    if (parts.length < 2) return { start: 0, end: 0 };
    const [start, end] = parts.map(v => parseInt(v, 10));
    return { start: start || 0, end: end || 0 };
  };
  const yearRange = parseRange(taskParams.year);
  const mileageRange = parseRange(taskParams.km);
  const engineVolumeRange = parseRange(taskParams.engineval);
  const payload = {
    email,
    manufacturer: taskParams.manufacturer || '',
    model: taskParams.model || '',
    year_start: yearRange.start,
    year_end: yearRange.end,
    km_start: mileageRange.start,
    km_end: mileageRange.end,
    engine_vol_start: engineVolumeRange.start,
    engine_vol_end: engineVolumeRange.end,
    seller_type: taskParams.seller_type || 'all', // preserve previous seller type if present
  };
  return createTaskV2(payload);
};
