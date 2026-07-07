<template>
  <div class="page page--wide">
    <div class="page-head">
      <p class="page-head__eyebrow">知识库</p>
      <h1 class="page-head__title">知识图谱</h1>
      <p class="page-head__desc">
        以掌握度驱动知识点点亮：深绿代表已掌握，浅绿代表基本掌握，黄色代表待巩固，灰色代表建议重点学习。
      </p>
    </div>

    <div v-if="loading" class="card" style="margin-top: 24px">
      <div class="text-center py-12 text-text-3">正在加载知识图谱数据...</div>
    </div>

    <div v-else-if="errorMsg" class="card" style="margin-top: 24px">
      <div class="text-center py-12 text-err">{{ errorMsg }}</div>
    </div>

    <template v-else>
      <div class="knowledge-card">
        <div class="knowledge-card__head">
          <div>
            <div class="section-title">知识图谱</div>
            <div class="section-subtitle">
              {{ isLoggedIn ? '当前账号学习进度' : '未登录，仅展示知识体系结构' }}
            </div>
          </div>
          <span class="badge badge--mute">平均掌握度 {{ stats.average_score }}%</span>
        </div>

        <div class="graph-panel">
          <ClientOnly v-if="graphData">
            <VChart
              :option="graphChartOption"
              autoresize
              class="graph-chart"
              @click="handleChartClick"
            />
            <template #fallback>
              <div class="text-center py-12 text-text-3">正在加载图表...</div>
            </template>
          </ClientOnly>
          <p v-else class="text-text-3 text-center py-12">
            暂无知识图谱数据<br/>
            <NuxtLink to="/workflow" class="btn btn--ghost btn--sm" style="margin-top: 12px">去生成学习资源 →</NuxtLink>
          </p>
        </div>

        <div class="legend-row">
          <span
            v-for="item in legendItems"
            :key="item.status"
            class="legend-item"
          >
            <span class="legend-dot" :style="{ background: item.color }"></span>
            {{ item.label }}
          </span>
        </div>

        <div class="summary-row">
          <div class="summary-card summary-card--blue">
            <div class="summary-card__label">知识点总数</div>
            <div class="summary-card__value">{{ stats.total }}</div>
          </div>
          <div class="summary-card summary-card--green">
            <div class="summary-card__label">已掌握知识点</div>
            <div class="summary-card__value">{{ stats.mastered }}</div>
          </div>
          <div class="summary-card summary-card--yellow">
            <div class="summary-card__label">待提升知识点</div>
            <div class="summary-card__value">{{ stats.to_improve }}</div>
          </div>
        </div>
      </div>

      <div class="detail-grid">
        <div class="card">
          <div class="card__head">
            <h2 class="card__title">节点详情</h2>
            <span v-if="selectedNode" class="status-pill" :style="{ color: getNodeColor(selectedNode.score) }">
              {{ selectedNode.status_label }}
            </span>
          </div>

          <div v-if="selectedNode" class="node-detail">
            <div class="node-detail__title">{{ selectedNode.name }}</div>
            <div class="node-detail__meta">
              <span>{{ selectedNode.category_label }}</span>
              <span v-if="selectedNode.file">{{ selectedNode.file }}</span>
            </div>

            <div class="mastery-line">
              <div class="mastery-line__top">
                <span>掌握度</span>
                <strong>{{ selectedNode.score }}%</strong>
              </div>
              <div class="mastery-bar">
                <div
                  class="mastery-bar__fill"
                  :style="{ width: selectedNode.score + '%', background: getNodeColor(selectedNode.score) }"
                ></div>
              </div>
            </div>

            <div class="source-list">
              <div v-if="selectedNode.source_type">来源类型：{{ selectedNode.source_type }}</div>
              <div v-if="selectedNode.source_name">来源名称：{{ selectedNode.source_name }}</div>
              <div v-if="selectedNode.author">作者：{{ selectedNode.author }}</div>
              <div v-if="selectedNode.year">年份：{{ selectedNode.year }}</div>
              <div v-if="selectedNode.chapter">章节：{{ selectedNode.chapter }}</div>
            </div>

            <button
              v-if="selectedNode.is_leaf"
              class="primary-mark-btn"
              :class="{ 'primary-mark-btn--reset': selectedNode.score >= 80 }"
              :disabled="markingNodes.has(selectedNode.id)"
              @click="toggleMark(selectedNode)"
            >
              {{ markingNodes.has(selectedNode.id) ? '处理中...' : (selectedNode.score >= 80 ? '重置掌握度' : '标记为已掌握') }}
            </button>
          </div>

          <div v-else class="empty-hint">
            点击图谱中的知识点查看详情。
          </div>
        </div>

        <div class="card">
          <div class="card__head">
            <h2 class="card__title">分类掌握情况</h2>
            <div class="category-toolbar">
              <button type="button" class="category-toolbar__btn" @click="collapseAllCategories">
                全部收起
              </button>
              <button type="button" class="category-toolbar__btn" @click="expandAllCategories">
                全部展开
              </button>
              <span class="badge badge--mute">{{ categoryDetails.length }} 类</span>
            </div>
          </div>

          <div
            v-for="cat in categoryDetails"
            :key="cat.key"
            class="category-block"
          >
            <button
              type="button"
              class="category-block__head"
              :aria-expanded="isCategoryExpanded(cat.key)"
              @click="toggleCategory(cat.key)"
            >
              <div>
                <div class="category-block__title">{{ cat.name }}</div>
                <div class="category-block__sub">
                  已掌握 {{ cat.mastered }} / {{ cat.total }}，平均 {{ cat.average_score }}%
                </div>
              </div>
              <div class="category-block__right">
                <span class="badge badge--mute">{{ cat.percentage }}%</span>
                <span
                  class="category-block__chevron"
                  :class="{ 'category-block__chevron--open': isCategoryExpanded(cat.key) }"
                >
                  >
                </span>
              </div>
            </button>

            <div v-show="isCategoryExpanded(cat.key)" class="category-block__body">
              <div class="mastery-bar mastery-bar--thin">
                <div
                  class="mastery-bar__fill"
                  :style="{ width: cat.percentage + '%', background: '#22C55E' }"
                ></div>
              </div>

              <div class="knowledge-list">
                <button
                  v-for="item in cat.items"
                  :key="item.id"
                  type="button"
                  class="knowledge-item"
                  :class="{ 'knowledge-item--active': selectedNode?.id === item.id }"
                  @click="selectedNodeId = item.id"
                >
                  <span class="knowledge-item__dot" :style="{ background: getNodeColor(item.score) }"></span>
                  <span class="knowledge-item__name">{{ item.name }}</span>
                  <span class="knowledge-item__score">{{ item.score }}%</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 底部出口 -->
      <div style="display: flex; gap: 12px; justify-content: center; margin-top: 32px">
        <NuxtLink to="/resources" class="btn btn--primary btn--lg">去学习资源 →</NuxtLink>
        <NuxtLink to="/dashboard" class="btn btn--ghost btn--lg">查看学情诊断 →</NuxtLink>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ ssr: false })

