import { create } from 'zustand';
import { tokenUtils } from '../utils/token';
import { AngelUserProfile, AngelCredentials } from '../types';
import { authApi } from '../api';

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
    set({ isLoading: true, error: null });
    try {
      const response = await authApi.login(credentials);
      const { jwt_token, refresh_token, feed_token } = response.data.data;
      
      tokenUtils.setJwtToken(jwt_token);
      tokenUtils.setRefreshToken(refresh_token);
      tokenUtils.setFeedToken(feed_token);
      
      set({ isAuthenticated: true, isLoading: false });
    } catch (error: any) {
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
