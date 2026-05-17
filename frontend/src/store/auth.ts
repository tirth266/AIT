import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { authApi } from '../services/api'
import authManager from '../auth/auth.manager'
import sessionManager from '../auth/session.manager'
import type { User, LoginCredentials, RegisterCredentials, AuthStore } from '../auth/auth.types'

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      authError: null,
      sessionExpiry: null,
      lastActivity: Date.now(),
      mode: 'paper',

      login: async (credentials: LoginCredentials) => {
        set({ isLoading: true, authError: null })
        try {
          const result = await authManager.login(credentials)
          if (result.success && result.user) {
            const state = get()
            set({
              user: result.user,
              accessToken: sessionStorage.getItem('auth_access_token'),
              refreshToken: localStorage.getItem('auth_refresh_token'),
              isAuthenticated: true,
              isLoading: false,
              lastActivity: Date.now(),
            })
            return true
          }
          set({ isLoading: false, authError: result.error || 'Login failed' })
          return false
        } catch (error) {
          set({ isLoading: false, authError: 'An unexpected error occurred' })
          return false
        }
      },

      register: async (credentials: RegisterCredentials) => {
        set({ isLoading: true, authError: null })
        try {
          const result = await authManager.register(credentials)
          if (result.success && result.user) {
            set({
              user: result.user,
              accessToken: sessionStorage.getItem('auth_access_token'),
              refreshToken: localStorage.getItem('auth_refresh_token'),
              isAuthenticated: true,
              isLoading: false,
              lastActivity: Date.now(),
            })
            return true
          }
          set({ isLoading: false, authError: result.error || 'Registration failed' })
          return false
        } catch (error) {
          set({ isLoading: false, authError: 'An unexpected error occurred' })
          return false
        }
      },

      logout: async () => {
        set({ isLoading: true })
        try {
          await authManager.logout()
        } finally {
          set({
            user: null,
            accessToken: null,
            refreshToken: null,
            isAuthenticated: false,
            isLoading: false,
            authError: null,
            sessionExpiry: null,
          })
        }
      },

      refreshSession: async () => {
        const success = await authManager.refreshAccessToken()
        if (success) {
          set({ lastActivity: Date.now() })
        }
        return success
      },

      verifyToken: async () => {
        const token = get().accessToken
        if (!token) return false

        try {
          const response = await authApi.verify()
          if (response.data?.valid) {
            if (response.data?.user) {
              set({ user: response.data.user })
            }
            set({ lastActivity: Date.now() })
            return true
          }
          return false
        } catch {
          const refreshed = await get().refreshSession()
          return refreshed
        }
      },

      setUser: (user: User) => set({ user }),

      setToken: (accessToken: string, refreshToken?: string) => {
        set({ accessToken, isAuthenticated: true })
        if (refreshToken) {
          set({ refreshToken })
        }
      },

      setMode: (mode: 'paper' | 'live') => set({ mode }),

      updateLastActivity: () => {
        sessionManager.updateActivity()
        set({ lastActivity: Date.now() })
      },

      checkSessionExpiry: () => {
        const isExpired = sessionManager.checkSessionTimeout()
        if (isExpired && get().isAuthenticated) {
          get().logout()
          return true
        }
        return false
      },

      clearAuthError: () => set({ authError: null }),

      initializeAuth: async () => {
        if (!authManager.isAuthenticated()) {
          const refreshed = await get().refreshSession()
          if (!refreshed) {
            set({ isAuthenticated: false })
            return
          }
        }

        const isValid = await get().verifyToken()
        if (!isValid) {
          await get().logout()
        } else {
          set({ isAuthenticated: true })
        }
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => sessionStorage),
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
        mode: state.mode,
        lastActivity: state.lastActivity,
        token: state.accessToken,
      }),
    }
  )
)

useAuthStore.prototype

export const selectUser = (state: AuthStore) => state.user
export const selectIsAuthenticated = (state: AuthStore) => state.isAuthenticated
export const selectIsLoading = (state: AuthStore) => state.isLoading
export const selectAuthError = (state: AuthStore) => state.authError
export const selectUserRole = (state: AuthStore) => state.user?.role
export const selectMode = (state: AuthStore) => state.mode

export default useAuthStore