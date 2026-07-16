import type { AxiosInstance } from 'axios'
import { createHttpClient } from '~/utils/http'
import type {
  LearnerProfileInput,
  LearnerProfile,
  ResourceOutput,
  FeedbackInput,
  FeedbackResponse,
  PracticalFeedbackInput,
  PracticalFeedbackResponse,
  VisualizationData,
  CareerTrackConfig,
} from '~/types/api'

/**
 * 后端 API 封装（axios 版）
 *
 * 所有请求统一走 utils/http.ts 中的 axios 实例：
 * - 请求拦截自动带上 Authorization Bearer token
 * - 401 触发 logout + 跳转 /login
 * - 其他非 2xx 抽取 detail 抛错，调用方直接 try/catch (err as Error).message
 */
export function useApi() {
  const config = useRuntimeConfig()
  const baseURL = config.public.apiBase as string
  const { token, logout } = useAuth()
  const router = useRouter()

  const http: AxiosInstance = createHttpClient({
    baseURL,
    getToken: () => token.value,
    onUnauthorized: () => {
      logout()
      // router.push 在 SSR 时是同步；组件卸载路径下也安全
      router.push('/login')
    },
  })

  // 统一小助手：把 axios 返回体拆到 data，业务侧只处理业务对象
  const req = async <T>(method: string, url: string, body?: unknown): Promise<T> => {
    const res = await http.request<T>({
      url,
      method,
      data: body,
    })
    return res.data
  }

  const get = <T>(url: string) => req<T>('GET', url)
  const post = <T>(url: string, body?: unknown) => req<T>('POST', url, body)

  return {
    // 认证
    register: (data: { username: string; password: string; email?: string }) =>
      post<{ access_token: string; user_id: number; username: string; role: string }>('/api/auth/register', data),

    login: (data: { username: string; password: string }) =>
      post<{ access_token: string; user_id: number; username: string; role: string }>('/api/auth/login', data),

    getMe: () =>
      get<{ id: number; username: string; email?: string; role: string }>('/api/auth/me'),

    // 学习者画像
    createProfile: (data: LearnerProfileInput) =>
      post<LearnerProfile>('/api/profile/', data),

    getMyProfile: () =>
      get<LearnerProfile>('/api/profile/me'),

    // 资源生成
    generateResources: (sessionId: string, topic: string, resourceTypes?: string[], profile?: any) =>
      post<ResourceOutput[]>('/api/generate', {
        session_id: sessionId,
        topic,
        resource_types: resourceTypes || ['lecture', 'guide', 'test'],
        profile: profile || null,
      }),

    getResources: (sessionId: string, stage?: number) =>
      get<ResourceOutput[]>(`/api/resources/${sessionId}${stage !== undefined ? `?stage=${stage}` : ''}`),

    // 反馈
    submitFeedback: (data: FeedbackInput) =>
      post<FeedbackResponse>('/api/feedback/', data),

    // 实操题批改
    submitPracticalFeedback: (data: PracticalFeedbackInput) =>
      post<PracticalFeedbackResponse>('/api/feedback/practical', data),

    // 可视化
    getVisualization: (sessionId: string) =>
      get<VisualizationData>(`/api/visualization/${sessionId}`),

    // 历史
    getHistory: (learnerId: number | string, page: number = 1, pageSize: number = 20) =>
      get<{ items: any[]; total: number; page: number; page_size: number; total_pages: number }>(
        `/api/history/${learnerId}?page=${page}&page_size=${pageSize}`,
      ),

    // 试题
    getQuestions: (sessionId: string) =>
      get<{ topic: string; difficulty: string; questions: any[] }>(`/api/questions/${sessionId}`),

    // 答题进度持久化
    savePracticeState: (
      sessionId: string,
      data: { current_index: number; questions: any[]; level?: string | null; stage?: number | null },
    ) => post<{ ok: boolean }>(`/api/questions/practice/state/${sessionId}`, data),

    getPracticeState: (sessionId: string, level?: string | null, stage?: number | null) => {
      const query = new URLSearchParams()
      if (level) query.set('level', level)
      if (stage !== undefined && stage !== null) query.set('stage', String(stage))
      const suffix = query.toString() ? `?${query.toString()}` : ''
      return get<{ current_index: number; questions: any[]; level?: string | null; stage?: number | null }>(
        `/api/questions/practice/state/${sessionId}${suffix}`,
      )
    },

    // 重新生成试题
    regenerateQuestions: (sessionId: string) =>
      post<{ topic: string; difficulty: string; questions: any[] }>(`/api/questions/practice/regenerate/${sessionId}`),

    // 节点练习
    generateTieredQuestions: (sessionId: string) =>
      post<{ node_title: string; node: any }>(`/api/questions/generate/${sessionId}`),

    getTieredQuestions: (sessionId: string, level: 'node' | 'comprehensive', stage?: number) =>
      get<{
        level: string
        label: string
        topic: string
        difficulty: string
        format_version?: string
        scenario?: Record<string, any>
        questions: any[]
      }>(`/api/questions/set/${sessionId}/${level}${stage !== undefined ? `?stage=${stage}` : ''}`),

    savePracticeResult: (
      sessionId: string,
      data: {
        level: string
        stage?: number | null
        score: number
        correct_count: number
        wrong_count: number
        question_count: number
        questions: any[]
      },
    ) => post<{ ok: boolean; total: number }>(`/api/questions/practice/result/${sessionId}`, data),

    getPracticeResults: (sessionId: string) =>
      get<{ results: any[] }>(`/api/questions/practice/results/${sessionId}`),

    // 学习路径管理
    getLearningPath: (sessionId: string) =>
      get<{
        nodes: any[]
        total_estimated_hours: number
        current_stage: number
        recommended_order: string
        all_completed: boolean
      }>(`/api/learning-path/${sessionId}`),

    getCurrentNode: (sessionId: string) =>
      get<{ current_node: any; total_nodes: number; all_completed: boolean }>(
        `/api/learning-path/${sessionId}/current-node`,
      ),

    advanceNode: (sessionId: string, data: { basic_score: number; advanced_score: number; test_feedback: any[] }) =>
      post<{
        advanced_passed: boolean
        current_stage: number
        total_stages: number
        message: string
        new_stage: number | null
        all_completed: boolean
      }>(`/api/learning-path/${sessionId}/advance`, data),

    markBasicPassed: (sessionId: string, basicScore: number = 70) =>
      post<{ ok: boolean; stage: number; basic_test_passed: boolean }>(
        `/api/learning-path/${sessionId}/mark-basic-passed`,
        { basic_score: basicScore },
      ),

    completeCurrentNode: (sessionId: string) =>
      post<{
        ok: boolean
        stage?: number
        new_stage: number | null
        all_completed: boolean
        message: string
      }>(`/api/learning-path/${sessionId}/complete-current`),

    generateNodeContent: (sessionId: string, stage: number) =>
      post<{ ok: boolean; stage: number; resource_count: number }>(
        `/api/learning-path/${sessionId}/generate-node-content`,
        { session_id: sessionId, stage },
      ),

    // 职业方向
    getCareerTracks: () => get<CareerTrackConfig[]>('/api/career-tracks'),
    // 兼容
    getDomains: () => get<CareerTrackConfig[]>('/api/domains'),

    // 知识图谱
    getKnowledgeGraph: () => get<any>('/api/knowledge-graph'),

    getKnowledgeGraphGraph: (withProgress: boolean = true) =>
      get<any>(withProgress ? '/api/knowledge-graph/progress/graph' : '/api/knowledge-graph/graph'),

    getKnowledgeGraphProgress: () =>
      get<{
        username: string
        completed_nodes: string[]
        node_scores?: Record<string, any>
        total: number
        percentage: number
        stats?: any
      }>('/api/knowledge-graph/progress'),

    getKnowledgeGraphTreeWithProgress: () =>
      get<any>('/api/knowledge-graph/progress/tree'),

    markKnowledgeNode: (nodeId: string, completed: boolean, score?: number) =>
      post<{
        username: string
        completed_nodes: string[]
        node_scores?: Record<string, any>
        total: number
        percentage: number
        stats?: any
      }>('/api/knowledge-graph/progress', { node_id: nodeId, completed, score }),

    // 机台使用申请
    applyMachine: () =>
      post<{ message: string; status: string }>('/api/profile/apply-machine'),

    // 重新评估学习者画像
    reassessProfile: () =>
      post<import('~/types/api').LearnerProfile>('/api/profile/reassess'),

    // 追踪（调试）
    getTrace: (sessionId: string) =>
      get<any>(`/api/trace/${sessionId}`),
  }
}