import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { GraphChart } from 'echarts/charts'
import { CanvasRenderer } from 'echarts/renderers'
import { TooltipComponent } from 'echarts/components'

use([GraphChart, CanvasRenderer, TooltipComponent])

interface GraphNode {
  id: string
  name: string
  type: 'root' | 'category' | 'knowledge'
  category: string
  category_label: string
  score: number
  status: string
  status_label: string
  is_leaf: boolean
  file?: string
  source_type?: string
  source_name?: string
  author?: string
  year?: string
  chapter?: string
}

interface GraphLink {
  source: string
  target: string
  relation?: string
}

interface GraphStats {
  total: number
  mastered: number
  learning: number
  weak: number
  recommended: number
  to_improve: number
  average_score: number
  percentage: number
}

interface CategoryStat {
  key: string
  name: string
  total: number
  mastered: number
  to_improve: number
  average_score: number
  percentage: number
  items?: GraphNode[]
}

interface LegendItem {
  status: string
  label: string
  color: string
}

interface GraphPayload {
  domain: string
  domain_name: string
  nodes: GraphNode[]
  links: GraphLink[]
  stats: GraphStats
  categories: CategoryStat[]
  legend: LegendItem[]
}

const emptyStats: GraphStats = {
  total: 0,
  mastered: 0,
  learning: 0,
  weak: 0,
  recommended: 0,
  to_improve: 0,
  average_score: 0,
  percentage: 0,
}

