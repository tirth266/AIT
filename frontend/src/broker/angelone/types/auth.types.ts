export interface AngelCredentials {
  client_id: string;
  api_key: string;
  secret_key: string;
  mpin: string;
  totp_token?: string;
}

export interface AngelSession {
  jwt_token: string;
  refresh_token: string;
  feed_token: string;
}

export interface AngelUserProfile {
  client_code: string;
  name: string;
  email: string;
  mobileno: string;
  exchanges: string[];
  products: string[];
  last_login_time: string;
  broker: 'ANGELONE';
}

export interface AngelLoginResponse {
  success: boolean;
  message: string;
  access_token: string;
  broker_token: string;
  refresh_token: string;
  feed_token: string;
  client_code: string;
  data?: AngelSession & { access_token?: string };
}
