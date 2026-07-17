import axios from 'axios';
import type {
  TokenResponse, User, Experiment, ExperimentDetail,
  CreateExperimentRequest, TrainingStatus, DashboardStats, AlgorithmMeta,
} from '../types';

const BASE_URL = '/api/v1';

const api = axios.create({ baseURL: BASE_URL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  },
);

export const authApi = {
  register: (email: string, username: string, password: string) =>
    api.post<TokenResponse>('/auth/register', { email, username, password }),

  login: (email: string, password: string) =>
    api.post<TokenResponse>('/auth/login', { email, password }),

  demo: () => api.post<TokenResponse>('/auth/demo'),

  me: () => api.get<User>('/auth/me'),
};

export const experimentsApi = {
  list: (skip = 0, limit = 50) =>
    api.get<Experiment[]>('/experiments', { params: { skip, limit } }),

  get: (id: string) =>
    api.get<ExperimentDetail>(`/experiments/${id}`),

  create: (data: CreateExperimentRequest) =>
    api.post<Experiment>('/experiments', data),

  delete: (id: string) =>
    api.delete(`/experiments/${id}`),
};

export const trainingApi = {
  start: (id: string) =>
    api.post<{ message: string; experiment_id: string }>(`/training/${id}/start`),

  cancel: (id: string) =>
    api.post<{ message: string }>(`/training/${id}/cancel`),

  status: (id: string) =>
    api.get<TrainingStatus>(`/training/${id}/status`),
};

export const privacyApi = {
  budget: (id: string) =>
    api.get(`/privacy/experiments/${id}/budget`),

  overview: () =>
    api.get(`/privacy/overview`),

  algorithms: () =>
    api.get(`/privacy/algorithms`),
};

export const metricsApi = {
  dashboard: () =>
    api.get<DashboardStats>('/metrics/dashboard'),

  algorithms: () =>
    api.get<AlgorithmMeta[]>('/metrics/algorithms'),
};

export const getWsUrl = (experimentId: string): string => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host     = window.location.host;
  return `${protocol}//${host}/api/v1/training/ws/${experimentId}`;
};

export default api;
