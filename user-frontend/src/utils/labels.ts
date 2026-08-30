/** 能力等级 / 难度映射 */
export const LEVEL_MAP: Record<string, string> = {
  beginner: '初级',
  intermediate: '中级',
  advanced: '高级',
  expert: '专家',
}

/** 学习风格映射 */
export const LEARNING_STYLE_MAP: Record<string, string> = {
  visual: '视觉型',
  theory: '理论型',
  practice: '实践型',
}

/** 获取难度中文标签 */
export function difficultyLabel(d: string): string {
  return LEVEL_MAP[d] || d
}

/** 获取难度对应的样式类名 */
export function difficultyBadgeClass(d: string): string {
  const map: Record<string, string> = {
    beginner: 'badge--mute',
    intermediate: 'badge--accent',
    advanced: 'badge--warn',
    expert: 'badge--err',
  }
  return map[d] || 'badge--mute'
}
