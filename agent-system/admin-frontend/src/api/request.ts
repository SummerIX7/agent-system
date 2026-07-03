import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

const instance = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// 请求拦截器：自动注入 token
instance.interceptors.request.use((config) => {
  const authStore = useAuthStore()
  if (authStore.token) {
    config.headers.Authorization = `Bearer ${authStore.token}`
  }
  return config
})

// 响应拦截器：401 拦截 + 错误提取
instance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const authStore = useAuthStore()
      authStore.logout()
      throw new Error('未授权')
    }
    const detail = error.response?.data?.detail || error.message || '请求失败'
    throw new Error(detail)
  },
)

export const api = {
  get: <T = unknown>(url: string, params?: Record<string, unknown>) =>
    instance.get<T>(url, { params }).then((r) => r.data),

  post: <T = unknown>(url: string, data?: unknown, params?: Record<string, unknown>) =>
    instance.post<T>(url, data, { params }).then((r) => r.data),

  put: <T = unknown>(url: string, data?: unknown) =>
    instance.put<T>(url, data).then((r) => r.data),

  delete: <T = unknown>(url: string, params?: Record<string, unknown>) =>
    instance.delete<T>(url, { params }).then((r) => r.data),
}
