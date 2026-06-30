<template>
  <div class="page page--wide">
    <div class="page-head">
      <p class="page-head__eyebrow">Step 3</p>
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
      <span class="t2">Session: <span class="mono">{{ sessionId || '未设置' }}</span></span>
      <span style="margin-left: auto" :class="['badge', generating ? (currentProgress >= 100 ? 'badge--ok' : 'badge--accent') : 'badge--mute']">
        {{ generating ? (currentProgress >= 100 ? '生成完成' : '生成中...') : '等待触发' }}
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

    <!-- 调试面板 -->
    <div v-if="debugLogs.length > 0" class="debug-panel">
      <div class="debug-header" @click="debugOpen = !debugOpen">
        <span>🔍 决策调试日志（{{ debugLogs.length }} 条）</span>
        <span style="font-size:12px;color:var(--text-3)">{{ debugOpen ? '收起 ▲' : '展开 ▼' }}</span>
      </div>
      <div v-if="debugOpen" class="debug-body">
        <div v-for="(log, i) in debugLogs" :key="i" class="debug-entry">
          <div class="debug-entry__head">
            <span :class="['badge', log.status === 'completed' ? 'badge--ok' : log.status === 'error' ? 'badge--err' : 'badge--accent']">
              {{ log.agent_name }}
            </span>
            <span class="t2" style="font-size:12px">{{ log.status }}</span>
          </div>
          <pre class="debug-entry__msg">{{ log.message }}</pre>
        </div>
      </div>
    </div>

    <div style="display: flex; gap: 12px; justify-content: center; margin-top: 32px">
      <button
        class="btn btn--primary btn--lg"
        :disabled="!sessionId || generating"
        @click="startGenerate"
      >
        {{ generating ? (currentProgress >= 100 ? '生成完成' : '正在生成...') : '触发资源生成' }}
      </button>
      <NuxtLink to="/resources" class="btn btn--ghost btn--lg" :class="{ 'opacity-50 pointer-events-none': generating && currentProgress < 100 }">
        查看生成结果 →
      </NuxtLink>
      <NuxtLink :to="`/trace?sessionId=${sessionId}`" class="btn btn--ghost btn--lg" style="font-size:13px">
        🔍 查看完整追踪
      </NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
const { sessionId, profile } = useSession()
const api = useApi()
const toast = useToast()

// 调试日志
const debugOpen = ref(false)
const debugLogs = ref<any[]>([])

// 真实进度和消息（来自 WebSocket）
const currentProgress = ref(0)
const currentMessage = ref('准备中...')
const generating = ref(false)

// Bug#10 修复：未登录时 WebSocket 使用空字符串避免路由歧义，
// 仅在有有效 sessionId 时才建立真实连接
const { agents, isConnected } = useAgentWebSocket(sessionId.value || '')

// 初始化 6 个 Agent 状态
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
  if (!sessionId.value) return

  generating.value = true
  currentProgress.value = 0
  currentMessage.value = '启动工作流...'
  debugLogs.value = []

  // 重置所有 Agent 状态为 idle
  agents.value = agents.value.map(a => ({ ...a, status: 'idle' as const, message: '等待启动', progress: 0 }))

  try {
    // 从画像中获取学习目标作为主题，或以画像推荐难度对应的领域主题
    const goals = profile.value?.goals || []
    const topic = goals.length > 0 ? goals[0] : (profile.value?.knowledge_points?.[0]?.name || '基础知识')
    const result = await api.generateResources(
      sessionId.value,
      topic,
      ['lecture', 'guide', 'project'],
      profile.value || {}
    )

    currentProgress.value = 100
    currentMessage.value = `已生成 ${result.length} 个资源`

    // 拉取调试日志
    await fetchDebugLogs()

    toast.add({
      title: '生成成功',
      description: `已生成 ${result.length} 个资源`,
      color: 'green',
    })
  } catch (err: any) {
    console.error('生成失败:', err)
    await fetchDebugLogs()  // 失败也拉日志
    toast.add({
      title: '生成失败',
      description: err.message || '请稍后重试',
      color: 'red',
    })
  } finally {
    setTimeout(() => {
      generating.value = false
    }, 2000)
  }
}

const fetchDebugLogs = async () => {
  if (!sessionId.value) return
  try {
    const config = useRuntimeConfig()
    const data = await $fetch(`${config.public.apiBase}/api/trace/${sessionId.value}`)
    debugLogs.value = (data as any).agent_logs || []
    if (debugLogs.value.length > 0) {
      debugOpen.value = true
    }
  } catch (e) {
    console.error('调试日志获取失败:', e)
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

/* 调试面板 */
.debug-panel {
  margin-top: 24px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  overflow: hidden;
}
.debug-header {
  padding: 12px 20px;
  background: var(--bg-soft);
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  font-size: 14px;
  user-select: none;
}
.debug-header:hover {
  background: var(--bg-muted);
}
.debug-body {
  padding: 16px;
  max-height: 480px;
  overflow-y: auto;
}
.debug-entry {
  margin-bottom: 14px;
  border-bottom: 1px solid var(--line);
  padding-bottom: 14px;
}
.debug-entry:last-child {
  margin-bottom: 0;
  border-bottom: none;
  padding-bottom: 0;
}
.debug-entry__head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.debug-entry__msg {
  font-size: 12.5px;
  font-family: var(--mono);
  color: var(--text-2);
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-all;
  background: var(--bg-soft);
  padding: 12px;
  border-radius: 6px;
  margin: 0;
}

@media (max-width: 760px) {
  .agent-grid { grid-template-columns: 1fr; }
}
</style>
