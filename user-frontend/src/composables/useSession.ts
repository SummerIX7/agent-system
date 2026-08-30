/**
 * 全局会话状态管理（模块级单例状态）
 * sessionId 持久化到 localStorage，确保刷新/重登后数据不丢失
 */
import { ref } from 'vue'

const STORAGE_KEY = 'agent_session_id'
const LEARNER_KEY = 'agent_learner_id'

// 模块级单例：初始化时从 localStorage 恢复
const sessionId = ref(localStorage.getItem(STORAGE_KEY) || '')
const learnerId = ref(localStorage.getItem(LEARNER_KEY) || '')
const profile = ref<any>(null)

export function useSession() {
  const setSession = (sid: string, lid: string) => {
    sessionId.value = sid
    learnerId.value = lid
    localStorage.setItem(STORAGE_KEY, sid)
    localStorage.setItem(LEARNER_KEY, lid)
  }

  const setProfile = (p: any) => {
    profile.value = p
  }

  const clearSession = () => {
    sessionId.value = ''
    learnerId.value = ''
    profile.value = null
    localStorage.removeItem(STORAGE_KEY)
    localStorage.removeItem(LEARNER_KEY)
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
