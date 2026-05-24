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
const getStoredToken = (): string | null => {
  try {
    const token = localStorage.getItem('access_token');
    if (token && token.startsWith('eyJ')) {
      return token.replace(/^Bearer\s+/i, '').trim();
    }
  } catch (e) {
    console.error('[API] Token error:', e);
  }
  return null;
};

// Request interceptor for JWT authentication
apiClient.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    const authHeader = `Bearer ${token}`;
    console.log('[AXIOS] Token first 50 chars:', token.substring(0, 50));
    console.log('[AXIOS] Auth header:', authHeader.substring(0, 60));
    config.headers.Authorization = authHeader;
  } else {
    console.warn('[AXIOS] NO TOKEN - request will likely fail with 401/422');
  }
  return config;
});

// Response interceptor for handling auth failures and errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle unauthorized or invalid token errors by clearing session
    if (error.response?.status === 422 || error.response?.status === 401) {
      const errorData = error.response?.data;
      const isAuthError = errorData?.error === 'invalid_token' 
                       || errorData?.error === 'unauthorized'
                       || errorData?.type === 'Unauthorized'
                       || error.response?.status === 401;

      // Only clear session for true auth failures, not all 422s
      if (isAuthError && window.location.pathname !== '/login') {
        console.warn(`[API] Auth error (${error.response?.status}) - clearing session and redirecting`);
        localStorage.removeItem('access_token');
        localStorage.removeItem('broker_token');
        localStorage.removeItem('angel-one-auth-storage');
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
