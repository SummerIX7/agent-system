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

    <!-- 操作按钮 -->
    <div class="mt-8 flex justify-center gap-4">
      <UButton
        :disabled="!sessionId"
        :loading="generating"
        @click="startGenerate"
      >
        {{ generating ? '正在生成...' : '触发资源生成' }}
      </UButton>
      <UButton to="/resources" variant="outline">
        查看生成结果
      </UButton>
    </div>
  </div>
</template>

<script setup lang="ts">
const { sessionId, profile } = useSession()
const api = useApi()

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

const startGenerate = async () => {
  if (!sessionId.value) return

  generating.value = true
  try {
    // 传入画像数据，让 Agent 生成个性化内容
    const result = await api.generateResources(
      sessionId.value,
      'Python 数据分析基础',
      ['lecture', 'guide', 'project'],
      profile.value || {}
    )
    console.log('生成完成:', result)
  } catch (err: any) {
    console.error('生成失败:', err)
    alert(`生成失败: ${err.message}`)
  } finally {
    generating.value = false
  }
}
</script>
