import { authApi } from '../services/api'
import tokenManager from './token.manager'
import sessionManager from './session.manager'
import type { LoginCredentials, RegisterCredentials, User } from './auth.types'

export interface AuthResult {
  success: boolean
  user?: User
  error?: string
}

export const authManager = {
  async login(credentials: LoginCredentials): Promise<AuthResult> {
    try {
      const response = await authApi.login({
        email: credentials.email,
        password: credentials.password
      })

      const { access_token, refresh_token, expires_in, token_type } = response.data.data

      tokenManager.setAccessToken(access_token, expires_in)
      if (refresh_token) {
        tokenManager.setRefreshToken(refresh_token)
      }

      if (credentials.rememberMe) {
        localStorage.setItem('remember_me', 'true')
      }

      sessionManager.updateActivity()

      return { success: true, user: response.data.data.user }
    } catch (error: unknown) {
      const err = error as { response?: { data?: { message?: string } } }
      return { success: false, error: err.response?.data?.message || 'Login failed' }
    }
  },

  async register(credentials: RegisterCredentials): Promise<AuthResult> {
    try {
      const response = await authApi.register(credentials)
      const { access_token, refresh_token, expires_in } = response.data.data

      tokenManager.setAccessToken(access_token, expires_in)
      if (refresh_token) {
        tokenManager.setRefreshToken(refresh_token)
      }

      sessionManager.updateActivity()

      return { success: true, user: response.data.data.user }
    } catch (error: unknown) {
      const err = error as { response?: { data?: { message?: string } } }
      return { success: false, error: err.response?.data?.message || 'Registration failed' }
    }
  },

  async logout(): Promise<void> {
    try {
      await authApi.logout()
    } catch {
    } finally {
      tokenManager.clearTokens()
      sessionManager.clearSession()
      localStorage.removeItem('remember_me')
    }
  },

  async refreshAccessToken(): Promise<boolean> {
    const refreshToken = tokenManager.getRefreshToken()
    if (!refreshToken) return false

    try {
      const response = await authApi.refresh(refreshToken)
      const { access_token, expires_in } = response.data

      tokenManager.setAccessToken(access_token, expires_in)
      sessionManager.updateActivity()

      return true
    } catch {
      await this.logout()
      return false
    }
  },

  async verifyToken(): Promise<boolean> {
    const accessToken = tokenManager.getAccessToken()
    if (!accessToken) return false

    if (tokenManager.isTokenExpired()) {
      return await this.refreshAccessToken()
    }

    try {
      const response = await authApi.verify()
      return response.data?.valid === true
    } catch {
      return false
    }
  },

  isAuthenticated(): boolean {
    const accessToken = tokenManager.getAccessToken()
    if (!accessToken) return false

    if (sessionManager.checkSessionTimeout()) {
      return false
    }

    return true
  },

  rememberMe(): boolean {
    return localStorage.getItem('remember_me') === 'true'
  }
}

export default authManager