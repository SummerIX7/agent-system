/** 管理员用户 */
export interface AdminUser {
  id: number
  username: string
  email: string
  role: 'admin' | 'learner'
}

/** 数据看板概览 */
export interface DashboardOverview {
  total_learners: number
  pending_approvals: number
  active_today: number
  avg_pass_rate: number
  knowledge_distribution: Record<string, { low: number; medium: number; high: number }>
  kg_stats?: {
    learners_with_progress: number
    avg_percentage: number
  }
}

/** 学员列表项 */
export interface LearnerItem {
  id: number
  username: string
  email: string
  education_background: string
  major: string
  overall_level: string
  learning_progress: number
  kg_progress?: {
    completed_nodes: string[]
    percentage: number
    total: number
  }
  machine_approval_status: 'none' | 'pending' | 'approved' | 'rejected'
  updated_at: string
}

/** 分页列表 */
export interface PaginatedList<T> {
  total: number
  page: number
  page_size: number
  items: T[]
}

/** 审批日志 */
export interface ApprovalLog {
  id: number
  learner_id: number
  action: 'submit' | 'approve' | 'reject'
  operator_id: number
  reason: string | null
  created_at: string
}
