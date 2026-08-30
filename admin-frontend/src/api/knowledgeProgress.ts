import { api } from './request'

export interface LearnerProgress {
  username: string
  completed_nodes: string[]
  completed_count: number
  total: number
  percentage: number
}

export interface AllProgressData {
  total_learners: number
  total_knowledge_points: number
  learners: LearnerProgress[]
}

export interface TreeNode {
  name: string
  id: string
  children?: TreeNode[]
  is_leaf?: boolean
  completed?: boolean
  category?: string
  file?: string
  source_type?: string
  author?: string
  year?: string
  chapter?: string
  source_name?: string
  total_leaves?: number
}

export const knowledgeProgressApi = {
  /** 获取所有学员学习进度 */
  getAllProgress: () =>
    api.get<AllProgressData>('/knowledge-graph/progress/all'),

  /** 获取知识图谱树状图数据 */
  getTree: () =>
    api.get<TreeNode>('/knowledge-graph'),

  /** 获取带指定用户进度的树状图数据（需要后端支持，暂用前端合并） */
  getTreeWithUserProgress: (username: string) =>
    api.get<TreeNode>('/knowledge-graph/progress/tree', { user: username }),
}
