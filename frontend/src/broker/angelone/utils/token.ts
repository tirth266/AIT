const ANGEL_JWT_KEY = 'angel_jwt_token';
const ANGEL_REFRESH_KEY = 'angel_refresh_token';
const ANGEL_FEED_KEY = 'angel_feed_token';

export const tokenUtils = {
  getJwtToken: () => localStorage.getItem(ANGEL_JWT_KEY),
  setJwtToken: (token: string) => localStorage.setItem(ANGEL_JWT_KEY, token),
  
  getRefreshToken: () => localStorage.getItem(ANGEL_REFRESH_KEY),
  setRefreshToken: (token: string) => localStorage.setItem(ANGEL_REFRESH_KEY, token),
  
  getFeedToken: () => localStorage.getItem(ANGEL_FEED_KEY),
  setFeedToken: (token: string) => localStorage.setItem(ANGEL_FEED_KEY, token),
  
  clearTokens: () => {
    localStorage.removeItem(ANGEL_JWT_KEY);
    localStorage.removeItem(ANGEL_REFRESH_KEY);
    localStorage.removeItem(ANGEL_FEED_KEY);
  },
};
