const ACCESS_TOKEN_KEY = 'auth_access_token'
const REFRESH_TOKEN_KEY = 'auth_refresh_token'
const TOKEN_EXPIRY_KEY = 'auth_token_expiry'

export const tokenManager = {
  setAccessToken(token: string, expiresIn: number = 3600): void {
    const expiry = Date.now() + expiresIn * 1000
    sessionStorage.setItem(ACCESS_TOKEN_KEY, token)
    sessionStorage.setItem(TOKEN_EXPIRY_KEY, expiry.toString())
  },

  getAccessToken(): string | null {
    return sessionStorage.getItem(ACCESS_TOKEN_KEY)
  },

  setRefreshToken(token: string): void {
    localStorage.setItem(REFRESH_TOKEN_KEY, token)
  },

  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_KEY)
  },

  clearTokens(): void {
    sessionStorage.removeItem(ACCESS_TOKEN_KEY)
    sessionStorage.removeItem(TOKEN_EXPIRY_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
  },

  isTokenExpired(): boolean {
    const expiry = sessionStorage.getItem(TOKEN_EXPIRY_KEY)
    if (!expiry) return true
    return Date.now() > parseInt(expiry, 10)
  },

  getTimeUntilExpiry(): number {
    const expiry = sessionStorage.getItem(TOKEN_EXPIRY_KEY)
    if (!expiry) return 0
    const remaining = parseInt(expiry, 10) - Date.now()
    return Math.max(0, remaining)
  },

  shouldRefreshToken(): boolean {
    const remaining = tokenManager.getTimeUntilExpiry()
    return remaining > 0 && remaining < 5 * 60 * 1000
  }
}

export default tokenManager