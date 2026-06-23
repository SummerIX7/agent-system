import type {
  LearnerProfileInput,
  LearnerProfile,
  GenerateRequest,
  ResourceOutput,
  FeedbackInput,
  FeedbackResponse,
  VisualizationData,
} from '~/types/api'

/**
 * 后端 API 封装
 */
export function useApi() {
  const config = useRuntimeConfig()
  const baseURL = config.public.apiBase as string

  const request = async <T>(url: string, options: RequestInit = {}): Promise<T> => {
    const response = await fetch(`${baseURL}${url}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(`API Error ${response.status}: ${error}`)
    }

    return response.json()
  }

  return {
    // 学习者画像
    createProfile: (data: LearnerProfileInput) =>
      request<LearnerProfile>('/api/profile', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    getProfile: (learnerId: string) =>
      request<LearnerProfile>(`/api/profile/${learnerId}`),

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

    getResources: (sessionId: string) =>
      request<ResourceOutput[]>(`/api/resources/${sessionId}`),

    // 反馈
    submitFeedback: (data: FeedbackInput) =>
      request<FeedbackResponse>('/api/feedback', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    // 可视化
    getVisualization: (sessionId: string) =>
      request<VisualizationData>(`/api/visualization/${sessionId}`),

    // 历史
    getHistory: (learnerId: string) =>
      request<any[]>(`/api/history/${learnerId}`),
  }
}
