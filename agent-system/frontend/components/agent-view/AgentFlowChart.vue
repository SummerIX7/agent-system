<template>
  <div class="flex flex-col gap-4">
    <div
      v-for="agent in agents"
      :key="agent.name"
      class="flex items-center gap-4 p-4 rounded-lg border transition-all"
      :class="statusClass(agent.status)"
    >
      <!-- 状态图标 -->
      <div
        class="w-10 h-10 rounded-full flex items-center justify-center"
        :class="iconBgClass(agent.status)"
      >
        <UIcon :name="statusIcon(agent.status)" class="w-5 h-5" :class="iconClass(agent.status)" />
      </div>

      <!-- Agent 信息 -->
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2">
          <h3 class="font-semibold text-sm">{{ agent.name }}</h3>
          <UBadge
            :color="badgeColor(agent.status)"
            variant="subtle"
            size="xs"
          >
            {{ statusLabel(agent.status) }}
          </UBadge>
        </div>
        <p class="text-sm text-gray-500 mt-0.5 truncate">{{ agent.message }}</p>
      </div>

      <!-- 进度条 -->
      <div class="w-32">
        <UProgress
          :value="agent.progress"
          :color="agent.status === 'error' ? 'red' : 'primary'"
          size="sm"
        />
        <p class="text-xs text-gray-400 text-right mt-1">{{ agent.progress }}%</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
export interface AgentStatus {
  name: string
  status: 'idle' | 'running' | 'completed' | 'error'
  message: string
  progress: number
}

defineProps<{
  agents: AgentStatus[]
}>()

const statusClass = (status: string) => ({
  'border-gray-200 bg-white': status === 'idle',
  'border-blue-300 bg-blue-50': status === 'running',
  'border-green-300 bg-green-50': status === 'completed',
  'border-red-300 bg-red-50': status === 'error',
})

const iconBgClass = (status: string) => ({
  'bg-gray-100': status === 'idle',
  'bg-blue-100': status === 'running',
  'bg-green-100': status === 'completed',
  'bg-red-100': status === 'error',
})

const iconClass = (status: string) => ({
  'text-gray-500': status === 'idle',
  'text-blue-600': status === 'running',
  'text-green-600': status === 'completed',
  'text-red-600': status === 'error',
})

const statusIcon = (status: string): string => {
  const icons: Record<string, string> = {
    idle: 'i-heroicons-clock',
    running: 'i-heroicons-arrow-path',
    completed: 'i-heroicons-check-circle',
    error: 'i-heroicons-exclamation-triangle',
  }
  return icons[status] || 'i-heroicons-question-mark-circle'
}

const statusLabel = (status: string): string => {
  const labels: Record<string, string> = {
    idle: '空闲',
    running: '运行中',
    completed: '已完成',
    error: '错误',
  }
  return labels[status] || status
}

const badgeColor = (status: string): string => {
  const colors: Record<string, string> = {
    idle: 'gray',
    running: 'blue',
    completed: 'green',
    error: 'red',
  }
  return colors[status] || 'gray'
}
</script>
