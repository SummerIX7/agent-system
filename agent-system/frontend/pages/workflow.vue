<template>
  <div class="container mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold mb-6">Agent 协同可视化</h1>

    <AgentViewAgentFlowChart :agents="agents" />

    <div class="mt-4 flex items-center gap-4">
      <UBadge :color="isConnected ? 'green' : 'red'" variant="subtle">
        {{ isConnected ? '已连接' : '未连接' }}
      </UBadge>
      <span class="text-sm text-gray-500">
        Session: {{ sessionId || '未设置' }}
      </span>
    </div>

    <!-- 真实进度条 -->
    <div v-if="generating" class="mt-6">
      <UCard>
        <div class="flex items-center gap-4">
          <UIcon
            :name="currentProgress >= 100 ? 'i-heroicons-check-circle' : 'i-heroicons-arrow-path'"
            class="w-6 h-6"
            :class="currentProgress >= 100 ? 'text-green-500' : 'animate-spin text-primary'"
          />
          <div class="flex-1">
            <p class="font-medium">
              {{ currentProgress >= 100 ? '生成完成！' : '正在生成个性化资源...' }}
            </p>
            <p class="text-sm text-gray-500 mt-1">{{ currentMessage }}</p>
          </div>
          <span class="text-lg font-bold text-primary">{{ Math.round(currentProgress) }}%</span>
        </div>
        <UProgress :value="currentProgress" class="mt-3" />
      </UCard>
    </div>

    <!-- 操作按钮 -->
    <div class="mt-8 flex flex-wrap justify-center gap-4">
      <UButton
        :disabled="!sessionId || generating"
        :loading="generating && currentProgress < 100"
        @click="startGenerate"
      >
        {{ generating ? (currentProgress >= 100 ? '生成完成' : '正在生成...') : '触发资源生成' }}
      </UButton>
      <UButton to="/resources" variant="outline" :disabled="generating && currentProgress < 100">
        查看生成结果
      </UButton>
    </div>
  </div>
</template>

<script setup lang="ts">
const { sessionId, profile } = useSession()
const api = useApi()
const toast = useToast()

// 真实进度和消息（来自 WebSocket）
const currentProgress = ref(0)
const currentMessage = ref('准备中...')
const generating = ref(false)

// WebSocket 连接
const { agents, isConnected } = useAgentWebSocket(sessionId.value || 'demo')

// 初始化 6 个 Agent 状态
if (agents.value.length === 0) {
  agents.value = [
    { name: '学情分析 Agent', status: 'idle', message: '等待启动', progress: 0 },
    { name: '路径规划 Agent', status: 'idle', message: '等待启动', progress: 0 },
    { name: '知识生成 Agent', status: 'idle', message: '等待启动', progress: 0 },
    { name: '审核纠偏 Agent', status: 'idle', message: '等待启动', progress: 0 },
    { name: '裁判 Agent', status: 'idle', message: '等待启动', progress: 0 },
    { name: '试题生成 Agent', status: 'idle', message: '等待启动', progress: 0 },
    { name: '决策调度 Agent', status: 'idle', message: '等待启动', progress: 0 },
  ]
}

// 监听 WebSocket 消息，更新真实进度
watch(() => agents.value, (newAgents) => {
  // 找到当前最高进度
  let maxProgress = 0
  let latestMessage = ''

  for (const agent of newAgents) {
    if (agent.progress > maxProgress) {
      maxProgress = agent.progress
      latestMessage = agent.message
    }
    // 如果有正在运行的 agent，显示其消息
    if (agent.status === 'running') {
      latestMessage = agent.message
    }
  }

  currentProgress.value = maxProgress
  if (latestMessage) {
    currentMessage.value = latestMessage
  }
}, { deep: true })

const startGenerate = async () => {
  if (!sessionId.value) return

  generating.value = true
  currentProgress.value = 0
  currentMessage.value = '启动工作流...'

  // 重置所有 Agent 状态为 idle
  agents.value = agents.value.map(a => ({ ...a, status: 'idle' as const, message: '等待启动', progress: 0 }))

  try {
    const result = await api.generateResources(
      sessionId.value,
      'Python 数据分析基础',
      ['lecture', 'guide', 'project'],
      profile.value || {}
    )

    // 确保进度显示 100%
    currentProgress.value = 100
    currentMessage.value = `已生成 ${result.length} 个资源`

    toast.add({
      title: '生成成功',
      description: `已生成 ${result.length} 个资源`,
      color: 'green',
    })
  } catch (err: any) {
    console.error('生成失败:', err)
    toast.add({
      title: '生成失败',
      description: err.message || '请稍后重试',
      color: 'red',
    })
  } finally {
    // 延迟关闭，让用户看到 100% 完成状态
    setTimeout(() => {
      generating.value = false
    }, 2000)
  }
}
</script>
