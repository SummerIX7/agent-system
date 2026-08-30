/**
 * 全局会话状态管理
 * sessionId 持久化到 localStorage，确保刷新/重登后数据不丢失
 */
const STORAGE_KEY = 'agent_session_id'
const LEARNER_KEY = 'agent_learner_id'

export function useSession() {
  const sessionId = useState<string>('sessionId', () => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem(STORAGE_KEY) || ''
    }
    return ''
  })
  const learnerId = useState<string>('learnerId', () => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem(LEARNER_KEY) || ''
    }
    return ''
  })
  const profile = useState<any>('profile', () => null)

  const setSession = (sid: string, lid: string) => {
    sessionId.value = sid
    learnerId.value = lid
    if (typeof window !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, sid)
      localStorage.setItem(LEARNER_KEY, lid)
    }
  }

  const setProfile = (p: any) => {
    profile.value = p
  }

  const clearSession = () => {
    sessionId.value = ''
    learnerId.value = ''
    profile.value = null
    if (typeof window !== 'undefined') {
      localStorage.removeItem(STORAGE_KEY)
      localStorage.removeItem(LEARNER_KEY)
    }
  }

  return {
    sessionId,
    learnerId,
    profile,
    setSession,
    setProfile,
    clearSession,
  }
}
