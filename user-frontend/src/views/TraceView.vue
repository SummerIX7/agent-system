<template>
  <div class="page page--wide">
    <div class="page-head">
      <p class="page-head__eyebrow">调试工具</p>
      <h1 class="page-head__title">工作流全链路追踪</h1>
      <p class="page-head__desc">查看每个 Agent 的输入输出、LLM 调用明细、审核评分和修正过程。</p>
    </div>

    <!-- 输入栏 -->
    <div class="trace-bar">
      <input v-model="inputSid" class="inp" placeholder="输入会话 ID（如 user-1）" @keyup.enter="loadTrace" />
      <button class="btn btn--primary" :disabled="loading" @click="loadTrace">
        {{ loading ? '加载中...' : '加载追踪' }}
      </button>
      <span v-if="traceData" class="t2">
        主题: <b>{{ traceData.topic }}</b> ·
        结果: <b :class="outcomeClass">{{ outcomeText }}</b>
      </span>
    </div>

    <!-- 时间线 -->
    <div v-if="traceData && traceData.nodes" class="timeline">
      <div v-for="(node, i) in (traceData.nodes as any[])" :key="i" class="tl-node">
        <!-- 连线 -->
        <div v-if="i > 0" class="tl-connector">
          <div class="tl-line" :class="{ 'tl-line--retry': isRetryEdge(i) }"></div>
          <span v-if="isRetryEdge(i)" class="tl-retry-badge">重试</span>
        </div>

        <!-- 节点卡片 -->
        <div class="tl-card" :class="nodeStatusClass(node)">
          <div class="tl-card__header" @click="toggleNode(i)">
            <div class="tl-card__left">
              <span class="tl-num">{{ nodeNum(node, i) }}</span>
              <span class="tl-agent">{{ node.agent_name }}</span>
              <span :class="['badge', nodeBadge(node)]">{{ nodeStatusLabel(node) }}</span>
            </div>
            <div class="tl-card__right">
              <span class="t2" style="font-size:12px">{{ node.duration_ms }}ms</span>
              <span style="font-size:12px;color:var(--text-3);margin-left:12px">{{ openNodes[i] ? '收起 ▲' : '展开 ▼' }}</span>
            </div>
          </div>

          <!-- 展开内容 -->
          <div v-if="openNodes[i]" class="tl-card__body">
            <!-- 输入 -->
            <div class="tl-section">
              <div class="tl-section__title" @click="toggleSection(i, 'input')">
                 输入 {{ openSections[i]?.input ? '▼' : '▶' }}
              </div>
              <pre v-if="openSections[i]?.input" class="tl-json">{{ fmtJson(node.input) }}</pre>
            </div>

            <!-- 输出 -->
            <div class="tl-section">
              <div class="tl-section__title" @click="toggleSection(i, 'output')">
                 输出 {{ openSections[i]?.output ? '▼' : '▶' }}
              </div>
              <pre v-if="openSections[i]?.output" class="tl-json">{{ fmtJson(node.output) }}</pre>
            </div>

            <!-- LLM 调用 -->
            <div v-if="node.llm_calls && node.llm_calls.length > 0" class="tl-section">
              <div class="tl-section__title" @click="toggleSection(i, 'llm')">
                 LLM 调用 ×{{ node.llm_calls.length }} {{ openSections[i]?.llm ? '▼' : '▶' }}
              </div>
              <div v-if="openSections[i]?.llm">
                <div v-for="(call, ci) in (node.llm_calls as any[])" :key="ci" class="tl-llm">
                  <div class="tl-llm__head" @click="toggleLlmCall(i, ci)">
                    <span class="badge badge--accent">{{ call.label }}</span>
                    <span class="t2" style="font-size:11px">{{ call.elapsed_ms }}ms</span>
                    <span style="font-size:11px;color:var(--text-3);margin-left:auto">
                      {{ openLlmCalls[`${i}-${ci}`] ? '收起 ▲' : '展开 ▼' }}
                    </span>
                  </div>
                  <div v-if="openLlmCalls[`${i}-${ci}`]" class="tl-llm__body">
                    <div class="tl-llm__col">
                      <div class="tl-llm__label"> 提示词</div>
                      <pre class="tl-code">{{ truncate(call.prompt, 6000) }}</pre>
                    </div>
                    <div class="tl-llm__col">
                      <div class="tl-llm__label"> 响应</div>
                      <pre class="tl-code">{{ call.response }}</pre>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="traceData && (!traceData.nodes || traceData.nodes.length === 0)" class="tl-empty">
        暂无追踪数据。请先触发一次资源生成。
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="!traceData && !loading" class="tl-empty">
      输入会话 ID 查看工作流追踪数据
    </div>
  </div>
