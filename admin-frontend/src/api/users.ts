import { api } from './request'
import type { LearnerItem, PaginatedList } from '@/types/admin'

export const usersApi = {
  getList: (params: {
    page?: number
    page_size?: number
    keyword?: string
    status?: string
    approval_status?: string
    domain?: string
    level?: string
  }) => api.get<PaginatedList<LearnerItem>>('/admin/users/list', params),

  getDetail: (learnerId: number) => api.get(`/admin/users/${learnerId}`),

  getLearningDetail: (learnerId: number) =>
    api.get(`/admin/users/${learnerId}/learning-detail`),
}
