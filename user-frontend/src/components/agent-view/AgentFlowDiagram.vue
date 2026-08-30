<template>
  <svg
    viewBox="0 0 780 510"
    xmlns="http://www.w3.org/2000/svg"
    class="agent-flow-diagram"
  >
    <defs>
      <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
        <path d="M0,0 L10,5 L0,10" fill="none" stroke="#9CA3AF" stroke-width="1.4"/>
      </marker>
      <marker id="arrActive" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
        <path d="M0,0 L10,5 L0,10" fill="none" stroke="#4F46E5" stroke-width="1.4"/>
      </marker>
      <marker id="arrCompleted" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
        <path d="M0,0 L10,5 L0,10" fill="none" stroke="#059669" stroke-width="1.4"/>
      </marker>
    </defs>

    <!-- ========== 决策调度 Agent ========== -->
    <g :class="['agent-node', getAgentStatusClass('dispatcher')]">
      <rect x="240" y="12" width="200" height="46" rx="10"
        :fill="getAgentFill('dispatcher')" :stroke="getAgentStroke('dispatcher')" stroke-width="1.5"/>
      <circle cx="262" cy="35" r="4" :fill="getAgentDotColor('dispatcher')"/>
      <text x="274" y="32" font-family="sans-serif" font-size="13" font-weight="600" fill="#111827">决策调度 Agent</text>
      <text x="274" y="48" font-family="sans-serif" font-size="10.5" fill="#9CA3AF">{{ getAgentDescription('dispatcher') }}</text>
      <rect v-if="getAgentStatus('dispatcher') === 'running'" x="240" y="54" width="200" height="3" rx="1.5" fill="#E5E7EB"/>
      <rect v-if="getAgentStatus('dispatcher') === 'running'" x="240" y="54" :width="getAgentProgress('dispatcher') * 2" height="3" rx="1.5" fill="#4F46E5" class="progress-bar"/>
    </g>

    <!-- 决策调度 → 学情分析 -->
    <line x1="340" y1="58" x2="340" y2="84"
      :stroke="getConnectionColor('dispatcher', 'analyzer')" stroke-width="1.4"
      :marker-end="getConnectionMarker('dispatcher', 'analyzer')"
      :class="{ 'flowing-line': isConnectionActive('dispatcher', 'analyzer') }"/>

    <!-- ========== 学情分析 Agent ========== -->
    <g :class="['agent-node', getAgentStatusClass('analyzer')]">
      <rect x="240" y="86" width="200" height="46" rx="10"
        :fill="getAgentFill('analyzer')" :stroke="getAgentStroke('analyzer')" stroke-width="1"/>
      <circle cx="262" cy="109" r="4" :fill="getAgentDotColor('analyzer')"/>
      <text x="274" y="106" font-family="sans-serif" font-size="13" font-weight="600" fill="#111827">学情分析 Agent</text>
      <text x="274" y="122" font-family="sans-serif" font-size="10.5" fill="#9CA3AF">{{ getAgentDescription('analyzer') }}</text>
    </g>

    <!-- 学情分析 → 路径规划 -->
    <line x1="340" y1="132" x2="340" y2="158"
      :stroke="getConnectionColor('analyzer', 'planner')" stroke-width="1.4"
      :marker-end="getConnectionMarker('analyzer', 'planner')"
      :class="{ 'flowing-line': isConnectionActive('analyzer', 'planner') }"/>

    <!-- ========== 路径规划 Agent ========== -->
    <g :class="['agent-node', getAgentStatusClass('planner')]">
      <rect x="240" y="160" width="200" height="46" rx="10"
        :fill="getAgentFill('planner')" :stroke="getAgentStroke('planner')" stroke-width="1"/>
      <circle cx="262" cy="183" r="4" :fill="getAgentDotColor('planner')"/>
      <text x="274" y="180" font-family="sans-serif" font-size="13" font-weight="600" fill="#111827">路径规划 Agent</text>
      <text x="274" y="196" font-family="sans-serif" font-size="10.5" fill="#9CA3AF">{{ getAgentDescription('planner') }}</text>
    </g>

    <!-- 路径规划 → 知识生成（左侧入口） -->
    <path d="M 340 206 L 340 272 L 190 272 L 190 290" fill="none"
      :stroke="getConnectionColor('planner', 'generator')" stroke-width="1.4"
      :marker-end="getConnectionMarker('planner', 'generator')"
      :class="{ 'flowing-line': isConnectionActive('planner', 'generator') }"/>

    <!-- ========== 审核纠偏机制虚线框 ========== -->
    <rect x="50" y="232" width="680" height="160" rx="12"
      fill="none" stroke="#4F46E5" stroke-width="1.2" stroke-dasharray="5 4" opacity=".55"/>
    <text x="70" y="254" font-family="sans-serif" font-size="11" font-weight="600" fill="#4F46E5" letter-spacing=".04em">
      双视角审核纠偏机制 · 降低知识谬误率
    </text>

    <!-- ========== 知识生成 Agent ========== -->
    <g :class="['agent-node', getAgentStatusClass('generator')]">
      <rect x="95" y="290" width="190" height="52" rx="10"
        :fill="getAgentFill('generator')" :stroke="getAgentStroke('generator')" stroke-width="1"/>
      <circle cx="117" cy="316" r="4" :fill="getAgentDotColor('generator')"/>
      <text x="129" y="312" font-family="sans-serif" font-size="13" font-weight="600" fill="#111827">知识生成 Agent</text>
      <text x="129" y="330" font-family="sans-serif" font-size="10.5" fill="#9CA3AF">{{ getAgentDescription('generator') }}</text>
    </g>

    <!-- 知识生成 → 审核纠偏 -->
    <line x1="285" y1="316" x2="349" y2="316"
      :stroke="getConnectionColor('generator', 'reviewer')" stroke-width="1.4"
      :marker-end="getConnectionMarker('generator', 'reviewer')"
      :class="{ 'flowing-line': isConnectionActive('generator', 'reviewer') }"/>
    <text x="317" y="308" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#4F46E5">提交审核</text>

    <!-- ========== 审核纠偏 Agent（合并原预审+辩论+裁判） ========== -->
    <g :class="['agent-node', getAgentStatusClass('reviewer')]">
      <rect x="355" y="290" width="210" height="52" rx="10"
        :fill="getAgentFill('reviewer')" :stroke="getAgentStroke('reviewer')" stroke-width="1"/>
      <circle cx="377" cy="316" r="4" :fill="getAgentDotColor('reviewer')"/>
      <text x="389" y="312" font-family="sans-serif" font-size="13" font-weight="600" fill="#111827">审核纠偏 Agent</text>
      <text x="389" y="330" font-family="sans-serif" font-size="10.5" fill="#9CA3AF">{{ getAgentDescription('reviewer') }}</text>
    </g>

    <!-- 审核纠偏通过 → 试题生成 -->
    <path d="M 460 342 L 460 382 L 435 382 L 435 424" fill="none"
      :stroke="getConnectionColor('reviewer', 'quiz')" stroke-width="1.4"
      :marker-end="getConnectionMarker('reviewer', 'quiz')"
      :class="{ 'flowing-line': isConnectionActive('reviewer', 'quiz') }"/>
    <text x="468" y="386" font-family="sans-serif" font-size="10.5" fill="#059669">审核通过</text>

    <!-- 审核纠偏驳回 → 知识生成（回环重试） -->
    <path d="M 420 342 C 420 374, 190 374, 190 344" fill="none"
      :stroke="getLoopConnectionColor('reviewer', 'generator')" stroke-width="1.4"
      stroke-dasharray="4 3"
      :marker-end="getLoopConnectionMarker('reviewer', 'generator')"
      :class="{ 'flowing-line': isLoopConnectionActive('reviewer', 'generator') }"/>
    <text x="305" y="370" text-anchor="middle" font-family="sans-serif" font-size="10.5" fill="#DC2626">
      未通过 → 重新生成
    </text>

    <!-- ========== 试题生成 Agent ========== -->
    <g :class="['agent-node', getAgentStatusClass('quiz')]">
      <rect x="340" y="424" width="190" height="46" rx="10"
        :fill="getAgentFill('quiz')" :stroke="getAgentStroke('quiz')" stroke-width="1.5"/>
      <circle cx="362" cy="447" r="4" :fill="getAgentDotColor('quiz')"/>
      <text x="374" y="444" font-family="sans-serif" font-size="13" font-weight="600" fill="#111827">试题生成 Agent</text>
      <text x="374" y="460" font-family="sans-serif" font-size="10.5" fill="#9CA3AF">{{ getAgentDescription('quiz') }}</text>
    </g>
  </svg>
