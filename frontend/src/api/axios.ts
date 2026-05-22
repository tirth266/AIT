import axios from 'axios';
import { useAuthStore } from '../store/auth.store';

/**
 * Production-safe Axios instance for REST API communication.
 * Configured with proper CORS credentials and base URL.
 */
const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  "http://localhost:5000";

const API_URL = `${API_BASE_URL.replace(/\/$/, '')}/api/v1`;

export const apiClient = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for JWT authentication
apiClient.interceptors.request.use((config) => {
  const { jwtToken } = useAuthStore.getState();
  if (jwtToken) {
    config.headers.Authorization = `Bearer ${jwtToken}`;
  }
  return config;
});

// Response interceptor for handling auth failures and errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle unauthorized errors by clearing session
    if (error.response?.status === 401) {
      console.warn('[API] 401 Unauthorized - clearing session');
      useAuthStore.getState().clearAuth();
    }
    
    // Provide cleaner error feedback
    if (!error.response) {
      console.error('[API] Network Error - possible CORS issue or server down');
    }
    
    return Promise.reject(error);
  }
);
