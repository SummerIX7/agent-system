import { api } from './request'
import type { AdminUser } from '@/types/admin'

interface LoginResponse {
  access_token: string
  token_type: string
  user_id: number
  username: string
  role: string
}

export const authApi = {
  login: (username: string, password: string) =>
    api.post<LoginResponse>('/auth/login', { username, password }),

  getMe: () => api.get<AdminUser>('/auth/me'),
}
