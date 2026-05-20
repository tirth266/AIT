import { useCallback, useEffect } from 'react';
import { useAngelAuthStore } from '../store/angelAuth.store';
import { angelAuthService } from '../services/angelAuth.service';
import { AngelCredentials, AngelUserProfile } from '../types';
import { BrokerError } from '../utils/errors';

export const useAngelLogin = () => {
  const { isAuthenticated, profile, isLoading, error, setLoading, setError, logout } = useAngelAuthStore();

  const setAuthenticated = (value: boolean) => {
    useAngelAuthStore.setState({ isAuthenticated: value });
  };

  const setProfile = (userProfile: AngelUserProfile | null) => {
    useAngelAuthStore.setState({ profile: userProfile });
  };

  const login = useCallback(async (credentials: AngelCredentials) => {
    setLoading(true);
    setError(null);
    try {
      const response = await angelAuthService.login(credentials);
      if (response.data.status) {
        setAuthenticated(true);
        await fetchProfile();
      } else {
        setError(response.data.message || 'Login failed');
      }
    } catch (err: any) {
      setError(err instanceof BrokerError ? err.message : 'An unexpected error occurred during login');
      setAuthenticated(false);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchProfile = useCallback(async () => {
    try {
      const userProfile = await angelAuthService.getProfile();
      if (userProfile) {
        setProfile(userProfile);
      }
    } catch (err) {
      console.error('Failed to fetch profile', err);
    }
  }, []);

  const handleLogout = useCallback(async () => {
    await angelAuthService.logout();
    logout();
  }, []);

  // Optionally fetch profile on mount if already authenticated
  useEffect(() => {
    if (isAuthenticated && !profile) {
      fetchProfile();
    }
  }, [isAuthenticated, profile, fetchProfile]);

  return {
    isAuthenticated,
    profile,
    isLoading,
    error,
    login,
    logout: handleLogout,
    fetchProfile
  };
};
