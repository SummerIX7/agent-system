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
  CareerTrackConfig,
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
      request<{ access_token: string; user_id: number; username: string; role: string }>('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    login: (data: { username: string; password: string }) =>
      request<{ access_token: string; user_id: number; username: string; role: string }>('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    getMe: () =>
      request<{ id: number; username: string; email?: string; role: string }>('/api/auth/me'),

    // 学习者画像
    createProfile: (data: LearnerProfileInput) =>
      request<LearnerProfile>('/api/profile/', {
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
    getHistory: (learnerId: number | string) =>
      request<any[]>(`/api/history/${learnerId}`),

    // 试题
    getQuestions: (sessionId: string) =>
      request<{ topic: string; difficulty: string; questions: any[] }>(`/api/questions/${sessionId}`),

    // 答题进度持久化
    savePracticeState: (sessionId: string, data: { current_index: number; questions: any[]; level?: string | null; stage?: number | null }) =>
      request<{ ok: boolean }>(`/api/questions/practice/state/${sessionId}`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    getPracticeState: (sessionId: string, level?: string | null, stage?: number | null) => {
      const query = new URLSearchParams()
      if (level) query.set('level', level)
      if (stage !== undefined && stage !== null) query.set('stage', String(stage))
      const suffix = query.toString() ? `?${query.toString()}` : ''
      return request<{ current_index: number; questions: any[]; level?: string | null; stage?: number | null }>(`/api/questions/practice/state/${sessionId}${suffix}`)
    },

    // 重新生成试题（清除缓存后重新调用 LLM 生成）
    regenerateQuestions: (sessionId: string) =>
      request<{ topic: string; difficulty: string; questions: any[] }>(`/api/questions/practice/regenerate/${sessionId}`, {
        method: 'POST',
      }),

    // 节点练习
    generateTieredQuestions: (sessionId: string) =>
      request<{ node_title: string; node: any }>(`/api/questions/generate/${sessionId}`, {
        method: 'POST',
      }),

    getTieredQuestions: (sessionId: string, level: 'node' | 'comprehensive', stage?: number) =>
      request<{ level: string; label: string; topic: string; difficulty: string; format_version?: string; scenario?: Record<string, any>; questions: any[] }>(`/api/questions/set/${sessionId}/${level}${stage !== undefined ? `?stage=${stage}` : ''}`),

    savePracticeResult: (sessionId: string, data: { level: string; stage?: number | null; score: number; correct_count: number; wrong_count: number; question_count: number; questions: any[] }) =>
      request<{ ok: boolean; total: number }>(`/api/questions/practice/result/${sessionId}`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    getPracticeResults: (sessionId: string) =>
      request<{ results: any[] }>(`/api/questions/practice/results/${sessionId}`),

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

    markBasicPassed: (sessionId: string, basicScore: number = 70) =>
      request<{ ok: boolean; stage: number; basic_test_passed: boolean }>(`/api/learning-path/${sessionId}/mark-basic-passed`, {
        method: 'POST',
        body: JSON.stringify({ basic_score: basicScore }),
      }),

    completeCurrentNode: (sessionId: string) =>
      request<{ ok: boolean; stage?: number; new_stage: number | null; all_completed: boolean; message: string }>(`/api/learning-path/${sessionId}/complete-current`, {
        method: 'POST',
      }),

    generateNodeContent: (sessionId: string, stage: number) =>
      request<{ ok: boolean; stage: number; resource_count: number }>(`/api/learning-path/${sessionId}/generate-node-content`, {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId, stage }),
      }),

    // 职业方向
    getCareerTracks: () =>
      request<CareerTrackConfig[]>('/api/career-tracks'),
    // 兼容
    getDomains: () =>
      request<CareerTrackConfig[]>('/api/domains'),

    // 知识图谱
    getKnowledgeGraph: () =>
      request<any>('/api/knowledge-graph'),

    getKnowledgeGraphGraph: (withProgress: boolean = true) =>
      request<any>(withProgress ? '/api/knowledge-graph/progress/graph' : '/api/knowledge-graph/graph'),

    getKnowledgeGraphProgress: () =>
      request<{ username: string; completed_nodes: string[]; node_scores?: Record<string, any>; total: number; percentage: number; stats?: any }>('/api/knowledge-graph/progress'),

    getKnowledgeGraphTreeWithProgress: () =>
      request<any>('/api/knowledge-graph/progress/tree'),

    markKnowledgeNode: (nodeId: string, completed: boolean, score?: number) =>
      request<{ username: string; completed_nodes: string[]; node_scores?: Record<string, any>; total: number; percentage: number; stats?: any }>('/api/knowledge-graph/progress', {
        method: 'POST',
        body: JSON.stringify({ node_id: nodeId, completed, score }),
      }),

    // 机台使用申请
    applyMachine: () =>
      request<{ message: string; status: string }>('/api/profile/apply-machine', {
        method: 'POST',
      }),
  }
}
