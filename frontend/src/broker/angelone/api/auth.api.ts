import { angelClient } from './apiClient';
import { AngelCredentials, AngelLoginResponse, AngelUserProfile } from '../types';

export const authApi = {
  login: (credentials: AngelCredentials) => 
    angelClient.post<AngelLoginResponse>('/login', credentials),
    
  logout: () => 
    angelClient.post('/logout'),
    
  getProfile: () => 
    angelClient.get<{ data: AngelUserProfile }>('/profile'),
    
  generateToken: (refreshToken: string) => 
    angelClient.post('/refresh', { refresh_token: refreshToken }),

  testConnection: () =>
    angelClient.get('/test-connection'),
};
