// === 学习者画像 ===

export interface LearnerProfileInput {
  education_background: string
  major: string
  work_experience_years: number
  self_assessment: Record<string, string>
  learning_style: string
  goals: string[]
}

export interface KnowledgePoint {
  name: string
  score: number
  level: string
  confidence?: number
}

export interface LearnerProfile {
  id: number
  session_id?: string
  education_background: string
  major: string
  work_experience_years: number
  self_assessment: Record<string, string>
  learning_style: string
  goals: string[]
  knowledge_points: KnowledgePoint[]
  blind_spots: string[]
  overall_level: string
  recommended_difficulty: string
}

// === 资源生成 ===

export interface GenerateRequest {
  session_id: string
  topic: string
  resource_types?: string[]
}

export interface ResourceOutput {
  type: string
  content: string | any[]
  topic: string
  difficulty: string
  sources?: any[]
}

// === 反馈 ===

export interface FeedbackInput {
  session_id: string
  topic: string
  question: string
  user_answer: string
  correct_answer: string
}

export interface FeedbackResponse {
  is_correct: boolean
  correct_answer: string
  heuristic_question: string | null
  topic: string
  correctness: number
}

// === 可视化 ===

export interface VisualizationData {
  knowledge_points: KnowledgePoint[]
  blind_spots: { name: string; severity: number }[]
  learning_path: { title: string; completed: boolean; score?: number }[]
  match_curve: any | null
  agent_logs: any[]
  metrics?: {
    hallucination_rate: number | null
    difficulty_match_rate: number | null
    knowledge_coverage_rate: number | null
  }
}

// === Agent 状态 ===

export interface AgentStatus {
  name: string
  status: 'idle' | 'running' | 'completed' | 'error'
  message: string
  progress: number
}
