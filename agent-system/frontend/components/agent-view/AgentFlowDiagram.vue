<template>
  <svg
    viewBox="0 0 900 510"
    xmlns="http://www.w3.org/2000/svg"
    class="agent-flow-diagram"
  >
    <defs>
      <!-- 箭头标记（默认灰色） -->
      <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
        <path d="M0,0 L10,5 L0,10" fill="none" stroke="#9CA3AF" stroke-width="1.4"/>
      </marker>
      <!-- 箭头标记（激活状态靛蓝色） -->
      <marker id="arrActive" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
        <path d="M0,0 L10,5 L0,10" fill="none" stroke="#4F46E5" stroke-width="1.4"/>
      </marker>
      <!-- 箭头标记（完成状态绿色） -->
      <marker id="arrCompleted" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
        <path d="M0,0 L10,5 L0,10" fill="none" stroke="#059669" stroke-width="1.4"/>
      </marker>
    </defs>

    <!-- ========== 决策调度 Agent ========== -->
    <g :class="['agent-node', getAgentStatusClass('dispatcher')]">
      <rect
        x="240" y="12" width="200" height="46" rx="10"
        :fill="getAgentFill('dispatcher')"
        :stroke="getAgentStroke('dispatcher')"
        stroke-width="1.5"
      />
      <circle cx="262" cy="35" r="4" :fill="getAgentDotColor('dispatcher')"/>
      <text x="274" y="32" font-family="sans-serif" font-size="13" font-weight="600" fill="#111827">
        决策调度 Agent
      </text>
      <text x="274" y="48" font-family="sans-serif" font-size="10.5" fill="#9CA3AF">
        {{ getAgentDescription('dispatcher') }}
      </text>
      <!-- 进度指示器（仅运行时显示） -->
      <rect
        v-if="getAgentStatus('dispatcher') === 'running'"
        x="240" y="54" width="200" height="3" rx="1.5"
        fill="#E5E7EB"
      />
      <rect
        v-if="getAgentStatus('dispatcher') === 'running'"
        x="240" y="54" :width="getAgentProgress('dispatcher') * 2" height="3" rx="1.5"
        fill="#4F46E5"
        class="progress-bar"
      />
    </g>

    <!-- 连接线：决策调度 → 学情分析 -->
    <line
      x1="340" y1="58" x2="340" y2="84"
      :stroke="getConnectionColor('dispatcher', 'analyzer')"
      stroke-width="1.4"
      :marker-end="getConnectionMarker('dispatcher', 'analyzer')"
      :class="{ 'flowing-line': isConnectionActive('dispatcher', 'analyzer') }"
    />

    <!-- ========== 学情分析 Agent ========== -->
    <g :class="['agent-node', getAgentStatusClass('analyzer')]">
      <rect
        x="240" y="86" width="200" height="46" rx="10"
        :fill="getAgentFill('analyzer')"
        :stroke="getAgentStroke('analyzer')"
        stroke-width="1"
      />
      <circle cx="262" cy="109" r="4" :fill="getAgentDotColor('analyzer')"/>
      <text x="274" y="106" font-family="sans-serif" font-size="13" font-weight="600" fill="#111827">
        学情分析 Agent
      </text>
      <text x="274" y="122" font-family="sans-serif" font-size="10.5" fill="#9CA3AF">
        {{ getAgentDescription('analyzer') }}
      </text>
    </g>

    <!-- 连接线：学情分析 → 路径规划 -->
    <line
      x1="340" y1="132" x2="340" y2="158"
      :stroke="getConnectionColor('analyzer', 'planner')"
      stroke-width="1.4"
      :marker-end="getConnectionMarker('analyzer', 'planner')"
      :class="{ 'flowing-line': isConnectionActive('analyzer', 'planner') }"
    />

    <!-- ========== 路径规划 Agent ========== -->
    <g :class="['agent-node', getAgentStatusClass('planner')]">
      <rect
        x="240" y="160" width="200" height="46" rx="10"
        :fill="getAgentFill('planner')"
        :stroke="getAgentStroke('planner')"
        stroke-width="1"
      />
      <circle cx="262" cy="183" r="4" :fill="getAgentDotColor('planner')"/>
      <text x="274" y="180" font-family="sans-serif" font-size="13" font-weight="600" fill="#111827">
        路径规划 Agent
      </text>
      <text x="274" y="196" font-family="sans-serif" font-size="10.5" fill="#9CA3AF">
        {{ getAgentDescription('planner') }}
      </text>
    </g>

    <!-- 入口折线：路径规划 → 知识生成 -->
    <path
      d="M 340 206 L 340 272 L 190 272 L 190 290"
      fill="none"
      :stroke="getConnectionColor('planner', 'generator')"
      stroke-width="1.4"
      :marker-end="getConnectionMarker('planner', 'generator')"
      :class="{ 'flowing-line': isConnectionActive('planner', 'generator') }"
    />

    <!-- ========== 辩论闭环虚线框 ========== -->
    <rect
      x="50" y="232" width="810" height="160" rx="12"
      fill="none"
      stroke="#4F46E5"
      stroke-width="1.2"
      stroke-dasharray="5 4"
      opacity=".55"
    />
    <text x="70" y="254" font-family="sans-serif" font-size="11" font-weight="600" fill="#4F46E5" letter-spacing=".04em">
      辩论与独立裁判机制 · 降低知识谬误率
    </text>

    <!-- ========== 知识生成 Agent ========== -->
    <g :class="['agent-node', getAgentStatusClass('generator')]">
      <rect
        x="95" y="290" width="190" height="52" rx="10"
        :fill="getAgentFill('generator')"
        :stroke="getAgentStroke('generator')"
        stroke-width="1"
      />
      <circle cx="117" cy="316" r="4" :fill="getAgentDotColor('generator')"/>
      <text x="129" y="312" font-family="sans-serif" font-size="13" font-weight="600" fill="#111827">
        知识生成 Agent
      </text>
      <text x="129" y="330" font-family="sans-serif" font-size="10.5" fill="#9CA3AF">
        {{ getAgentDescription('generator') }}
      </text>
    </g>

    <!-- 连接线：知识生成 → 审核纠偏 -->
    <line
      x1="285" y1="316" x2="349" y2="316"
      :stroke="getConnectionColor('generator', 'reviewer')"
      stroke-width="1.4"
      :marker-end="getConnectionMarker('generator', 'reviewer')"
      :class="{ 'flowing-line': isConnectionActive('generator', 'reviewer') }"
    />
    <text x="317" y="308" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#4F46E5">提交</text>

    <!-- ========== 审核纠偏 Agent ========== -->
    <g :class="['agent-node', getAgentStatusClass('reviewer')]">
      <rect
        x="355" y="290" width="190" height="52" rx="10"
        :fill="getAgentFill('reviewer')"
        :stroke="getAgentStroke('reviewer')"
        stroke-width="1"
      />
      <circle cx="377" cy="316" r="4" :fill="getAgentDotColor('reviewer')"/>
      <text x="389" y="312" font-family="sans-serif" font-size="13" font-weight="600" fill="#111827">
        审核纠偏 Agent
      </text>
      <text x="389" y="330" font-family="sans-serif" font-size="10.5" fill="#9CA3AF">
        {{ getAgentDescription('reviewer') }}
      </text>
    </g>

    <!-- 连接线：审核纠偏 → 裁判 -->
    <line
      x1="545" y1="316" x2="609" y2="316"
      :stroke="getConnectionColor('reviewer', 'judge')"
      stroke-width="1.4"
      :marker-end="getConnectionMarker('reviewer', 'judge')"
      :class="{ 'flowing-line': isConnectionActive('reviewer', 'judge') }"
    />
    <text x="577" y="308" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#4F46E5">分歧</text>

    <!-- ========== 裁判 Agent ========== -->
    <g :class="['agent-node', getAgentStatusClass('judge')]">
      <rect
        x="615" y="290" width="190" height="52" rx="10"
        :fill="getAgentFill('judge')"
        :stroke="getAgentStroke('judge')"
        stroke-width="1"
      />
      <circle cx="637" cy="316" r="4" :fill="getAgentDotColor('judge')"/>
      <text x="649" y="312" font-family="sans-serif" font-size="13" font-weight="600" fill="#111827">
        裁判 Agent
      </text>
      <text x="649" y="330" font-family="sans-serif" font-size="10.5" fill="#9CA3AF">
        {{ getAgentDescription('judge') }}
      </text>
    </g>

    <!-- 回环连线：裁判 → 知识生成（需修正） -->
    <path
      d="M 660 342 C 660 374, 190 374, 190 344"
      fill="none"
      :stroke="getLoopConnectionColor('judge', 'generator')"
      stroke-width="1.4"
      stroke-dasharray="4 3"
      :marker-end="getLoopConnectionMarker('judge', 'generator')"
      :class="{ 'flowing-line': isLoopConnectionActive('judge', 'generator') }"
    />
    <text x="425" y="370" text-anchor="middle" font-family="sans-serif" font-size="10.5" fill="#4F46E5">
      需修正 → 重新生成
    </text>

    <!-- 连接线：裁判 → 试题生成（裁决通过） -->
    <line
      x1="760" y1="342" x2="760" y2="422"
      :stroke="getConnectionColor('judge', 'quiz')"
      stroke-width="1.4"
      :marker-end="getConnectionMarker('judge', 'quiz')"
      :class="{ 'flowing-line': isConnectionActive('judge', 'quiz') }"
    />
    <text x="768" y="386" font-family="sans-serif" font-size="10.5" fill="#4F46E5">裁决通过</text>

    <!-- ========== 试题生成 Agent ========== -->
    <g :class="['agent-node', getAgentStatusClass('quiz')]">
      <rect
        x="665" y="424" width="190" height="46" rx="10"
        :fill="getAgentFill('quiz')"
        :stroke="getAgentStroke('quiz')"
        stroke-width="1.5"
      />
      <circle cx="687" cy="447" r="4" :fill="getAgentDotColor('quiz')"/>
      <text x="699" y="444" font-family="sans-serif" font-size="13" font-weight="600" fill="#111827">
        试题生成 Agent
      </text>
      <text x="699" y="460" font-family="sans-serif" font-size="10.5" fill="#9CA3AF">
        {{ getAgentDescription('quiz') }}
      </text>
    </g>
  </svg>