</template>

<script setup lang="ts">
import { useApi } from '@/composables/useApi'
const inputSid = ref('')
const traceData = ref<any>(null)
const loading = ref(false)
const openNodes = ref<Record<number, boolean>>({})
const openSections = ref<Record<number, Record<string, boolean>>>({})
const openLlmCalls = ref<Record<string, boolean>>({})

const route = useRoute()
const api = useApi()

// 从 URL 自动加载
onMounted(() => {
  const sid = route.query.sessionId as string
  if (sid) {
    inputSid.value = sid
    loadTrace()
  }
})

const loadTrace = async () => {
  if (!inputSid.value) return
  loading.value = true
  traceData.value = null
  openNodes.value = {}
  openSections.value = {}
  openLlmCalls.value = {}
  try {
    const data = await api.getTrace(inputSid.value)
    traceData.value = data
    // 默认展开第一个节点
    if (data.nodes?.length > 0) {
      openNodes.value[0] = true
    }
  } catch (e: any) {
    console.error('加载追踪失败:', e)
  } finally {
    loading.value = false
  }
}

const toggleNode = (i: number) => {
  openNodes.value[i] = !openNodes.value[i]
  if (openNodes.value[i] && !openSections.value[i]) {
    openSections.value[i] = { input: false, output: false, llm: false }
  }
}

const toggleSection = (i: number, section: string) => {
  if (!openSections.value[i]) {
    openSections.value[i] = { input: false, output: false, llm: false }
  }
  openSections.value[i][section] = !openSections.value[i][section]
}

const toggleLlmCall = (i: number, ci: number) => {
  const key = `${i}-${ci}`
  openLlmCalls.value[key] = !openLlmCalls.value[key]
}

const fmtJson = (obj: any) => {
  try {
    return JSON.stringify(obj, null, 2)
  } catch {
    return String(obj)
  }
}

const truncate = (text: string, max: number) => {
  if (!text || text.length <= max) return text
  const half = Math.floor(max / 2)
  return text.slice(0, half) + `\n\n... [省略 ${text.length - max} 字符] ...\n\n` + text.slice(-half)
}

const nodeNum = (node: any, i: number) => {
  const map: Record<string, string> = {
    analyze: '①', plan_path: '②', generate: '③',
    review_correct: '③½', gen_questions: '④',
  }
  return map[node.node] || String(i + 1)
}

const isRetryEdge = (i: number) => {
  if (!traceData.value?.nodes) return false
  const prev = traceData.value.nodes[i - 1]
  const curr = traceData.value.nodes[i]
  return prev?.node === 'review_correct' && curr?.node === 'generate'
}

const nodeStatusClass = (node: any) => {
  if (node.output?.has_degraded) return 'tl-card--degraded'
  if (node.output?.all_passed === false) return 'tl-card--failed'
  if (node.output?.all_passed === true) return 'tl-card--passed'
  return ''
}

const nodeBadge = (node: any) => {
  if (node.output?.has_degraded) return 'badge--err'
  if (node.output?.all_passed === false) return 'badge--err'
  if (node.output?.all_passed === true) return 'badge--ok'
  return 'badge--mute'
}

const nodeStatusLabel = (node: any) => {
  if (node.output?.has_degraded) return '已降级'
  if (node.output?.all_passed === false) return '未通过'
  if (node.output?.all_passed === true) return '已通过'
  return '已完成'
}

