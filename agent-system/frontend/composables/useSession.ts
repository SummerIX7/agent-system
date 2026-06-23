/**
 * 全局会话状态管理
 */
export function useSession() {
  const sessionId = useState<string>('sessionId', () => '')
  const learnerId = useState<string>('learnerId', () => '')
  const profile = useState<any>('profile', () => null)

  const setSession = (sid: string, lid: string) => {
    sessionId.value = sid
    learnerId.value = lid
  }

  const setProfile = (p: any) => {
    profile.value = p
  }

  return {
    sessionId,
    learnerId,
    profile,
    setSession,
    setProfile,
  }
}
