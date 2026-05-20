import axios from 'axios';
import { tokenUtils } from '../utils/token';

const API_ROOT = import.meta.env.VITE_API_URL || 'http://localhost:5000';
const API_BASE_URL = `${API_ROOT.replace(/\/$/, '')}/api/v1/broker/angelone`;

export const angelClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

angelClient.interceptors.request.use(
  (config) => {
    const token = tokenUtils.getJwtToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

angelClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const refreshToken = tokenUtils.getRefreshToken();
        if (refreshToken) {
          const response = await axios.post(`${API_BASE_URL}/refresh`, {
            refresh_token: refreshToken,
          });
          
          const { jwt_token } = response.data.data;
          tokenUtils.setJwtToken(jwt_token);
          
          originalRequest.headers.Authorization = `Bearer ${jwt_token}`;
          return angelClient(originalRequest);
        }
      } catch (refreshError) {
        tokenUtils.clearTokens();
        window.location.href = '/settings';
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);
