/** 格式化百分比 */
export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`
}

/** 格式化日期 */
export function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** 审批状态映射 */
export const APPROVAL_STATUS_MAP: Record<string, { label: string; type: string }> = {
  none: { label: '未申请', type: 'default' },
  pending: { label: '审批中', type: 'warning' },
  approved: { label: '已批准', type: 'success' },
  rejected: { label: '未通过', type: 'error' },
}
