import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAngelAuthStore } from '../broker/angelone/store/angelAuth.store';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const isAuthenticated = useAngelAuthStore((state) => state.isAuthenticated);
  const location = useLocation();

  if (!isAuthenticated) {
    console.log('[Auth] Not authenticated, redirecting to login from', location.pathname);
    return <Navigate to="/" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};
