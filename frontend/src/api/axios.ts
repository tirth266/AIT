import axios from 'axios';
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

// Helper to get token directly from localStorage to avoid circular store imports
const getStoredToken = () => {
  try {
    const authData = localStorage.getItem('angel-one-auth-storage');
    if (authData) {
      const parsed = JSON.parse(authData);
      return parsed?.state?.jwtToken || parsed?.state?.accessToken || parsed?.state?.token;
    }
  } catch (e) {
    console.error('[API] Failed to parse auth storage:', e);
  }
  return null;
};

// Request interceptor for JWT authentication
apiClient.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor for handling auth failures and errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle unauthorized or invalid token errors by clearing session
    if (error.response?.status === 401 || error.response?.status === 422) {
      console.warn(`[API] ${error.response?.status} error - clearing session and redirecting`);
      
      // Clear storage directly to avoid dependency on store
      localStorage.removeItem('angel-one-auth-storage');
      localStorage.removeItem('access_token');
      
      // Redirect to login if not already there
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    
    // Provide cleaner error feedback
    if (!error.response) {
      console.error('[API] Network Error - possible CORS issue or server down');
    }
    
    return Promise.reject(error);
  }
);