const { isLoggedIn, token } = useAuth()
const api = useApi()
const router = useRouter()

const loading = ref(true)
const errorMsg = ref('')
const graphData = ref<GraphPayload | null>(null)
const selectedNodeId = ref('')
const markingNodes = ref<Set<string>>(new Set())
const expandedCategories = ref<Set<string>>(new Set())

const stats = computed(() => graphData.value?.stats || emptyStats)
const legendItems = computed<LegendItem[]>(() => graphData.value?.legend || [
  { status: 'mastered', label: '掌握度 >= 80%', color: '#22C55E' },
  { status: 'learning', label: '掌握度 60-79%', color: '#A3E635' },
  { status: 'weak', label: '掌握度 < 60%', color: '#FACC15' },
  { status: 'recommended', label: '建议重点学习', color: '#D1D5DB' },
])

const nodesById = computed(() => {
  const map = new Map<string, GraphNode>()
  for (const node of graphData.value?.nodes || []) {
    map.set(node.id, node)
  }
  return map
})

const selectedNode = computed(() => {
  if (!selectedNodeId.value) return null
  return nodesById.value.get(selectedNodeId.value) || null
})

const leafNodes = computed(() => (graphData.value?.nodes || []).filter(node => node.is_leaf))

const categoryDetails = computed<CategoryStat[]>(() => {
  const categories = graphData.value?.categories || []
  return categories.map(cat => ({
    ...cat,
    items: leafNodes.value
      .filter(node => node.category === cat.key)
      .sort((a, b) => a.score - b.score || a.name.localeCompare(b.name, 'zh-Hans-CN')),
  }))
})

function isCategoryExpanded(key: string) {
  return expandedCategories.value.has(key)
}

function toggleCategory(key: string) {
  const next = new Set(expandedCategories.value)
  if (next.has(key)) {
    next.delete(key)
  } else {
    next.add(key)
  }
  expandedCategories.value = next
}

function expandAllCategories() {
  expandedCategories.value = new Set(categoryDetails.value.map(cat => cat.key))
}

function collapseAllCategories() {
  expandedCategories.value = new Set()
}

function getNodeColor(score: number) {
  if (score >= 80) return '#22C55E'
  if (score >= 60) return '#A3E635'
  if (score > 0) return '#FACC15'
  return '#D1D5DB'
}

function getNodeBorderColor(score: number) {
  if (score >= 80) return '#15803D'
  if (score >= 60) return '#65A30D'
  if (score > 0) return '#CA8A04'
  return '#9CA3AF'
}

function getNodeSize(node: GraphNode) {
  if (node.type === 'root') return 58
  if (node.type === 'category') return 42
  if (node.score >= 80) return 32
  if (node.score >= 60) return 28
  return 26
}

function shortName(name: string, maxLength = 12) {
  return name.length > maxLength ? `${name.slice(0, maxLength)}...` : name
}

