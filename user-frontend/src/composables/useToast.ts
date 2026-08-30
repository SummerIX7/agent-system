/**
 * 极简 Toast 通知（替代原 @nuxt/ui 的 useToast，签名兼容 toast.add）
 * 模块级单例，配合 components/ToastHost.vue 展示
 */
import { ref } from 'vue'

export interface ToastItem {
  id: number
  title: string
  description?: string
  color?: string
}

// 模块级单例
const toasts = ref<ToastItem[]>([])
let seq = 0

export function useToast() {
  const add = (toast: { title: string; description?: string; color?: string }) => {
    const id = ++seq
    toasts.value.push({ id, ...toast })
    setTimeout(() => {
      toasts.value = toasts.value.filter(t => t.id !== id)
    }, 3800)
  }

  return { add, toasts }
}
