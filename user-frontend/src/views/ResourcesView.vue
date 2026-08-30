<template>
  <div class="page page--wide">
    <div class="page-head">
      <p class="page-head__eyebrow">步骤 4</p>
      <h1 class="page-head__title">个性化学习资源</h1>
      <p class="page-head__desc">系统已为你生成多类资源，每条知识点均标注来源出处，难度适配你的当前水平。</p>
    </div>

    <!-- 5 个节点均可直接切换查看，不再做顺序解锁 -->
    <div v-if="!loading && nodes.length > 0" class="node-selector">
      <button
        v-for="node in nodes"
        :key="node.stage"
        class="node-selector__card"
        :class="{ active: Number(node.stage) === selectedStage }"
        @click="switchStage(Number(node.stage))"
      >
        <span class="node-selector__stage">节点 {{ node.stage }}</span>
        <strong>{{ node.title }}</strong>
        <span class="node-selector__meta">
          {{ difficultyLabel(node.difficulty || 'beginner') }}
          <template v-if="node.estimated_hours"> · {{ node.estimated_hours }} 小时</template>
        </span>
      </button>
    </div>

    <!-- 当前查看节点信息条 -->
    <div v-if="currentNode" class="node-info-bar">
      <div class="node-info-left">
        <span class="node-info-stage">正在查看节点 {{ currentNode.stage }}</span>
        <span class="node-info-divider">|</span>
        <span class="node-info-title">{{ currentNode.title }}</span>
        <span v-if="currentNode.difficulty" class="badge" :class="difficultyBadge(currentNode.difficulty)">
          {{ difficultyLabel(currentNode.difficulty) }}
        </span>
      </div>
      <div class="node-info-right">
        <span v-if="currentNode.estimated_hours" class="text-sm text-text-3"> {{ currentNode.estimated_hours }} 小时</span>
      </div>
    </div>

    <div v-if="loading" class="text-center py-12">
      <div class="spinner"></div>
      <p class="mt-4 text-text-2">正在加载资源...</p>
    </div>

    <div v-else-if="resources.length === 0" class="text-center py-12">
      <p class="text-text-3">暂无生成资源，请先完成 Agent 协同生成</p>
      <RouterLink to="/workflow" class="btn btn--primary mt-4">前往 Agent 协同</RouterLink>
    </div>

    <div v-else>
      <!-- Tabs（不再包含试题） -->
      <div class="tabs-bar">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="tab-btn"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </div>

      <!-- 讲义 -->
      <div v-if="activeTab === 'lecture'" class="card">
        <div class="res-meta">
          <span class="badge badge--accent">{{ difficultyLabel(currentNode?.difficulty || 'beginner') }}</span>
          <span>·</span><span>约 12 分钟阅读</span>
          <span>·</span><span>已通过审核纠偏</span>
        </div>
        <MarkdownRenderer :content="lectureContent" />
      </div>

      <!-- 实验指导 -->
      <div v-if="activeTab === 'guide'" class="card">
        <div class="res-meta">
          <span class="badge badge--accent">{{ difficultyLabel(currentNode?.difficulty || 'beginner') }}</span>
          <span>·</span><span>预计 30 分钟</span>
          <span>·</span><span>含完整示例</span>
        </div>
        <MarkdownRenderer :content="guideContent" />
      </div>

      <!-- 项目案例 -->
      <div v-if="activeTab === 'project'" class="card">
        <div class="res-meta">
          <span class="badge badge--accent">{{ difficultyLabel(currentNode?.difficulty || 'beginner') }}</span>
          <span>·</span><span>综合项目</span>
          <span>·</span><span>含完整解答</span>
        </div>
        <MarkdownRenderer :content="projectContent" />
      </div>

      <!-- 底部操作按钮 -->
      <div class="actions-bar">
        <RouterLink to="/report" class="btn btn--ghost">← 返回分析报告</RouterLink>
        <div class="actions-group">
          <button class="btn btn--ghost" @click="goToPractice">
            练习本节点 →
          </button>
        </div>
      </div>

      <!-- 参考来源汇总 -->
      <div v-if="allSources.length > 0" class="card" style="margin-top: 24px;">
        <div class="card__head">
          <h2 class="card__title"> 参考来源汇总</h2>
          <span class="badge badge--mute">{{ allSources.length }} 个来源</span>
        </div>

        <div class="sources-grid">
          <div v-for="(src, idx) in allSources" :key="idx" class="source-item">
            <div style="display: flex; align-items: start; gap: 12px;">
              <span style="font-size: 24px; flex-shrink: 0;">{{ src.icon }}</span>
              <div style="min-width: 0; flex: 1;">
                <div style="display: flex; align-items: center; gap: 8px;">
                  <span class="text-sm font-semibold text-text truncate">
                    {{ src.type === '书籍' ? '《' + src.name + '》' : src.name }}
                  </span>
                  <span class="badge badge--mute" style="font-size: 10px;">{{ src.type }}</span>
                </div>
                <div class="mt-1 text-xs text-text-3" style="line-height: 1.6;">
                  <p v-if="src.author">作者：{{ src.author }}</p>
                  <p v-if="src.year">年份：{{ src.year }}</p>
                  <p v-if="src.chapter">章节：{{ src.chapter }}</p>
                  <a v-if="src.url" :href="src.url" target="_blank" class="text-accent hover:underline"> 查看链接</a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部导航 -->
    <div v-if="!loading && resources.length > 0" style="display: flex; gap: 12px; justify-content: center; margin-top: 32px">
      <RouterLink to="/workflow" class="btn btn--ghost btn--lg">← 重新生成资源</RouterLink>
      <RouterLink :to="`/practice?stage=${selectedStage}&level=node`" class="btn btn--primary btn--lg">进入答题练习 →</RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { LearningPathNode } from '@/types/api'
