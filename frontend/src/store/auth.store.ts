import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { AuthState } from '../types/auth.types';

interface AuthStore extends AuthState {
  setAuth: (data: { jwtToken: string; feedToken: string; clientCode: string }) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      isAuthenticated: false,
      jwtToken: null,
      feedToken: null,
      clientCode: null,
      setAuth: (data) =>
        set({
          isAuthenticated: true,
          jwtToken: data.jwtToken,
          feedToken: data.feedToken,
          clientCode: data.clientCode,
        }),
      clearAuth: () =>
        set({
          isAuthenticated: false,
          jwtToken: null,
          feedToken: null,
          clientCode: null,
        }),
    }),
    {
      name: 'angel-one-auth-storage',
    }
  )
);
