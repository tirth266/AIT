import { useEffect, useCallback, useRef } from 'react'
import { useAuthStore } from '../store/auth'
import sessionManager from '../auth/session.manager'
import tokenManager from '../auth/token.manager'

interface AuthProviderProps {
  children: React.ReactNode
  sessionCheckInterval?: number
}

export function AuthProvider({
  children,
  sessionCheckInterval = 60000
}: AuthProviderProps) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const checkSessionExpiry = useAuthStore((state) => state.checkSessionExpiry)
  const refreshSession = useAuthStore((state) => state.refreshSession)
  const updateLastActivity = useAuthStore((state) => state.updateLastActivity)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    sessionManager.init()
  }, [])

  useEffect(() => {
    if (!isAuthenticated) return

    intervalRef.current = setInterval(() => {
      if (sessionManager.checkSessionTimeout()) {
        checkSessionExpiry()
      } else if (tokenManager.shouldRefreshToken()) {
        refreshSession()
      }
    }, sessionCheckInterval)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [isAuthenticated, sessionCheckInterval, checkSessionExpiry, refreshSession])

  useEffect(() => {
    if (!isAuthenticated) return

    const handleActivity = () => {
      updateLastActivity()
    }

    const events = ['mousedown', 'keydown', 'scroll', 'touchstart']
    events.forEach(event => window.addEventListener(event, handleActivity))

    return () => {
      events.forEach(event => window.removeEventListener(event, handleActivity))
    }
  }, [isAuthenticated, updateLastActivity])

  useEffect(() => {
    if (!isAuthenticated) return

    const handleBeforeUnload = () => {
      sessionManager.updateActivity()
    }

    window.addEventListener('beforeunload', handleBeforeUnload)

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload)
    }
  }, [isAuthenticated])

  const value = {
    isAuthenticated,
    updateLastActivity: useCallback(() => updateLastActivity(), [updateLastActivity]),
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

const AuthContext = createContext<{
  isAuthenticated: boolean
  updateLastActivity: () => void
} | null>(null)

export function useAuthContext() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuthContext must be used within AuthProvider')
  }
  return context
}

import { createContext, useContext } from 'react'

export default AuthProvider