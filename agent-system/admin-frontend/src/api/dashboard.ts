import { api } from './request'
import type { DashboardOverview } from '@/types/admin'

export const dashboardApi = {
  getOverview: () => api.get<DashboardOverview>('/admin/dashboard/overview'),

  getTrends: (days = 30) =>
    api.get('/admin/dashboard/trends', { days }),

  getDomainStats: () => api.get('/admin/dashboard/domain-stats'),
}
