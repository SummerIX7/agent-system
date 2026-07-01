import type {
  LearnerProfileInput,
  LearnerProfile,
  GenerateRequest,
  ResourceOutput,
  FeedbackInput,
  FeedbackResponse,
  PracticalFeedbackInput,
  PracticalFeedbackResponse,
  VisualizationData,
  DomainConfig,
} from '~/types/api'

/**
 * 后端 API 封装（带认证）
 */
export function useApi() {
  const config = useRuntimeConfig()
  const baseURL = config.public.apiBase as string
  const { token, logout } = useAuth()
  const router = useRouter()

  const request = async <T>(url: string, options: RequestInit = {}): Promise<T> => {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...options.headers as Record<string, string>,
    }

    // 自动添加认证头
    if (token.value) {
      headers['Authorization'] = `Bearer ${token.value}`
    }

    const response = await fetch(`${baseURL}${url}`, {
      headers,
      ...options,
    })

    if (response.status === 401) {
      // token 过期或无效，跳转登录
      logout()
      router.push('/login')
      throw new Error('认证已过期，请重新登录')
    }

    if (!response.ok) {
      const error = await response.json().catch(() => response.text())
      throw new Error(error.detail || `API Error ${response.status}`)
    }

    return response.json()
  }

  return {
    // 认证
    register: (data: { username: string; password: string; email?: string }) =>
      request<{ access_token: string; user_id: number; username: string }>('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    login: (data: { username: string; password: string }) =>
      request<{ access_token: string; user_id: number; username: string }>('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    getMe: () =>
      request<{ id: number; username: string; email?: string }>('/api/auth/me'),

    // 学习者画像
    createProfile: (data: LearnerProfileInput) =>
      request<LearnerProfile>('/api/profile', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    getMyProfile: () =>
      request<LearnerProfile>('/api/profile/me'),

    // 资源生成
    generateResources: (sessionId: string, topic: string, resourceTypes?: string[], profile?: any) =>
      request<ResourceOutput[]>('/api/generate', {
        method: 'POST',
        body: JSON.stringify({
          session_id: sessionId,
          topic,
          resource_types: resourceTypes || ['lecture', 'guide', 'test'],
          profile: profile || null,
        }),
      }),

    getResources: (sessionId: string, stage?: number) =>
      request<ResourceOutput[]>(`/api/resources/${sessionId}${stage !== undefined ? `?stage=${stage}` : ''}`),

    // 反馈
    submitFeedback: (data: FeedbackInput) =>
      request<FeedbackResponse>('/api/feedback/', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    // 实操题批改
    submitPracticalFeedback: (data: PracticalFeedbackInput) =>
      request<PracticalFeedbackResponse>('/api/feedback/practical', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    // 可视化
    getVisualization: (sessionId: string) =>
      request<VisualizationData>(`/api/visualization/${sessionId}`),

    // 历史
    getHistory: (learnerId: number) =>
      request<any[]>(`/api/history/${learnerId}`),

    // 试题
    getQuestions: (sessionId: string) =>
      request<{ topic: string; difficulty: string; questions: any[] }>(`/api/questions/${sessionId}`),

    // 答题进度持久化
    savePracticeState: (sessionId: string, data: { current_index: number; questions: any[] }) =>
      request<{ ok: boolean }>(`/api/questions/practice/state/${sessionId}`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    getPracticeState: (sessionId: string) =>
      request<{ current_index: number; questions: any[] }>(`/api/questions/practice/state/${sessionId}`),

    // 重新生成试题（清除缓存后重新调用 LLM 生成）
    regenerateQuestions: (sessionId: string) =>
      request<{ topic: string; difficulty: string; questions: any[] }>(`/api/questions/practice/regenerate/${sessionId}`, {
        method: 'POST',
      }),

    // 分阶试题
    generateTieredQuestions: (sessionId: string) =>
      request<{ node_title: string; basic: any; advanced: any }>(`/api/questions/generate/${sessionId}`, {
        method: 'POST',
      }),

    getTieredQuestions: (sessionId: string, level: 'basic' | 'advanced', stage?: number) =>
      request<{ level: string; label: string; topic: string; difficulty: string; questions: any[] }>(`/api/questions/set/${sessionId}/${level}${stage !== undefined ? `?stage=${stage}` : ''}`),

    // 学习路径管理
    getLearningPath: (sessionId: string) =>
      request<{ nodes: any[]; total_estimated_hours: number; current_stage: number; recommended_order: string; all_completed: boolean }>(`/api/learning-path/${sessionId}`),

    getCurrentNode: (sessionId: string) =>
      request<{ current_node: any; total_nodes: number; all_completed: boolean }>(`/api/learning-path/${sessionId}/current-node`),

    advanceNode: (sessionId: string, data: { basic_score: number; advanced_score: number; test_feedback: any[] }) =>
      request<{ advanced_passed: boolean; current_stage: number; total_stages: number; message: string; new_stage: number | null; all_completed: boolean }>(`/api/learning-path/${sessionId}/advance`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    // 领域
    getDomains: () =>
      request<DomainConfig[]>('/api/domains'),
  }
}
