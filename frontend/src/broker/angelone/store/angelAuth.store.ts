import { create } from 'zustand';
import { tokenUtils } from '../utils/token';
import { AngelUserProfile, AngelCredentials } from '../types';
import { authApi } from '../api';
import { useAuthStore } from '../../../store/auth.store';

interface AngelAuthState {
  isAuthenticated: boolean;
  profile: AngelUserProfile | null;
  isLoading: boolean;
  error: string | null;
  
  login: (credentials: AngelCredentials) => Promise<void>;
  logout: () => void;
  fetchProfile: () => Promise<void>;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useAngelAuthStore = create<AngelAuthState>((set) => ({
  isAuthenticated: !!tokenUtils.getJwtToken(),
  profile: null,
  isLoading: false,
  error: null,

  login: async (credentials) => {
    console.log('[AngelAuthStore] Starting login...');
    set({ isLoading: true, error: null });
    try {
      const response = await authApi.login(credentials);
      console.log('[AngelAuthStore] Login response received');
      
      // The backend returns access_token (platform) and broker_token (Angel One)
      const { broker_token, refresh_token, feed_token, access_token } = response.data;
      
      // If the backend nested them under 'data' (legacy support)
      const jwtToken = access_token || response.data.data?.access_token;
      const angelToken = broker_token || response.data.data?.jwt_token;
      const refreshToken = refresh_token || response.data.data?.refresh_token;
      const feedToken = feed_token || response.data.data?.feed_token;

      tokenUtils.setJwtToken(angelToken);
      tokenUtils.setRefreshToken(refreshToken);
      tokenUtils.setFeedToken(feedToken);
      
      // Crucial: Save the platform access token (Flask-JWT-Extended) for application API calls
      if (jwtToken) {
        console.log('[AUTH] Saving access_token:', jwtToken.substring(0, 50));
        localStorage.setItem('access_token', jwtToken);
      } else {
        console.warn('[AUTH] No access_token received from backend!');
      }
      
      // Also update the general auth store for axios interceptors
      useAuthStore.getState().setAuth({
        jwtToken: jwtToken || angelToken, // Prefer platform token if available
        feedToken: feedToken,
        clientCode: credentials.client_code
      });
      
      set({ isAuthenticated: true, isLoading: false });
      console.log('[AngelAuthStore] Login successful and stores updated');
    } catch (error: any) {
      console.error('[AngelAuthStore] Login failed:', error);
      set({ 
        error: error.response?.data?.message || 'Login failed', 
        isLoading: false,
        isAuthenticated: false 
      });
    }
  },

  fetchProfile: async () => {
    try {
      const response = await authApi.getProfile();
      set({ profile: response.data.data });
    } catch (error) {
      console.error('Failed to fetch Angel One profile', error);
    }
  },

  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  
  logout: () => {
    tokenUtils.clearTokens();
    set({ isAuthenticated: false, profile: null, error: null });
  }
}));
