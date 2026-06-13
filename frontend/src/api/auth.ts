import api from "./index";

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  role?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
}

export const authApi = {
  login: (data: LoginRequest) =>
    api.post<TokenResponse>("/auth/login", data),

  register: (data: RegisterRequest) =>
    api.post<UserResponse>("/auth/register", data),

  getMe: () =>
    api.get<UserResponse>("/auth/me"),

  initAdmin: () =>
    api.post<UserResponse>("/auth/init-admin"),
};
