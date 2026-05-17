export type UserRole = 'trader' | 'admin' | 'analyst'

export interface User {
  id: string
  email: string
  full_name: string
  phone?: string
  role: UserRole
  twofa_enabled?: boolean
  broker?: string
  created_at?: string
  last_login?: string
}

export interface AuthTokens {
  accessToken: string
  refreshToken: string
  expiresIn: number
  tokenType: string
}

export interface LoginCredentials {
  email: string
  password: string
  rememberMe?: boolean
}

export interface RegisterCredentials {
  full_name: string
  email: string
  phone: string
  password: string
  confirm_password?: string
  pan_number?: string
  broker?: string
}

export interface AuthResponse {
  data: {
    access_token: string
    refresh_token: string
    token_type: string
    expires_in: number
    user: User
  }
  message?: string
}

export interface RefreshResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export interface SessionInfo {
  sessionId: string
  device: string
  ip: string
  lastActive: string
  createdAt: string
}

export interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  authError: string | null
  sessionExpiry: number | null
  lastActivity: number
  mode: 'paper' | 'live'
}

export interface AuthActions {
  login: (credentials: LoginCredentials) => Promise<boolean>
  register: (credentials: RegisterCredentials) => Promise<boolean>
  logout: () => Promise<void>
  refreshSession: () => Promise<boolean>
  verifyToken: () => Promise<boolean>
  setUser: (user: User) => void
  setToken: (accessToken: string, refreshToken?: string) => void
  setMode: (mode: 'paper' | 'live') => void
  updateLastActivity: () => void
  checkSessionExpiry: () => boolean
  clearAuthError: () => void
  initializeAuth: () => Promise<void>
}

export type AuthStore = AuthState & AuthActions

export interface Permission {
  resource: string
  actions: string[]
}

export const RolePermissions: Record<UserRole, Permission[]> = {
  admin: [
    { resource: '*', actions: ['*'] }
  ],
  trader: [
    { resource: 'dashboard', actions: ['read'] },
    { resource: 'orders', actions: ['read', 'create', 'cancel'] },
    { resource: 'positions', actions: ['read'] },
    { resource: 'strategies', actions: ['read', 'create', 'update', 'delete', 'start', 'stop'] },
    { resource: 'watchlist', actions: ['read', 'create', 'update', 'delete'] },
    { resource: 'funds', actions: ['read', 'deposit', 'withdraw'] },
    { resource: 'settings', actions: ['read', 'update'] },
  ],
  analyst: [
    { resource: 'dashboard', actions: ['read'] },
    { resource: 'signals', actions: ['read', 'create'] },
    { resource: 'strategies', actions: ['read'] },
    { resource: 'reports', actions: ['read'] },
  ]
}

export function hasPermission(role: UserRole, resource: string, action: string): boolean {
  const permissions = RolePermissions[role]
  return permissions.some(p => {
    if (p.resource === '*') return true
    if (p.resource === resource) {
      return p.actions.includes('*') || p.actions.includes(action)
    }
    return false
  })
}