</template>

<script setup lang="ts">
import { useAgentWebSocket } from '~/composables/useAgentWebSocket'

// ✅ 接收WebSocket实时数据
const { agents, isConnected } = useAgentWebSocket()

// Agent ID映射
const AGENT_MAP: Record<string, string> = {
  dispatcher: 'decision_dispatcher',
  analyzer: 'learning_analysis',
  planner: 'path_planning',
  generator: 'knowledge_generation',
  reviewer: 'review_correction',
  judge: 'judge_agent',
  quiz: 'question_generation',
}

// ========== 状态计算函数 ==========

/**
 * 获取Agent状态
 */
const getAgentStatus = (agentId: string): string => {
  const realId = AGENT_MAP[agentId]
  const agent = agents.value.find(a => a.id === realId)
  return agent?.status || 'idle'
}

/**
 * 获取Agent进度（0-100）
 */
const getAgentProgress = (agentId: string): number => {
  const realId = AGENT_MAP[agentId]
  const agent = agents.value.find(a => a.id === realId)
  return agent?.progress || 0
}

/**
 * 获取Agent状态CSS类
 */
const getAgentStatusClass = (agentId: string): string => {
  const status = getAgentStatus(agentId)
  return `status-${status}`
}

/**
 * 获取Agent背景色
 */
