<template>
  <div class="page page--wide">
    <div class="page-head">
      <p class="page-head__eyebrow">步骤 3</p>
      <h1 class="page-head__title">Agent 协同</h1>
      <p class="page-head__desc">实时查看6个AI Agent的协同工作状态，从学情分析到试题生成的完整流程。</p>
    </div>

    <!-- 连接状态 -->
    <div class="conn-bar">
      <span :class="['dot', isConnected ? 'dot--ok' : 'dot--err']" style="width: 8px; height: 8px"></span>
      <span :style="{ color: isConnected ? 'var(--ok)' : 'var(--err)', fontWeight: 500 }">
        {{ isConnected ? '实时已连接' : '未连接' }}
      </span>
      <span class="muted">·</span>
      <span class="t2">会话: <span class="mono">{{ sessionId || '未设置' }}</span></span>
      <span style="margin-left: auto" :class="['badge', hasExistingResources ? 'badge--ok' : generating ? (currentProgress >= 100 ? 'badge--ok' : 'badge--accent') : 'badge--mute']">
        {{ hasExistingResources ? '已有资源' : generating ? (currentProgress >= 100 ? '生成完成' : '生成中...') : '等待触发' }}
      </span>
    </div>

    <!-- 生成进度 -->
    <div v-if="generating" class="gen-box">
      <div class="gen-box__icon">
        <svg v-if="currentProgress >= 100" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5"/></svg>
        <svg v-else width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="animate-spin"><path d="M12 2v4m0 12v4m-7.07-3.93l2.83-2.83m8.48-8.48l2.83-2.83M2 12h4m12 0h4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83"/></svg>
      </div>
      <div style="flex: 1">
        <div style="font-size: 14px; font-weight: 600">
          {{ currentProgress >= 100 ? '生成完成！' : '正在生成个性化资源...' }}
        </div>
        <div style="font-size: 13px; color: var(--text-2); margin-top: 4px">{{ currentMessage }}</div>
      </div>
      <div style="font-size: 22px; font-weight: 600; font-family: var(--mono); color: var(--accent)">{{ Math.round(currentProgress) }}%</div>
    </div>

    <!-- Agent 状态列表 -->
    <div class="agent-grid">
      <div
        v-for="(agent, idx) in agents"
        :key="idx"
        class="agent-card"
        :class="agent.status"
      >
        <div class="agent-card__icon" :class="agent.status">
          {{ String(idx + 1).padStart(2, '0') }}
        </div>
        <div style="flex: 1; min-width: 0">
          <div style="font-size: 14px; font-weight: 600; display: flex; align-items: center; gap: 8px">
            {{ agent.name }}
            <span :class="['badge', getStatusBadgeClass(agent.status)]">{{ getStatusText(agent.status) }}</span>
          </div>
          <div style="font-size: 12.5px; color: var(--text-2); margin-top: 3px">{{ agent.message }}</div>
        </div>
        <div style="width: 130px; flex-shrink: 0">
          <div class="bar"><div class="bar__fill" :class="getBarClass(agent.status)" :style="{ width: agent.progress + '%' }"></div></div>
          <div style="font-size: 12px; color: var(--text-3); text-align: right; margin-top: 4px; font-family: var(--mono)">{{ agent.progress }}%</div>
        </div>
      </div>
    </div>

    <div style="display: flex; gap: 12px; justify-content: center; margin-top: 32px">
      <button
        class="btn btn--primary btn--lg"
        :disabled="!sessionId || generating || checkingResources"
        @click="startGenerate"
      >
        {{ checkingResources ? '检查中...' : generating ? (currentProgress >= 100 ? '生成完成' : '正在生成...') : hasExistingResources ? '重新生成资源' : '触发资源生成' }}
      </button>
      <NuxtLink to="/report" class="btn btn--ghost btn--lg" :class="{ 'opacity-50 pointer-events-none': generating && currentProgress < 100 }">
        查看学习报告 →
      </NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
// 保持页面状态：避免每次切换都重新初始化 agent 并触发 WS 重连
definePageMeta({ keepalive: true })

const { sessionId, profile } = useSession()
const api = useApi()

const currentProgress = ref(0)
const currentMessage = ref('准备中...')
const generating = ref(false)
const hasExistingResources = ref(false)
const checkingResources = ref(true)

const { agents, isConnected } = useAgentWebSocket(sessionId.value || 'demo')

