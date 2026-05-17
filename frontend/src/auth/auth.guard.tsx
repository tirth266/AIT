import { useEffect, useRef } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore, selectIsAuthenticated } from '../store/auth'
import { hasPermission, type UserRole } from '../auth/auth.types'

interface AuthGuardProps {
  children: React.ReactNode
  requiredRoles?: UserRole[]
  fallbackPath?: string
}

export function AuthGuard({
  children,
  requiredRoles,
  fallbackPath = '/login'
}: AuthGuardProps) {
  const isAuthenticated = useAuthStore(selectIsAuthenticated)
  const user = useAuthStore((state) => state.user)
  const verifyToken = useAuthStore((state) => state.verifyToken)
  const location = useLocation()
  const navigate = useNavigate()
  const initialized = useRef(false)

  useEffect(() => {
    if (!initialized.current) {
      initialized.current = true
      verifyToken()
    }
  }, [verifyToken])

  if (!isAuthenticated) {
    return (
      <Navigate
        to={fallbackPath}
        state={{ from: location.pathname, replace: true }}
        replace
      />
    )
  }

  if (requiredRoles && user?.role) {
    const hasRequiredRole = requiredRoles.includes(user.role)
    if (!hasRequiredRole) {
      return <Navigate to="/unauthorized" replace />
    }
  }

  return <>{children}</>
}

interface PermissionGuardProps {
  children: React.ReactNode
  resource: string
  action: 'read' | 'create' | 'update' | 'delete' | 'start' | 'stop' | '*'
  fallback?: React.ReactNode
}

export function PermissionGuard({
  children,
  resource,
  action,
  fallback = null
}: PermissionGuardProps) {
  const user = useAuthStore((state) => state.user)

  if (!user?.role) {
    return <>{fallback}</>
  }

  const hasAccess = hasPermission(user.role, resource, action)

  if (!hasAccess) {
    return <>{fallback}</>
  }

  return <>{children}</>
}

export default AuthGuard