const getAgentFill = (agentId: string): string => {
  const status = getAgentStatus(agentId)
  const colorMap: Record<string, string> = {
    idle: '#FFFFFF',         // 白色
    running: '#EEF2FF',      // 淡靛蓝
    completed: '#ECFDF5',    // 淡绿色
    error: '#FEF2F2',        // 淡红色
    paused: '#FFFBEB',       // 淡黄色
  }
  return colorMap[status] || colorMap.idle
}

/**
 * 获取Agent边框色
 */
const getAgentStroke = (agentId: string): string => {
  const status = getAgentStatus(agentId)
  const colorMap: Record<string, string> = {
    idle: '#E5E7EB',         // 灰色
    running: '#4F46E5',      // 靛蓝色
    completed: '#059669',    // 绿色
    error: '#DC2626',        // 红色
    paused: '#D97706',       // 橙色
  }
  return colorMap[status] || colorMap.idle
}

/**
 * 获取Agent状态点颜色
 */
const getAgentDotColor = (agentId: string): string => {
  const status = getAgentStatus(agentId)
  const colorMap: Record<string, string> = {
    idle: '#9CA3AF',         // 灰色
    running: '#4F46E5',      // 靛蓝色
    completed: '#059669',    // 绿色
    error: '#DC2626',        // 红色
    paused: '#D97706',       // 橙色
  }
  return colorMap[status] || colorMap.idle
}

/**
 * 获取Agent描述文本
 */
