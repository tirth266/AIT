import { apiClient } from './axios';
import { AngelOneLoginPayload, AuthResponse } from '../types/auth.types';

export const loginToAngelOne = async (payload: AngelOneLoginPayload): Promise<AuthResponse> => {
  try {
    const response = await apiClient.post<AuthResponse>('/broker/angelone/login', payload);
    return response.data;
  } catch (error: any) {
    if (error.response && error.response.data) {
      return error.response.data as AuthResponse;
    }
    return {
      success: false,
      message: 'Network error or server is unreachable',
      error: 'NETWORK_ERROR'
    };
  }
};

export const checkAngelOneStatus = async (): Promise<{ is_valid: boolean }> => {
  try {
    const response = await apiClient.get('/broker/angelone/session/status');
    return response.data;
  } catch (error) {
    return { is_valid: false };
  }
};
