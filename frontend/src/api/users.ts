import api from "./index";

export interface UserRoleResponse {
  id: string;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
}

export interface CreateUserRequest {
  username: string;
  email: string;
  password: string;
  role?: string;
}

export interface UpdateUserRequest {
  email?: string;
  password?: string;
}

export const usersApi = {
  list: (keyword?: string) =>
    api.get<UserRoleResponse[]>("/users", { params: keyword ? { keyword } : {} }),

  create: (data: CreateUserRequest) =>
    api.post<UserRoleResponse>("/users", data),

  update: (userId: string, data: UpdateUserRequest) =>
    api.put<UserRoleResponse>(`/users/${userId}`, data),

  changeRole: (userId: string, role: string) =>
    api.put<UserRoleResponse>(`/users/${userId}/role`, { role }),

  toggleActive: (userId: string) =>
    api.put<UserRoleResponse>(`/users/${userId}/toggle-active`),
};
