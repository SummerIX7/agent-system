// === 学习者画像 ===

export interface LearnerProfileInput {
  education_background: string
  major: string
  work_experience_years: number
  career_track?: string
  current_level?: string
  self_assessment: Record<string, string>
  learning_style: string
  goals: string[]
  domain?: string
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
  career_track?: string
  current_level?: string
  self_assessment: Record<string, string>
  learning_style: string
  goals: string[]
  knowledge_points: KnowledgePoint[]
  blind_spots: (string | { name: string; severity?: number })[]
  overall_level: string
  recommended_difficulty: string
  learning_path?: LearningPathData
  machine_approval_status?: string
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
  /** 后端生成时会带，但 C 端展示来源是从 content 中的"📚 来源："标记解析的（见 ResourcesView.parseSources），不直接消费此字段 */
  sources?: unknown[]
  stage?: number
  review_score?: number | null
  review_passed?: boolean
}

// === 反馈 ===

export interface FeedbackInput {
  session_id: string
  topic: string
  question: string
  user_answer: string
  correct_answer: string
  round?: number
  heuristic_context?: string
}

export interface FeedbackResponse {
  is_correct: boolean
  correct_answer: string
  heuristic_question: string | null
  topic: string
  correctness: number
  round?: number
  reveal_answer?: boolean
}

// === 实操题批改 ===

export interface PracticalFeedbackInput {
  session_id: string
  topic: string
  question: string
  user_answer: string
  correct_answer: string
  explanation?: string
}

export interface PracticalFeedbackResponse {
  score: number
  is_correct: boolean
  feedback: string
  key_points: string[]
  reference_answer: string
}

// === 可视化 ===

export interface VisualizationData {
  knowledge_points: KnowledgePoint[]
  blind_spots: { name: string; severity: number }[]
  learning_path: { title: string; completed: boolean; score?: number }[]
  match_curve: { learner_level: string; resources: { name: string; difficulty: number; match: number }[] } | null
  agent_logs: TraceAgentLog[]
  metrics?: {
    hallucination_rate: number | null
    difficulty_match_rate: number | null
    knowledge_coverage_rate: number | null
  }
  learning_path_meta?: {
    total_estimated_hours: number
    current_stage: number
    recommended_order: string
  } | null
}

// === Agent 状态 ===

export interface AgentStatus {
  name: string
  status: 'idle' | 'running' | 'completed' | 'error'
  message: string
  progress: number
}

// === 职业方向配置 ===

export interface CareerTrackConfig {
  code: string
  name: string
  description: string
  order: number
  difficulty_levels: string[]
  self_assessment_skills: string[]
  prerequisite_knowledge: string
}

// 兼容别名
export type DomainConfig = CareerTrackConfig


// === 学习路径（实测 /api/learning-path/{sid}） ===

export interface LearningPathNode {
  stage: number
  title: string
  topics: string[]
  estimated_hours: number
  difficulty: string
  prerequisites: string[]
  resources_type: string[]
  completed?: boolean
  basic_test_passed?: boolean
  advanced_test_passed?: boolean
  /** 资源是否已生成（工作流 finalize 阶段统一标记） */
  has_resources?: boolean
}

export interface LearningPathData {
  nodes: LearningPathNode[]
  total_estimated_hours: number
  current_stage: number
  recommended_order: string
  all_completed: boolean
}

// === 试题与练习（实测 /api/questions/*） ===

export type QuestionType = 'multiple_choice' | 'true_false' | 'practical'

/** 后端返回的原始试题 */
export interface PracticeQuestion {
  question: string
  question_type: QuestionType | string
  options?: string[]
  correct_answer?: string
  explanation?: string
  topic?: string
}

/** 前端答题流程中附加了作答状态的试题（PracticeView/usePractice） */
export interface PracticeQuestionState extends PracticeQuestion {
  correctIndex: number
  selectedIndex: number
  answered: boolean
  finalCorrect: boolean | null
  correctAnswer: string
  practicalAnswer: string
  practicalGraded: boolean
  practicalResult: PracticalFeedbackResponse | null
}