import type { ResourceOutput } from '@/types/api'
import { useApi } from '@/composables/useApi'
import { useSession } from '@/composables/useSession'
import { useLearningPath } from '@/composables/useLearningPath'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'
const router = useRouter()
const route = useRoute()
const api = useApi()
const { sessionId } = useSession()
const { nodes, fetchLearningPath } = useLearningPath()

const loading = ref(true)
const resources = ref<ResourceOutput[]>([])
const activeTab = ref('lecture')
const selectedStage = ref(Number(route.query.stage) || 1)

const lectureContent = ref('')
const guideContent = ref('')
const projectContent = ref('')

const currentNode = ref<LearningPathNode | null>(null)

interface SourceInfo {
  icon: string; type: string; name: string; author: string
  year: string; chapter: string; url: string; raw: string
}

const allSources = ref<SourceInfo[]>([])

const tabs = [
  { key: 'lecture', label: '定制讲义' },
  { key: 'guide', label: '实验指导' },
  { key: 'project', label: '项目案例' },
]

const difficultyLabel = (d: string) => {
  const map: Record<string, string> = { beginner: '初级', intermediate: '中级', advanced: '高级', expert: '专家' }
  return map[d] || d
}
const difficultyBadge = (d: string) => {
  const map: Record<string, string> = { beginner: 'badge--mute', intermediate: 'badge--accent', advanced: 'badge--warn', expert: 'badge--err' }
  return map[d] || 'badge--mute'
}

const goToPractice = () => {
  router.push({
    path: '/practice',
    query: { stage: String(selectedStage.value), level: 'node' },
  })
}

const switchStage = (stage: number) => {
  if (!stage || stage === selectedStage.value) return
  router.push({ path: '/resources', query: { stage: String(stage) } })
}

/** 从生成内容中解析所有来源标注 */
const parseSources = (content: string): SourceInfo[] => {
  if (!content) return []
  const sources: SourceInfo[] = []
  const seen = new Set<string>()

  const bookRegex = /\s*来源[：:]\s*《([^》]+)》\s*\(([^,)]+)(?:,\s*([^)]+))?\)\s*(.*)?/g
  let match
  while ((match = bookRegex.exec(content)) !== null) {
    const key = match[1]
    if (seen.has(key)) continue
    seen.add(key)
    sources.push({ icon: '', type: '书籍', name: match[1], author: match[2]?.trim() || '', year: match[3]?.trim() || '', chapter: match[4]?.trim() || '', url: '', raw: match[0] })
  }
  const urlRegex = /\s*(?:链接|URL)[：:]\s*(https?:\/\/[^\s<]+)/g
  while ((match = urlRegex.exec(content)) !== null) {
    if (sources.length > 0 && !sources[sources.length - 1].url) {
      sources[sources.length - 1].url = match[1]
    } else {
      sources.push({ icon: '', type: '网页', name: match[1], author: '', year: '', chapter: '', url: match[1], raw: match[0] })
    }
  }
  return sources
}