</template>

<script setup lang="ts">
import { useAgentWebSocket } from '@/composables/useAgentWebSocket'
import { useSession } from '@/composables/useSession'

const { sessionId } = useSession()
const { agents, isConnected } = useAgentWebSocket(sessionId.value || 'demo')

// Agent ID 映射（与后端 WebSocket 广播名称对应）
// 值与后端 WebSocket 实际广播的 agent 名称一一对应（见 graph/nodes/_common.py 的 _broadcast 调用）
const AGENT_MAP: Record<string, string> = {
  dispatcher: '决策调度 Agent',
  analyzer: '学情分析 Agent',
  planner: '路径规划 Agent',
  generator: '知识生成 Agent',
  reviewer: '审核纠偏 Agent',
  quiz: '试题生成 Agent',
}

// ========== 状态计算函数 ==========

const getAgentStatus = (agentId: string): string => {
  const realId = AGENT_MAP[agentId]
  const agent = agents.value.find(a => a.name === realId)
  return agent?.status || 'idle'
}

const getAgentProgress = (agentId: string): number => {
  const realId = AGENT_MAP[agentId]
  const agent = agents.value.find(a => a.name === realId)
  return agent?.progress || 0
}

const getAgentStatusClass = (agentId: string): string => {
  return `status-${getAgentStatus(agentId)}`
}

