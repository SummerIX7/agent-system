import { api } from './request'

export interface KbFileItem {
  path: string
  name: string
  domain: string
  category: string
  size: number
  title: string
}

export const knowledgeApi = {
  getList: () => api.get<{ files: KbFileItem[] }>('/admin/knowledge/list'),

  readFile: (path: string) =>
    api.get<{ path: string; content: string }>('/admin/knowledge/read', { path }),

  writeFile: (path: string, content: string) =>
    api.post<{ message: string }>('/admin/knowledge/write', { content }, { path }),

  deleteFile: (path: string) =>
    api.delete<{ message: string }>('/admin/knowledge/delete', { path }),

  rebuildIndex: () =>
    api.post<{ ok: boolean; total_chunks: number; message: string }>('/admin/knowledge/rebuild-index'),
}