/** 综合练习的共享生产场景 */
export interface ComprehensiveScenario {
  title?: string
  role?: string
  production_task?: string
  machine?: string
  controller?: string
  material?: string
  blank_size?: string
  batch_size?: string
  clamping?: string
  work_coordinate?: string
  drawing_requirements?: { item: string; requirement: string }[]
  first_article_results?: { item: string; requirement: string; measured?: string }[]
  tools?: string[]
  program_excerpt?: string
  site_conditions?: string[]
  runtime_symptoms?: string[]
}

export interface TieredQuestionSet {
  level: 'node' | 'comprehensive' | string
  label: string
  topic: string
  difficulty: string
  format_version?: string
  stage?: number
  scenario?: ComprehensiveScenario | null
  questions: PracticeQuestion[]
}

/** 练习存档中的单题状态（只保存作答相关字段，题目本体在恢复时与题集按题干合并） */
export interface PracticeQuestionSaveState {
  question: string
  selectedIndex: number
  answered: boolean
  finalCorrect: boolean | null
  practicalAnswer: string
  practicalGraded: boolean
  practicalResult: PracticalFeedbackResponse | null
}

/** 练习作答进度的持久化结构（前端定义、后端原样存取） */
export interface PracticeStateData {
  current_index: number
  questions: PracticeQuestionSaveState[]
  level?: string | null
  stage?: number | null
}

export interface PracticeResultRecord {
  level?: string
  stage?: number | null
  score: number
  correct_count?: number
  wrong_count?: number
  question_count?: number
  created_at?: string
  questions?: Array<{
    topic: string
    question: string
    question_type: string
    is_correct: boolean
    user_answer: string
    correct_answer: string
  }>
}

// === 工作流追踪（实测 /api/trace/{sid}） ===

export interface TraceLlmCall {
  label: string
  prompt: string
  response?: string
  elapsed_ms?: number
  cache_hit?: boolean
  timestamp?: string
}

export interface TraceNodeOutput {
  all_passed?: boolean
  has_degraded?: boolean
  [key: string]: unknown
}

export interface TraceNode {
  node: string
  agent_name: string
  input: Record<string, unknown>
  output: TraceNodeOutput | null
  llm_calls: TraceLlmCall[]
  duration_ms: number
  timestamp?: string
}

export interface TraceAgentLog {
  agent_name: string
  status: string
  message: string
  progress?: number
  timestamp?: string
}

export interface TraceData {
  session_id: string
  topic: string
  profile?: Record<string, unknown>
  nodes: TraceNode[]
  agent_logs?: TraceAgentLog[]
  outcome?: { result?: string; resources_count?: number } | null
}

// === 知识图谱（实测 /api/knowledge-graph/*） ===

export interface KgStats {
  total: number
  mastered: number
  learning: number
  weak: number
  recommended: number
  to_improve: number
  average_score: number
  percentage: number
}

export interface KnowledgePointScore {
  score: number
  status: string
  source?: string
  updated_at?: string
}

export interface KgProgress {
  username: string
  completed_nodes: string[]
  node_scores?: Record<string, KnowledgePointScore>
  total: number
  percentage: number
  stats?: KgStats
}

// —— 力导向图（自 useKnowledgeGraph.ts 收编） ——

export interface GraphNode {
  id: string
  name: string
  type: 'root' | 'category' | 'knowledge'
  category: string
  category_label: string
  score: number
  status: string
  status_label: string
  is_leaf: boolean
  file?: string
  source_type?: string
  source_name?: string
  author?: string
  year?: string
  chapter?: string
}

export interface GraphLink {
  source: string
  target: string
  relation?: string
}

export interface GraphCategoryStat {
  key: string
  name: string
  total: number
  mastered: number
  to_improve: number
  average_score: number
  percentage: number
  items?: GraphNode[]
}

export interface GraphLegendItem {
  status: string
  label: string
  color: string
}

export interface GraphStats {
  total: number
  mastered: number
  learning: number
  weak: number
  recommended: number
  to_improve: number
  average_score: number
  percentage: number
}

export interface GraphPayload {
  domain: string
  domain_name: string
  nodes: GraphNode[]
  links: GraphLink[]
  stats: GraphStats
  categories: GraphCategoryStat[]
  legend: GraphLegendItem[]
}

// === 历史记录（实测 /api/history/{learnerId}） ===

export interface HistoryItem {
  title: string
  date: string
  description: string
  tags: string[]
}

export interface HistoryResponse {
  items: HistoryItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}
