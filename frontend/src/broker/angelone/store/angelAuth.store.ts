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

      // The backend returns access_token (platform) and broker_token (Angel One) at the top level
      const { 
        broker_token, 
        refresh_token, 
        feed_token, 
        access_token,
        client_code 
      } = response.data;

      // Crucial: Save the platform access token (Flask-JWT-Extended) immediately for application API calls
      if (access_token) {
        // Ensure we save clean token without Bearer prefix
        const cleanToken = access_token.replace(/^Bearer\s+/i, '').trim();
        console.log('[AUTH] Saved clean Platform JWT:', cleanToken.substring(0, 30));
        localStorage.setItem('platform_jwt', cleanToken);
      } else {
        console.warn('[AUTH] No access_token received from backend!');
      }

      // Small delay to ensure localStorage is committed before dashboard fetches
      await new Promise(resolve => setTimeout(resolve, 100));

      // Save broker-specific tokens using tokenUtils
      // Note: tokenUtils.setJwtToken now uses 'broker_token' key
      tokenUtils.setJwtToken(broker_token);
      tokenUtils.setRefreshToken(refresh_token);
      tokenUtils.setFeedToken(feed_token);

      // Also save broker_token explicitly to match user requirement
      if (broker_token) {
        localStorage.setItem('broker_token', broker_token);
      }

      // Update the general auth store for global axios interceptors
      useAuthStore.getState().setAuth({
        jwtToken: access_token, // Strictly use platform token (HS256)
        feedToken: feed_token,
        clientCode: client_code || credentials.client_code
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
