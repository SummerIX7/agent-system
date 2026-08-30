/**
 * 用户认证状态管理（模块级单例状态，SPA 下等价于原 Nuxt useState）
 */
import axios from 'axios'
import { ref } from 'vue'

// 模块级单例：所有调用 useAuth() 的组件共享同一份状态
const token = ref('')
const user = ref<{ id: number; username: string; role: string } | null>(null)
const isLoading = ref(true)

export function useAuth() {
  const isLoggedIn = computed(() => !!token.value)

  // 从 localStorage 恢复 token 和用户信息
  const restoreToken = async () => {
    const saved = localStorage.getItem('auth_token')
    if (saved) {
      token.value = saved
      // 恢复用户信息（直接用 axios，不复用 useApi 的拦截器：此时若 401 应静默清 token 而不是二次触发登出跳转）
      try {
        const { data } = await axios.get('/api/auth/me', {
          headers: { Authorization: `Bearer ${saved}` },
          validateStatus: (status: number) => status < 500,
        })
        if (data && data.id) {
          user.value = { id: data.id, username: data.username, role: data.role || 'learner' }
        } else {
          // token 过期，清除
          token.value = ''
          localStorage.removeItem('auth_token')
        }
      } catch {
        // 网络错误，保留 token 但不设 user
      }
    }
    isLoading.value = false
  }

  // 设置 token
  const setToken = (newToken: string) => {
    token.value = newToken
    localStorage.setItem('auth_token', newToken)
  }

  // 设置用户信息
  const setUser = (userInfo: { id: number; username: string; role?: string }) => {
    user.value = { id: userInfo.id, username: userInfo.username, role: userInfo.role ?? 'learner' }
  }

  // 登出
  const logout = () => {
    token.value = ''
    user.value = null
    localStorage.removeItem('auth_token')
    // 清除 session，防止下一个登录用户继承当前用户的 session 数据
    localStorage.removeItem('agent_session_id')
    localStorage.removeItem('agent_learner_id')
  }

  return {
    token,
    user,
    isLoggedIn,
    isLoading,
    restoreToken,
    setToken,
    setUser,
    logout,
  }
}
