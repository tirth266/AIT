import { authApi } from '../api';
import { tokenUtils } from '../utils/token';
import { AngelAuthRequest, AngelUserProfile } from '../types';

export const angelAuthService = {
  login: async (credentials: AngelAuthRequest) => {
    const response = await authApi.login(credentials);
    if (response.status && response.data) {
      tokenUtils.setTokens({
        jwtToken: response.data.jwtToken,
        refreshToken: response.data.refreshToken,
        feedToken: response.data.feedToken,
        isAuthenticated: true,
      });
    }
    return response;
  },

  logout: async () => {
    await authApi.logout();
    tokenUtils.clearTokens();
  },

  getProfile: async (): Promise<AngelUserProfile | null> => {
    try {
      const response = await authApi.getProfile();
      return response.status ? response.data : null;
    } catch {
      return null;
    }
  },
  
  isAuthenticated: () => {
    return !!tokenUtils.getJwtToken();
  }
};
