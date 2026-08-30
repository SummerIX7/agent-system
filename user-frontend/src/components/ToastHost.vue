<script setup lang="ts">
import { useToast } from '@/composables/useToast'

const { toasts } = useToast()

// 原页面使用的 color 取值：primary / orange / green / red → 映射到设计系统语义色
const colorClass = (color?: string): string => {
  const map: Record<string, string> = {
    primary: 'toast--accent',
    orange: 'toast--warn',
    green: 'toast--ok',
    red: 'toast--err',
  }
  return map[color || ''] || 'toast--accent'
}
</script>

<template>
  <Teleport to="body">
    <div class="toast-host">
      <TransitionGroup name="toast">
        <div v-for="t in toasts" :key="t.id" class="toast-item" :class="colorClass(t.color)">
          <div class="toast-item__title">{{ t.title }}</div>
          <div v-if="t.description" class="toast-item__desc">{{ t.description }}</div>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-host {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 10px;
  pointer-events: none;
}

.toast-item {
  min-width: 240px;
  max-width: 360px;
  padding: 12px 16px;
  border-radius: var(--radius);
  background: var(--bg);
  border: 1px solid var(--line);
  border-left-width: 3px;
  box-shadow: 0 8px 24px rgba(17, 24, 39, .10);
}

.toast-item__title {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text);
}

.toast-item__desc {
  font-size: 12.5px;
  color: var(--text-2);
  margin-top: 4px;
  line-height: 1.6;
}

.toast--accent { border-left-color: var(--accent); }
.toast--warn   { border-left-color: var(--warn); }
.toast--ok     { border-left-color: var(--ok); }
.toast--err    { border-left-color: var(--err); }

.toast-enter-active,
.toast-leave-active {
  transition: all .25s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(16px);
}
</style>