const getAgentDescription = (agentId: string): string => {
  const status = getAgentStatus(agentId)
  const realId = AGENT_MAP[agentId]
  const agent = agents.value.find(a => a.id === realId)

  const defaultDesc: Record<string, string> = {
    dispatcher: '调度中枢 · 任务编排',
    analyzer: '诊断盲区 · 匹配难度',
    planner: '生成学习路径序列',
    generator: 'RAG 生成 · 标注来源',
    reviewer: '质疑 · 提出修正',
    judge: '独立裁决 · 给出依据',
    quiz: '分阶试题 · 动态调整',
  }

  if (status === 'running' && agent?.progress) {
    return `执行中... ${agent.progress}%`
  }
  if (status === 'completed') {
    return '已完成 ✓'
  }
  if (status === 'error') {
    return '执行出错 ✗'
  }

  return defaultDesc[agentId] || ''
}

// ========== 连接线状态函数 ==========

/**
 * 判断连接线是否激活（源Agent完成，目标Agent运行中）
 */
const isConnectionActive = (fromId: string, toId: string): boolean => {
  const fromStatus = getAgentStatus(fromId)
  const toStatus = getAgentStatus(toId)
  return (fromStatus === 'completed' && toStatus === 'running') ||
         (fromStatus === 'running' && toStatus === 'idle')
}

/**
 * 获取连接线颜色
 */
const getConnectionColor = (fromId: string, toId: string): string => {
  if (isConnectionActive(fromId, toId)) return '#4F46E5'  // 激活：靛蓝色
  if (getAgentStatus(fromId) === 'completed' && getAgentStatus(toId) === 'completed') {
    return '#059669'  // 双方完成：绿色
  }
  return '#9CA3AF'  // 默认：灰色
}

/**
 * 获取连接线箭头标记
 */
const getConnectionMarker = (fromId: string, toId: string): string => {
  if (isConnectionActive(fromId, toId)) return 'url(#arrActive)'
  if (getAgentStatus(fromId) === 'completed' && getAgentStatus(toId) === 'completed') {
    return 'url(#arrCompleted)'
  }
  return 'url(#arr)'
}

/**
 * 判断回环连接线是否激活（裁判驳回，需重新生成）
 */
const isLoopConnectionActive = (fromId: string, toId: string): boolean => {
  const fromStatus = getAgentStatus(fromId)
  const toStatus = getAgentStatus(toId)
  // 裁判完成但知识生成需要重新运行
  return fromStatus === 'completed' && toStatus === 'running'
}

/**
 * 获取回环连接线颜色
 */
const getLoopConnectionColor = (fromId: string, toId: string): string => {
  if (isLoopConnectionActive(fromId, toId)) return '#DC2626'  // 驳回：红色
  return '#4F46E5'  // 默认：靛蓝色
}

/**
 * 获取回环连接线箭头标记
 */
const getLoopConnectionMarker = (fromId: string, toId: string): string => {
  if (isLoopConnectionActive(fromId, toId)) return 'url(#arrActive)'
  return 'url(#arr)'
}
</script>

<style scoped>
.agent-flow-diagram {
  width: 100%;
  height: auto;
  max-width: 920px;
  margin: 0 auto;
  display: block;
}

/* ========== Agent节点动画 ========== */

/* 运行状态：边框脉冲 */
.agent-node.status-running rect {
  animation: pulse-border 2s ease-in-out infinite;
}

/* 完成状态：平滑过渡 */
.agent-node.status-completed rect {
  transition: all 0.3s ease;
}

/* 错误状态：轻微震动 */
.agent-node.status-error rect {
  animation: shake 0.5s ease-in-out;
}

/* ========== 连接线动画 ========== */

/* 流动效果 */
.flowing-line {
  stroke-dasharray: 8 4;
  animation: flow-line 1s linear infinite;
}

/* 进度条动画 */
.progress-bar {
  transition: width 0.3s ease;
}

/* ========== 关键帧定义 ========== */

@keyframes pulse-border {
  0%, 100% {
    stroke-opacity: 1;
    filter: drop-shadow(0 0 0px rgba(79, 70, 229, 0));
  }
  50% {
    stroke-opacity: 0.7;
    filter: drop-shadow(0 0 4px rgba(79, 70, 229, 0.3));
  }
}

@keyframes flow-line {
  0% {
    stroke-dashoffset: 12;
  }
  100% {
    stroke-dashoffset: 0;
  }
}

@keyframes shake {
  0%, 100% {
    transform: translateX(0);
  }
  25% {
    transform: translateX(-2px);
  }
  75% {
    transform: translateX(2px);
  }
}
</style>
