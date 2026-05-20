export interface AngelOneLoginPayload {
  client_code: string;
  password: string;
  totp: string;
}

export interface AuthState {
  isAuthenticated: boolean;
  jwtToken: string | null;
  feedToken: string | null;
  clientCode: string | null;
}

export interface AuthResponse {
  success: boolean;
  message: string;
  data?: {
    jwt_token: string;
    refresh_token: string;
    feed_token: string;
  };
  error?: string;
}
