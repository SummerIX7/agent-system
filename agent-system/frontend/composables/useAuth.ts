/**
 * 用户认证状态管理
 */
export function useAuth() {
  const token = useState<string>('auth_token', () => '')
  const user = useState<{ id: number; username: string; role: string } | null>('auth_user', () => null)
  const isLoading = useState<boolean>('auth_loading', () => true)

  const isLoggedIn = computed(() => !!token.value)

  // 从 localStorage 恢复 token 和用户信息
  const restoreToken = async () => {
    if (import.meta.client) {
      const saved = localStorage.getItem('auth_token')
      if (saved) {
        token.value = saved
        // 恢复用户信息
        try {
          const config = useRuntimeConfig()
          const response = await fetch(`${config.public.apiBase}/api/auth/me`, {
            headers: { Authorization: `Bearer ${saved}` },
          })
          if (response.ok) {
            const data = await response.json()
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
  }

  // 设置 token
  const setToken = (newToken: string) => {
    token.value = newToken
    if (import.meta.client) {
      localStorage.setItem('auth_token', newToken)
    }
  }

  // 设置用户信息
  const setUser = (userInfo: { id: number; username: string; role?: string }) => {
    user.value = userInfo
  }

  // 登出
  const logout = () => {
    token.value = ''
    user.value = null
    if (import.meta.client) {
      localStorage.removeItem('auth_token')
    }
    // 不清除 session——用户下次登录应继续之前的进度
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