const loadResources = async () => {
  if (!sessionId.value) { loading.value = false; return }
  loading.value = true
  resources.value = []
  lectureContent.value = ''
  guideContent.value = ''
  projectContent.value = ''
  allSources.value = []
  currentNode.value = null

  try {
    await fetchLearningPath()
    let stage = Number(route.query.stage) || selectedStage.value || 1
    if (nodes.value.length > 0 && !nodes.value.some((n) => Number(n.stage) === stage)) {
      stage = Number(nodes.value[0].stage) || 1
    }
    selectedStage.value = stage
    currentNode.value = (nodes.value || []).find((n) => Number(n.stage) === stage) || null
    if (!currentNode.value && nodes.value.length > 0) currentNode.value = nodes.value[0]
  } catch { /* 降级：无节点信息也可正常使用 */ }

  const loadStage = selectedStage.value || Number(route.query.stage) || undefined
  try {
    const data = await api.getResources(sessionId.value, loadStage)
    resources.value = data

    for (const res of data) {
      const content = typeof res.content === 'string' ? res.content : JSON.stringify(res.content)
      if (res.type === 'lecture') lectureContent.value = content
      else if (res.type === 'guide') guideContent.value = content
      else if (res.type === 'project') projectContent.value = content
    }

    const rawContents = [lectureContent.value, guideContent.value, projectContent.value].filter(Boolean)
    allSources.value = parseSources(rawContents.join('\n'))
  } catch (err: any) {
    console.warn('获取资源失败:', err)
  } finally {
    loading.value = false
  }
}

onMounted(loadResources)

watch(() => route.query.stage, () => {
  loadResources()
})
</script>

<style scoped>
.node-selector {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}
.node-selector__card {
  text-align: left;
  border: 1px solid var(--line);
  background: var(--bg);
  border-radius: var(--radius-sm);
  padding: 14px 16px;
  cursor: pointer;
  transition: all .15s;
  min-height: 116px;
}
.node-selector__card:hover {
  border-color: var(--accent);
  transform: translateY(-1px);
}
.node-selector__card.active {
  border-color: var(--accent);
  background: var(--accent-soft);
  box-shadow: 0 0 0 1px rgba(99, 102, 241, .12);
}
.node-selector__stage {
  display: inline-flex;
  margin-bottom: 8px;
  padding: 3px 8px;
  border-radius: 99px;
  background: rgba(99, 102, 241, .1);
  color: var(--accent);
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 600;
}
.node-selector__card strong {
  display: block;
  font-size: 14px;
  line-height: 1.45;
  color: var(--text);
}
.node-selector__meta {
  display: block;
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-3);
}
.node-info-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  background: var(--accent-soft);
  border: 1px solid rgba(99, 102, 241, 0.15);
  border-radius: var(--radius-sm);
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 10px;
}
.node-info-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.node-info-stage {
  font-size: 12px;
  font-weight: 600;
  font-family: var(--mono);
  color: var(--accent);
  background: rgba(99, 102, 241, 0.1);
  padding: 3px 10px;
  border-radius: 99px;
}
.node-info-divider {
  color: var(--line);
}
.node-info-title {
  font-size: 14px;
  font-weight: 600;
}
.node-info-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.actions-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 28px;
  padding-top: 20px;
  border-top: 1px solid var(--line);
  gap: 12px;
  flex-wrap: wrap;
}
.actions-group {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.complete-hint {
  font-size: 13px;
  color: var(--ok);
  background: var(--ok-soft);
  border-radius: 99px;
  padding: 6px 12px;
}
.complete-message {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 16px;
  padding: 16px 18px;
  border: 1px solid #A7F3D0;
  border-radius: var(--radius-sm);
  background: var(--ok-soft);
  color: var(--text);
  flex-wrap: wrap;
}
.tabs-bar {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 28px;
}
.tab-btn {
  font-size: 13px;
  color: var(--text-2);
  font-weight: 500;
  padding: 12px 16px;
  position: relative;
  transition: color .15s;
  background: none;
  border: none;
  cursor: pointer;
}
.tab-btn:hover { color: var(--text); }
.tab-btn.active { color: var(--text); }
.tab-btn.active::after {
  content: "";
  position: absolute;
  left: 16px; right: 16px;
  bottom: -1px;
  height: 2px;
  background: var(--accent);
  border-radius: 99px;
}
.res-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: var(--text-3);
  margin-bottom: 20px;
}
.sources-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}
.source-item {
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  transition: border-color .15s;
}
.source-item:hover { border-color: var(--accent); }
.spinner {
  width: 32px; height: 32px;
  margin: 0 auto;
  border: 3px solid var(--line);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
@media (max-width: 760px) {
  .node-selector { grid-template-columns: 1fr; }
  .sources-grid { grid-template-columns: 1fr; }
}
</style>
