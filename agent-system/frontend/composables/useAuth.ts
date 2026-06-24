/**
 * 用户认证状态管理
 */
export function useAuth() {
  const token = useState<string>('auth_token', () => '')
  const user = useState<{ id: number; username: string } | null>('auth_user', () => null)

  const isLoggedIn = computed(() => !!token.value)

  // 从 localStorage 恢复 token
  const restoreToken = () => {
    if (import.meta.client) {
      const saved = localStorage.getItem('auth_token')
      if (saved) {
        token.value = saved
      }
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
  const setUser = (userInfo: { id: number; username: string }) => {
    user.value = userInfo
  }

  // 登出
  const logout = () => {
    token.value = ''
    user.value = null
    if (import.meta.client) {
      localStorage.removeItem('auth_token')
    }
  }

  return {
    token,
    user,
    isLoggedIn,
    restoreToken,
    setToken,
    setUser,
    logout,
  }
}
