import axios from 'axios';
import { useAuthStore } from '../store/auth.store';

const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  "http://localhost:5000";
const API_URL = `${API_BASE_URL.replace(/\/$/, '')}/api/v1`;

export const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

apiClient.interceptors.request.use((config) => {
  const { jwtToken } = useAuthStore.getState();
  if (jwtToken) {
    config.headers.Authorization = `Bearer ${jwtToken}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().clearAuth();
    }
    return Promise.reject(error);
  }
);