const graphChartOption = computed(() => {
  if (!graphData.value) return {}

  const nodes = graphData.value.nodes.map(node => ({
    id: node.id,
    name: node.name,
    value: node.score,
    raw: node,
    symbolSize: getNodeSize(node),
    draggable: true,
    itemStyle: {
      color: getNodeColor(node.score),
      borderColor: getNodeBorderColor(node.score),
      borderWidth: node.type === 'knowledge' ? 2 : 3,
      shadowBlur: node.score >= 80 ? 10 : 0,
      shadowColor: 'rgba(34, 197, 94, 0.28)',
    },
    label: {
      show: true,
      position: 'bottom',
      formatter: node.type === 'knowledge' ? shortName(node.name, 11) : node.name,
      color: '#334155',
      fontSize: node.type === 'knowledge' ? 10 : 12,
      fontWeight: node.type === 'knowledge' ? 400 : 600,
    },
  }))

  const links = graphData.value.links.map(link => ({
    ...link,
    lineStyle: {
      color: '#CBD5E1',
      width: 1.2,
      opacity: 0.9,
      curveness: 0.08,
    },
  }))

  return {
    tooltip: {
      trigger: 'item',
      borderWidth: 0,
      padding: 12,
      formatter: (params: any) => {
        const node = params.data?.raw as GraphNode | undefined
        if (!node) return ''
        const file = node.file ? `<br/>文件：${node.file}` : ''
        return `
          <div style="font-weight:600;margin-bottom:6px">${node.name}</div>
          <div>分类：${node.category_label}</div>
          <div>掌握度：${node.score}%</div>
          <div>状态：${node.status_label}</div>
          ${file}
        `
      },
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        draggable: true,
        data: nodes,
        links,
        force: {
          repulsion: 210,
          gravity: 0.055,
          edgeLength: [72, 150],
          friction: 0.28,
          layoutAnimation: true,
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: {
            width: 2.2,
          },
        },
      },
    ],
  }
})

function handleChartClick(params: any) {
  const node = params?.data?.raw as GraphNode | undefined
  if (node) {
    selectedNodeId.value = node.id
  }
}

async function toggleMark(node: GraphNode) {
  if (!node?.is_leaf || markingNodes.value.has(node.id)) return
  if (!isLoggedIn.value || !token.value) {
    router.push('/login')
    return
  }

  const markAsMastered = node.score < 80
  markingNodes.value = new Set([...markingNodes.value, node.id])

  try {
    await api.markKnowledgeNode(node.id, markAsMastered, markAsMastered ? 100 : 0)
    const keepSelected = selectedNodeId.value
    await loadData(false)
    selectedNodeId.value = keepSelected
  } catch (err: any) {
    console.error('更新知识点掌握度失败:', err)
    errorMsg.value = `更新失败: ${err.message || '未知错误'}`
  } finally {
    const next = new Set(markingNodes.value)
    next.delete(node.id)
    markingNodes.value = next
  }
}

async function loadData(showLoading = true) {
  if (showLoading) loading.value = true
  errorMsg.value = ''

  try {
    const withProgress = Boolean(isLoggedIn.value && token.value)
    const data = await api.getKnowledgeGraphGraph(withProgress)
    graphData.value = data

    if (expandedCategories.value.size === 0 && data.categories?.length) {
      expandedCategories.value = new Set([data.categories[0].key])
    }

    if (!selectedNodeId.value) {
      const firstWeakNode = leafNodes.value.find(node => node.score < 80)
      selectedNodeId.value = firstWeakNode?.id || leafNodes.value[0]?.id || ''
    }
  } catch (err: any) {
    console.error('加载知识图谱数据失败:', err)
    errorMsg.value = `数据加载失败: ${err.message || '未知错误'}`
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})

watch(isLoggedIn, () => {
  loadData(false)
})
</script>

<style scoped>
.knowledge-card {
  margin-top: 24px;
  padding: 20px 24px 24px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--bg);
}

.knowledge-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.section-title {
  position: relative;
  padding-left: 12px;
  font-size: 18px;
  font-weight: 700;
  color: var(--text-1);
}

.section-title::before {
  content: "";
  position: absolute;
  left: 0;
  top: 4px;
  width: 4px;
  height: 18px;
  border-radius: 2px;
  background: var(--accent);
}

.section-subtitle {
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-3);
}

.graph-panel {
  min-height: 540px;
  border-radius: 4px;
  background: #F8FAFC;
  overflow: hidden;
}

.graph-chart {
  width: 100%;
  height: 540px;
}

