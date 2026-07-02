import { useAuthStore } from '@/stores/auth'

const BASE_URL = '/api'

/** 构建 query string，自动过滤 undefined 值 */
function buildQuery(params?: Record<string, unknown>): string {
  if (!params) return ''
  const searchParams = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.append(key, String(value))
    }
  }
  const qs = searchParams.toString()
  return qs ? `?${qs}` : ''
}

/** 统一的 API 请求封装（token 注入 + 401 拦截） */
async function request<T = unknown>(
  url: string,
  options: RequestInit = {},
): Promise<T> {
  const authStore = useAuthStore()

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  if (authStore.token) {
    headers['Authorization'] = `Bearer ${authStore.token}`
  }

  const response = await fetch(`${BASE_URL}${url}`, {
    ...options,
    headers,
  })

  if (response.status === 401) {
    authStore.logout()
    // 不在这里 import router 避免循环依赖，
    // 由调用方在捕获异常后处理跳转
    throw new Error('未授权')
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '请求失败' }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }

  return response.json()
}

export const api = {
  get: <T = unknown>(url: string, params?: Record<string, unknown>) =>
    request<T>(`${url}${buildQuery(params)}`),

  post: <T = unknown>(url: string, data?: unknown, params?: Record<string, unknown>) =>
    request<T>(`${url}${buildQuery(params)}`, { method: 'POST', body: JSON.stringify(data) }),

  put: <T = unknown>(url: string, data?: unknown) =>
    request<T>(url, { method: 'PUT', body: JSON.stringify(data) }),

  delete: <T = unknown>(url: string, params?: Record<string, unknown>) =>
    request<T>(`${url}${buildQuery(params)}`, { method: 'DELETE' }),
}
