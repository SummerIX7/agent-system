import { api } from './request'
import type { LearnerItem, ApprovalLog, PaginatedList } from '@/types/admin'

export const approvalApi = {
  approve: (learnerId: number, reason?: string) =>
    api.post(`/admin/approval/${learnerId}/approve`, { reason }),

  reject: (learnerId: number, reason: string) =>
    api.post(`/admin/approval/${learnerId}/reject`, { reason }),

  getPending: (page = 1, page_size = 20) =>
    api.get<PaginatedList<LearnerItem>>('/admin/approval/pending', { page, page_size }),

  getLogs: (params: {
    learner_id?: number
    action?: string
    page?: number
    page_size?: number
  }) => api.get<PaginatedList<ApprovalLog>>('/admin/approval/logs', params),
}
