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

    <!-- 生成进度提示 -->
    <div v-if="generating" class="mt-6">
      <UCard>
        <div class="flex items-center gap-4">
          <UIcon name="i-heroicons-arrow-path" class="w-6 h-6 animate-spin text-primary" />
          <div class="flex-1">
            <p class="font-medium">正在生成个性化资源...</p>
            <p class="text-sm text-gray-500 mt-1">{{ progressMessage }}</p>
          </div>
        </div>
        <UProgress :value="progress" class="mt-3" />
      </UCard>
    </div>

    <!-- 操作按钮 -->
    <div class="mt-8 flex flex-wrap justify-center gap-4">
      <UButton
        :disabled="!sessionId || generating"
        :loading="generating"
        @click="startGenerate"
      >
        {{ generating ? '正在生成...' : '触发资源生成' }}
      </UButton>
      <UButton to="/resources" variant="outline" :disabled="generating">
        查看生成结果
      </UButton>
    </div>
  </div>
</template>

<script setup lang="ts">
const { sessionId, profile } = useSession()
const api = useApi()
const toast = useToast()

// WebSocket 连接
const { agents, isConnected } = useAgentWebSocket(sessionId.value || 'demo')

// 如果没有 WebSocket 数据，显示 6 个 Agent 初始状态
if (agents.value.length === 0) {
  agents.value = [
    { name: '学情分析 Agent', status: 'idle', message: '等待启动', progress: 0 },
    { name: '路径规划 Agent', status: 'idle', message: '等待启动', progress: 0 },
    { name: '知识生成 Agent', status: 'idle', message: '等待启动', progress: 0 },
    { name: '审核纠偏 Agent', status: 'idle', message: '等待启动', progress: 0 },
    { name: '试题生成 Agent', status: 'idle', message: '等待启动', progress: 0 },
    { name: '决策调度 Agent', status: 'idle', message: '等待启动', progress: 0 },
  ]
}

const generating = ref(false)
const progress = ref(0)
const progressMessage = ref('准备中...')

// 模拟进度更新
const progressMessages = [
  '学情分析 Agent 正在构建学习者画像...',
  '路径规划 Agent 正在规划学习路径...',
  '知识生成 Agent 正在生成个性化内容...',
  '审核纠偏 Agent 正在验证内容准确性...',
  '试题生成 Agent 正在生成练习题...',
  '决策调度 Agent 正在整合结果...',
]

const startGenerate = async () => {
  if (!sessionId.value) return

  generating.value = true
  progress.value = 0
  progressMessage.value = progressMessages[0]

  // 模拟进度更新
  const progressInterval = setInterval(() => {
    if (progress.value < 90) {
      progress.value += 15
      const msgIndex = Math.min(Math.floor(progress.value / 18), progressMessages.length - 1)
      progressMessage.value = progressMessages[msgIndex]
    }
  }, 2000)

  try {
    const result = await api.generateResources(
      sessionId.value,
      'Python 数据分析基础',
      ['lecture', 'guide', 'project'],
      profile.value || {}
    )
    progress.value = 100
    progressMessage.value = '生成完成！'

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
    clearInterval(progressInterval)
    generating.value = false
  }
}
</script>