.legend-row {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  align-items: center;
  margin-top: 16px;
  color: var(--text-2);
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.legend-dot {
  width: 13px;
  height: 13px;
  border-radius: 50%;
  border: 1px solid rgba(15, 23, 42, 0.08);
}

.summary-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-top: 18px;
}

.summary-card {
  padding: 20px;
  border-radius: 10px;
}

.summary-card__label {
  font-size: 14px;
  color: #475569;
}

.summary-card__value {
  margin-top: 8px;
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
}

.summary-card--blue {
  background: #EFF6FF;
}

.summary-card--blue .summary-card__value {
  color: #2563EB;
}

.summary-card--green {
  background: #ECFDF5;
}

.summary-card--green .summary-card__value {
  color: #22C55E;
}

.summary-card--yellow {
  background: #FEFCE8;
}

.summary-card--yellow .summary-card__value {
  color: #F59E0B;
}

.detail-grid {
  display: grid;
  grid-template-columns: minmax(320px, 0.8fr) minmax(0, 1.2fr);
  gap: 24px;
  margin-top: 24px;
}

.status-pill {
  font-size: 12px;
  font-weight: 600;
}

.node-detail__title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-1);
}

.node-detail__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-3);
}

.mastery-line {
  margin-top: 20px;
}

.mastery-line__top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: var(--text-2);
}

.mastery-bar {
  width: 100%;
  height: 10px;
  margin-top: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: #E5E7EB;
}

.mastery-bar--thin {
  height: 6px;
  margin-top: 10px;
}

.mastery-bar__fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.3s ease;
}

.source-list {
  display: grid;
  gap: 6px;
  margin-top: 18px;
  font-size: 12px;
  color: var(--text-3);
}

.primary-mark-btn {
  width: 100%;
  margin-top: 20px;
  padding: 10px 14px;
  border: 1px solid #22C55E;
  border-radius: 8px;
  background: #22C55E;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.primary-mark-btn:hover {
  background: #16A34A;
}

.primary-mark-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.primary-mark-btn--reset {
  border-color: #CBD5E1;
  background: #fff;
  color: #475569;
}

.primary-mark-btn--reset:hover {
  background: #F8FAFC;
}

.empty-hint {
  padding: 44px 0;
  text-align: center;
  color: var(--text-3);
}

.category-block {
  padding: 14px 0;
  border-bottom: 1px solid var(--line);
}

.category-block:last-child {
  border-bottom: 0;
}

.category-toolbar {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.category-toolbar__btn {
  padding: 4px 8px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: #fff;
  color: var(--text-3);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}

.category-toolbar__btn:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: rgba(79, 70, 229, 0.04);
}

.category-block__head {
  width: 100%;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.category-block__title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-1);
}

.category-block__sub {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-3);
}

.category-block__right {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.category-block__chevron {
  width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  color: var(--text-3);
  font-size: 12px;
  transform: rotate(0deg);
  transition: transform 0.16s ease, background 0.16s ease;
}

.category-block__head:hover .category-block__chevron {
  background: var(--bg-muted);
  color: var(--accent);
}

.category-block__chevron--open {
  transform: rotate(90deg);
}

.category-block__body {
  padding-top: 10px;
}

.knowledge-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 12px;
}

.knowledge-item {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  padding: 8px 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  color: var(--text-2);
  font-size: 12px;
  text-align: left;
  cursor: pointer;
}

.knowledge-item:hover,
.knowledge-item--active {
  border-color: var(--accent);
  background: rgba(79, 70, 229, 0.04);
}

.knowledge-item__dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
}

.knowledge-item__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.knowledge-item__score {
  color: var(--text-3);
}

@media (max-width: 960px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }

  .knowledge-list {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .knowledge-card__head,
  .category-block__head {
    flex-direction: column;
  }

  .summary-row {
    grid-template-columns: 1fr;
  }

  .graph-panel,
  .graph-chart {
    height: 460px;
    min-height: 460px;
  }
}
</style>