const outcomeClass = computed(() => {
  if (traceData.value?.outcome?.result === 'degraded') return 'c-err'
  if (traceData.value?.outcome?.result === 'completed') return 'c-ok'
  return ''
})

const outcomeText = computed(() => {
  if (traceData.value?.outcome?.result === 'degraded') return ' 降级通过'
  if (traceData.value?.outcome?.result === 'completed') return ' 正常完成'
  return '未知'
})
</script>

<style scoped>
.trace-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 32px;
  flex-wrap: wrap;
}
.inp {
  flex: 1;
  min-width: 220px;
  padding: 10px 16px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  font-size: 14px;
  background: var(--bg);
  color: var(--text);
  outline: none;
}
.inp:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

/* 时间线 */
.timeline { display: flex; flex-direction: column; }
.tl-connector {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-left: 48px;
  height: 32px;
  position: relative;
}
.tl-line {
  width: 2px;
  height: 100%;
  background: var(--line);
  margin-left: 19px;
}
.tl-line--retry {
  background: var(--err);
  stroke-dasharray: 4 3;
  background: repeating-linear-gradient(to bottom, var(--err) 0 4px, transparent 4px 8px);
}
.tl-retry-badge {
  font-size: 11px;
  color: var(--err);
  font-weight: 600;
  font-family: var(--mono);
}

/* 节点卡片 */
.tl-card {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  overflow: hidden;
  transition: border-color .15s;
}
.tl-card--passed { border-left: 3px solid var(--ok); }
.tl-card--failed { border-left: 3px solid var(--err); }
.tl-card--degraded { border-left: 3px solid #D97706; }

.tl-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  cursor: pointer;
  user-select: none;
  background: var(--bg);
  transition: background .1s;
}
.tl-card__header:hover { background: var(--bg-soft); }
.tl-card__left { display: flex; align-items: center; gap: 10px; }
.tl-card__right { display: flex; align-items: center; }
.tl-num {
  font-family: var(--mono);
  font-size: 13px;
  font-weight: 600;
  color: var(--accent);
  width: 24px;
}
.tl-agent { font-size: 14px; font-weight: 600; }

.tl-card__body {
  padding: 0 20px 20px;
  background: var(--bg-soft);
  border-top: 1px solid var(--line);
}

/* 分段 */
.tl-section { margin-top: 16px; }
.tl-section__title {
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  user-select: none;
  padding: 8px 0;
  color: var(--text-2);
}
.tl-section__title:hover { color: var(--text); }

.tl-json {
  font-size: 12px;
  font-family: var(--mono);
  white-space: pre-wrap;
  word-break: break-all;
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 12px;
  max-height: 360px;
  overflow-y: auto;
  margin: 0;
  line-height: 1.6;
  color: var(--text-2);
}

/* LLM 调用 */
.tl-llm {
  border: 1px solid var(--line);
  border-radius: 6px;
  margin-top: 10px;
  overflow: hidden;
}
.tl-llm__head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  cursor: pointer;
  user-select: none;
  background: var(--bg);
}
.tl-llm__head:hover { background: var(--bg-muted); }
.tl-llm__body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  border-top: 1px solid var(--line);
}
@media (max-width: 900px) {
  .tl-llm__body { grid-template-columns: 1fr; }
}
.tl-llm__col {
  padding: 0;
  overflow: hidden;
}
.tl-llm__col:first-child {
  border-right: 1px solid var(--line);
}
@media (max-width: 900px) {
  .tl-llm__col:first-child { border-right: none; border-bottom: 1px solid var(--line); }
}
.tl-llm__label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-3);
  padding: 8px 14px;
  background: var(--bg-muted);
}
.tl-code {
  font-size: 11px;
  font-family: var(--mono);
  white-space: pre-wrap;
  word-break: break-all;
  padding: 10px 14px;
  margin: 0;
  max-height: 420px;
  overflow-y: auto;
  line-height: 1.5;
  color: var(--text-2);
}

.tl-empty {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-3);
  font-size: 14px;
}

.c-ok { color: var(--ok); }
.c-err { color: var(--err); }
</style>
