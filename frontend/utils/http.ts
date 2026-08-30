import type { AxiosInstance, AxiosRequestConfig } from 'axios'
import axios, { AxiosError } from 'axios'

interface HttpClientOptions {
  baseURL: string
  getToken: () => string
  onUnauthorized: () => void
}

/**
 * 创建一个带统一拦截器的 axios 实例。
 *
 * 请求拦截：自动带上 Authorization Bearer token（token 存在时）。
 * 响应拦截：
 *  - 401：调用 onUnauthorized（登出 + 跳登录），抛出 `认证已过期` 错误
 *  - 其他非 2xx：抽取 response.data.detail 或 message 作为错误信息，符合后端 FastAPI 返回结构
 *  - 网络错误：抛出 `无法连接后端服务` 错误
 */
export function createHttpClient(options: HttpClientOptions): AxiosInstance {
  const instance = axios.create({
    baseURL: options.baseURL,
    headers: {
      'Content-Type': 'application/json',
    },
    // 避免 axios 默认对 4xx 抛出前把响应体扔掉
    validateStatus: (status) => status >= 200 && status < 300,
  })

  instance.interceptors.request.use((config) => {
    const token = options.getToken()
    if (token) {
      config.headers = config.headers ?? {}
      ;(config.headers as Record<string, string>).Authorization = `Bearer ${token}`
    }
    return config
  })

  instance.interceptors.response.use(
    (response) => response,
    (error: AxiosError<{ detail?: string }>) => {
      // 网络错误 / 后端未启动
      if (!error.response) {
        return Promise.reject(new Error(error.message || '无法连接后端服务'))
      }

      const { status, data } = error.response
      if (status === 401) {
        options.onUnauthorized()
        return Promise.reject(new Error('认证已过期，请重新登录'))
      }

      const detail = (data && typeof data === 'object' && 'detail' in data ? data.detail : undefined)
        || error.message
        || `API Error ${status}`
      return Promise.reject(new Error(String(detail)))
    },
  )

  return instance
}

/**
 * 语法糖：把 axios 请求结果拆到 response.data，供 useApi 调用侧只关心业务体。
 */
export async function unwrap<T>(http: AxiosInstance, config: AxiosRequestConfig): Promise<T> {
  const res = await http.request<T>(config)
  return res.data
}