const getAgentFill = (agentId: string): string => {
  const status = getAgentStatus(agentId)
  const colorMap: Record<string, string> = {
    idle: '#FFFFFF',
    running: '#EEF2FF',
    completed: '#ECFDF5',
    error: '#FEF2F2',
    paused: '#FFFBEB',
  }
  return colorMap[status] || colorMap.idle
}

const getAgentStroke = (agentId: string): string => {
  const status = getAgentStatus(agentId)
  const colorMap: Record<string, string> = {
    idle: '#E5E7EB',
    running: '#4F46E5',
    completed: '#059669',
    error: '#DC2626',
    paused: '#D97706',
  }
  return colorMap[status] || colorMap.idle
}

const getAgentDotColor = (agentId: string): string => {
  const status = getAgentStatus(agentId)
  const colorMap: Record<string, string> = {
    idle: '#9CA3AF',
    running: '#4F46E5',
    completed: '#059669',
    error: '#DC2626',
    paused: '#D97706',
  }
  return colorMap[status] || colorMap.idle
}

const getAgentDescription = (agentId: string): string => {
  const status = getAgentStatus(agentId)
  const realId = AGENT_MAP[agentId]
  const agent = agents.value.find(a => a.name === realId)

  const defaultDesc: Record<string, string> = {
    dispatcher: '调度中枢 · 任务编排',
    analyzer: '诊断盲区 · 匹配难度',
    planner: '生成学习路径序列',
    generator: 'RAG 生成 · 标注来源',
    reviewer: '双视角审查 · 自动修正',
    quiz: '节点练习 · 答题反馈',
  }

  if (status === 'running' && agent?.progress) return `执行中... ${agent.progress}%`
  if (status === 'completed') return '已完成 '
  if (status === 'error') return '执行出错 '
  return defaultDesc[agentId] || ''
}

// ========== 连接线状态函数 ==========

const isConnectionActive = (fromId: string, toId: string): boolean => {
  const fromStatus = getAgentStatus(fromId)
  const toStatus = getAgentStatus(toId)
  return (fromStatus === 'completed' && toStatus === 'running') ||
         (fromStatus === 'running' && toStatus === 'idle')
}

const getConnectionColor = (fromId: string, toId: string): string => {
  if (isConnectionActive(fromId, toId)) return '#4F46E5'
  if (getAgentStatus(fromId) === 'completed' && getAgentStatus(toId) === 'completed') return '#059669'
  return '#9CA3AF'
}

const getConnectionMarker = (fromId: string, toId: string): string => {
  if (isConnectionActive(fromId, toId)) return 'url(#arrActive)'
  if (getAgentStatus(fromId) === 'completed' && getAgentStatus(toId) === 'completed') return 'url(#arrCompleted)'
  return 'url(#arr)'
}

const isLoopConnectionActive = (fromId: string, toId: string): boolean => {
  const fromStatus = getAgentStatus(fromId)
  const toStatus = getAgentStatus(toId)
  return fromStatus === 'completed' && toStatus === 'running'
}

const getLoopConnectionColor = (fromId: string, toId: string): string => {
  if (isLoopConnectionActive(fromId, toId)) return '#DC2626'
  return '#4F46E5'
}

const getLoopConnectionMarker = (fromId: string, toId: string): string => {
  if (isLoopConnectionActive(fromId, toId)) return 'url(#arrActive)'
  return 'url(#arr)'
}
</script>

<style scoped>
.agent-flow-diagram {
  width: 100%;
  height: auto;
  max-width: 800px;
  margin: 0 auto;
  display: block;
}

.agent-node.status-running rect {
  animation: pulse-border 2s ease-in-out infinite;
}

.agent-node.status-completed rect {
  transition: all 0.3s ease;
}

.agent-node.status-error rect {
  animation: shake 0.5s ease-in-out;
}

.flowing-line {
  stroke-dasharray: 8 4;
  animation: flow-line 1s linear infinite;
}

.progress-bar {
  transition: width 0.3s ease;
}

@keyframes pulse-border {
  0%, 100% { stroke-opacity: 1; filter: drop-shadow(0 0 0px rgba(79, 70, 229, 0)); }
  50% { stroke-opacity: 0.7; filter: drop-shadow(0 0 4px rgba(79, 70, 229, 0.3)); }
}

@keyframes flow-line {
  0% { stroke-dashoffset: 12; }
  100% { stroke-dashoffset: 0; }
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-2px); }
  75% { transform: translateX(2px); }
}
</style>