function initAgents() {
  agents.value = [
    { name: '学情分析 Agent', status: 'idle', message: '等待启动', progress: 0 },
    { name: '路径规划 Agent', status: 'idle', message: '等待启动', progress: 0 },
    { name: '知识生成 Agent', status: 'idle', message: '等待启动', progress: 0 },
    { name: '审核纠偏 Agent', status: 'idle', message: '等待启动', progress: 0 },
    { name: '试题生成 Agent', status: 'idle', message: '等待启动', progress: 0 },
    { name: '决策调度 Agent', status: 'idle', message: '等待启动', progress: 0 },
  ]
}

if (agents.value.length === 0) {
  initAgents()
}

// 页面加载时检查是否已有资源，有则恢复完成状态
async function checkExistingResources() {
  if (!sessionId.value) {
    checkingResources.value = false
    return
  }
  try {
    const resources = await api.getResources(sessionId.value)
    if (resources && resources.length > 0) {
      hasExistingResources.value = true
      currentProgress.value = 100
      currentMessage.value = `已有 ${resources.length} 个资源（无需重新生成）`
      // 恢复 Agent 完成状态
      agents.value = agents.value.map((a, i) => ({
        ...a,
        status: 'completed' as const,
        message: ['学情分析完成', '路径规划完成', '知识生成完成', '审核纠偏完成', '试题生成完成', '决策调度完成'][i] || '已完成',
        progress: 100,
      }))
    }
  } catch {
    // 忽略，可能没有资源
  } finally {
    checkingResources.value = false
  }
}

onMounted(() => {
  checkExistingResources()
})

// 获取状态徽章样式
const getStatusBadgeClass = (status: string): string => {
  const map: Record<string, string> = {
    idle: 'badge--mute',
    running: 'badge--accent',
    completed: 'badge--ok',
    error: 'badge--err',
  }
  return map[status] || 'badge--mute'
}

// 获取状态文本
const getStatusText = (status: string): string => {
  const map: Record<string, string> = {
    idle: '等待中',
    running: '运行中',
    completed: '已完成',
    error: '出错',
  }
  return map[status] || '未知'
}

// 获取进度条样式
const getBarClass = (status: string): string => {
  if (status === 'completed') return 'ok'
  if (status === 'running') return ''
  return ''
}

// 监听 WebSocket 消息，更新真实进度
watch(() => agents.value, (newAgents) => {
  let maxProgress = 0
  let latestMessage = ''

  for (const agent of newAgents) {
    if (agent.progress > maxProgress) {
      maxProgress = agent.progress
      latestMessage = agent.message
    }
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
  if (!sessionId.value || generating.value) return

  generating.value = true
  currentProgress.value = 0
  currentMessage.value = '启动工作流...'
  hasExistingResources.value = false

  // 重置 agent 状态
  initAgents()

  try {
    const goals = profile.value?.goals || []
    const topic = goals.length > 0 ? goals[0] : (profile.value?.knowledge_points?.[0]?.name || '基础知识')
    const result = await api.generateResources(
      sessionId.value,
      topic,
      ['lecture', 'guide', 'project'],
      profile.value || {}
    )

    currentProgress.value = 100
    const resourceCount = result.filter((r: any) => ['lecture', 'guide', 'project'].includes(r.type)).length
    currentMessage.value = `已生成 ${resourceCount} 个资源（覆盖 5 个学习节点）`
    hasExistingResources.value = true
  } catch (err: any) {
    currentMessage.value = `生成失败: ${err.message || '未知错误'}`
    console.error('生成失败:', err)
  } finally {
    setTimeout(() => {
      generating.value = false
    }, 2000)
  }
}
</script>

<style scoped>
.conn-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 20px;
  background: var(--bg-soft);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  margin-bottom: 32px;
  font-size: 13px;
}
.gen-box {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 24px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  margin-bottom: 24px;
}
.gen-box__icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: var(--accent-soft);
  color: var(--accent);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.agent-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}
.agent-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 18px 20px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  transition: border-color .15s, background .15s;
}
.agent-card:hover {
  border-color: var(--line-2);
  background: var(--bg-soft);
}
.agent-card.running {
  border-color: #C7D2FE;
  background: var(--accent-soft);
}
.agent-card.completed {
  border-color: #A7F3D0;
  background: var(--ok-soft);
}
.agent-card__icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--mono);
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}
.agent-card__icon.idle { background: var(--bg-muted); color: var(--text-3); }
.agent-card__icon.running { background: #fff; color: var(--accent); }
.agent-card__icon.completed { background: var(--ok-soft); color: var(--ok); }
.agent-card__icon.error { background: var(--err-soft); color: var(--err); }

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.animate-spin {
  animation: spin 1s linear infinite;
}

@media (max-width: 760px) {
  .agent-grid { grid-template-columns: 1fr; }
}
</style>
