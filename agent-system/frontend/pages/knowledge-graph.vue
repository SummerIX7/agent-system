<template>
  <div class="page page--wide">
    <div class="page-head">
      <p class="page-head__eyebrow">知识库</p>
      <h1 class="page-head__title">知识图谱</h1>
      <p class="page-head__desc">数控加工知识体系树状图。完成分析报告或考核后系统自动标记已学习知识点，实时追踪学习进度。</p>
    </div>

    <!-- Loading 状态 -->
    <div v-if="loading" class="card" style="margin-top: 24px">
      <div class="text-center py-12 text-text-3">正在加载知识图谱数据...</div>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="errorMsg" class="card" style="margin-top: 24px">
      <div class="text-center py-12 text-err">{{ errorMsg }}</div>
    </div>

    <template v-else>
      <!-- 学习进度面板 -->
      <div class="stats-row" style="margin-top: 24px">
        <div class="stat-cell">
          <div class="stat-cell__label">知识节点总数</div>
          <div class="stat-cell__value">{{ totalLeaves }}</div>
          <div class="stat-cell__sub">个知识点</div>
        </div>
        <div class="stat-cell">
          <div class="stat-cell__label">已学习</div>
          <div class="stat-cell__value" style="color: var(--ok)">{{ completedCount }}</div>
          <div class="stat-cell__sub">个知识点</div>
        </div>
        <div class="stat-cell">
          <div class="stat-cell__label">学习进度</div>
          <div class="stat-cell__value" :style="{ color: progressColor }">{{ progressPercentage }}%</div>
          <div class="stat-cell__sub">
            <div class="progress-bar-mini">
              <div class="progress-bar-mini__fill" :style="{ width: progressPercentage + '%', background: progressColor }"></div>
            </div>
          </div>
        </div>
        <div class="stat-cell">
          <div class="stat-cell__label">知识分类</div>
          <div class="stat-cell__value">{{ categoryCount }}</div>
          <div class="stat-cell__sub">个分类维度</div>
        </div>
      </div>

      <!-- 树状图 -->
      <div class="dashboard-grid" style="margin-top: 24px">
        <!-- ECharts 树状图 -->
        <div class="card" style="grid-column: 1 / -1">
          <div class="card__head">
            <h2 class="card__title">知识体系树状图</h2>
            <span class="badge badge--mute">{{ totalLeaves }} 个知识点</span>
          </div>
          <div style="min-height: 520px">
            <ClientOnly v-if="treeData">
              <VChart :option="treeChartOption" autoresize style="width: 100%; height: 500px" />
              <template #fallback>
                <div class="text-center py-12 text-text-3">正在加载图表...</div>
              </template>
            </ClientOnly>
            <p v-else class="text-text-3 text-center py-12">暂无知识图谱数据</p>
          </div>
          <div class="legend-row">
            <span class="legend-item"><span class="legend-dot legend-dot--normal"></span> 未学习</span>
            <span class="legend-item"><span class="legend-dot legend-dot--completed"></span> 已学习</span>
            <span class="legend-item"><span class="legend-dot legend-dot--category"></span> 知识分类</span>
          </div>
        </div>

        <!-- 分类详情卡片 -->
        <div class="card">
          <div class="card__head">
            <h2 class="card__title">分类详情</h2>
            <span class="badge badge--mute">{{ categoryDetails.length }} 类</span>
          </div>
          <div
            v-for="cat in categoryDetails"
            :key="cat.name"
            style="margin-bottom: 16px"
          >
            <div class="category-header">
              <div style="font-size: 14px; font-weight: 600">{{ cat.name }}</div>
              <span class="badge badge--mute">{{ cat.completed }} / {{ cat.total }}</span>
            </div>
            <div class="bar" style="margin: 8px 0 12px">
              <div
                class="bar__fill ok"
                :style="{ width: (cat.total / maxCategoryCount * 100) + '%' }"
              ></div>
            </div>
            <div class="doc-list">
              <div
                v-for="item in cat.items"
                :key="item.name"
                class="doc-item"
                :class="{ 'doc-item--completed': completedSet.has(item.id) }"
              >
                <div class="doc-item__row">
                  <div class="doc-item__info">
                    <div class="doc-item__title">
                      <span class="doc-item__dot" :class="'dot--' + cat.key"></span>
                      {{ item.name }}
                      <span v-if="completedSet.has(item.id)" class="check-mark">&#10003;</span>
                    </div>
                    <div class="doc-item__meta">
                      <template v-if="item.source_type">
                        <span class="doc-item__tag">{{ item.source_type }}</span>
                      </template>
                      <template v-if="item.author">
                        <span>{{ item.author }}</span>
                      </template>
                    </div>
                  </div>
                  <button
                    class="mark-btn"
                    :class="{ 'mark-btn--learned': completedSet.has(item.id) }"
                    :disabled="markingNodes.has(item.id)"
                    @click.stop="toggleMark(item.id)"
                  >
                    {{ markingNodes.has(item.id) ? '...' : (completedSet.has(item.id) ? '取消标记' : '标记已学') }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

    </template>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ ssr: false })

import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { TreeChart } from 'echarts/charts'
import { CanvasRenderer } from 'echarts/renderers'
import { TooltipComponent, TitleComponent } from 'echarts/components'

use([TreeChart, CanvasRenderer, TooltipComponent, TitleComponent])

interface TreeNode {
  name: string
  id: string
  children?: TreeNode[]
  is_leaf?: boolean
  completed?: boolean
  category?: string
  file?: string
  source_type?: string
  author?: string
  year?: string
  chapter?: string
  source_name?: string
  total_leaves?: number
}

interface CategoryDetail {
  name: string
  key: string
  total: number
  completed: number
  items: TreeNode[]
}

const { isLoggedIn, token } = useAuth()
const api = useApi()

const loading = ref(true)
const errorMsg = ref('')
const treeData = ref<TreeNode | null>(null)
const completedSet = ref<Set<string>>(new Set())
const progressPercentage = ref(0)
const markingNodes = ref<Set<string>>(new Set())

const totalLeaves = computed(() => treeData.value?.total_leaves || 0)
const completedCount = computed(() => completedSet.value.size)
const categoryCount = computed(() => treeData.value?.children?.length || 0)
const progressColor = computed(() => {
  const p = progressPercentage.value
  if (p >= 80) return 'var(--ok)'
  if (p >= 40) return 'var(--warn)'
  return 'var(--text-1)'
})

const categoryDetails = computed<CategoryDetail[]>(() => {
  if (!treeData.value?.children) return []
  return treeData.value.children.map(cat => {
    const items = (cat.children || []).filter(c => c.is_leaf).map(c => ({
      ...c,
      name: c.name,
      id: c.id,
      is_leaf: true,
      source_type: c.source_type,
      author: c.author,
    }))
    const completed = items.filter(c => completedSet.value.has(c.id)).length
    return {
      name: cat.name,
      key: cat.category || cat.name,
      total: items.length,
      completed,
      items: items as TreeNode[],
    }
  })
})

const maxCategoryCount = computed(() => {
  if (categoryDetails.value.length === 0) return 1
  return Math.max(...categoryDetails.value.map(d => d.total))
})

// ECharts Tree 配置
const treeChartOption = computed(() => {
  if (!treeData.value) return {}

  const data = JSON.parse(JSON.stringify(treeData.value))

  // 递归处理节点样式
  function processNode(node: any) {
    if (node.is_leaf) {
      const isCompleted = completedSet.value.has(node.id)
      node.itemStyle = {
        color: isCompleted ? '#10B981' : '#4F46E5',
        borderColor: isCompleted ? '#059669' : '#4338CA',
        borderWidth: 2,
        borderRadius: 5,
      }
      if (isCompleted) {
        node.label = {
          ...(node.label || {}),
          color: '#059669',
          fontWeight: 'bold',
        }
      }
      node.symbol = isCompleted ? 'roundRect' : 'circle'
      node.symbolSize = isCompleted ? 14 : 10
    } else {
      // 分类节点样式
      node.itemStyle = {
        color: '#F59E0B',
        borderColor: '#D97706',
        borderWidth: 2,
        borderRadius: 5,
      }
      node.label = {
        ...(node.label || {}),
        color: '#92400E',
        fontWeight: 'bold',
        fontSize: 13,
      }
      node.symbol = 'roundRect'
      node.symbolSize = 16
    }
    if (node.children) {
      node.children.forEach(processNode)
    }
  }

  // 根节点样式
  data.itemStyle = {
    color: '#1E40AF',
    borderColor: '#1E3A8A',
    borderWidth: 3,
    borderRadius: 8,
  }
  data.label = {
    color: '#FFFFFF',
    fontWeight: 'bold',
    fontSize: 14,
  }
  data.symbol = 'roundRect'
  data.symbolSize = 20

  if (data.children) {
    data.children.forEach(processNode)
  }

  // 初始展开到第2层
  data.collapsed = false
  if (data.children) {
    data.children.forEach((cat: any) => {
      cat.collapsed = false
    })
  }

  return {
    tooltip: {
      trigger: 'item',
      triggerOn: 'mousemove',
      formatter: (params: any) => {
        if (params.data.is_leaf) {
          const completed = completedSet.value.has(params.data.id)
          let html = `<b>${params.data.name}</b><br/>`
          if (params.data.source_type) html += `类型: ${params.data.source_type}<br/>`
          if (params.data.author) html += `作者: ${params.data.author}<br/>`
          if (params.data.year) html += `年份: ${params.data.year}<br/>`
          html += `状态: <b style="color:${completed ? '#10B981' : '#9CA3AF'}">${completed ? '已学习 ✓' : '未学习'}</b>`
          return html
        }
        return `<b>${params.data.name}</b>`
      },
    },
    series: [
      {
        type: 'tree',
        data: [data],
        top: '2%',
        left: '8%',
        bottom: '2%',
        right: '10%',
        symbolSize: 10,
        orient: 'LR',
        expandAndCollapse: true,
        initialTreeDepth: 2,
        label: {
          position: 'right',
          verticalAlign: 'middle',
          align: 'left',
          fontSize: 12,
          fontFamily: '-apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif',
        },
        leaves: {
          label: {
            position: 'right',
            verticalAlign: 'middle',
            align: 'left',
            fontSize: 11,
          },
        },
        emphasis: {
          focus: 'descendant',
        },
        lineStyle: {
          color: '#CBD5E1',
          width: 1.5,
          curveness: 0.5,
        },
      },
    ],
  }
})

// 手动标记/取消标记知识点
async function toggleMark(nodeId: string) {
  if (!isLoggedIn.value || markingNodes.value.has(nodeId)) return

  const newCompleted = !completedSet.value.has(nodeId)
  markingNodes.value = new Set([...markingNodes.value, nodeId])

  // 乐观更新 UI
  const prevSet = new Set(completedSet.value)
  if (newCompleted) {
    completedSet.value = new Set([...completedSet.value, nodeId])
  } else {
    const next = new Set(completedSet.value)
    next.delete(nodeId)
    completedSet.value = next
  }

  try {
    const result = await api.markKnowledgeNode(nodeId, newCompleted)
    // 用 API 返回的数据同步确认
    completedSet.value = new Set(result.completed_nodes || [])
    progressPercentage.value = result.percentage || 0
  } catch (err: any) {
    // 失败时回滚
    completedSet.value = prevSet
    console.error('标记知识点失败:', err)
  } finally {
    const next = new Set(markingNodes.value)
    next.delete(nodeId)
    markingNodes.value = next
  }
}

// 加载数据
async function loadData() {
  loading.value = true
  errorMsg.value = ''

  try {
    // 并行加载树数据和进度数据
    const requests: Promise<any>[] = [
      api.getKnowledgeGraph(),
    ]

    if (isLoggedIn.value && token.value) {
      requests.push(
        api.getKnowledgeGraphProgress()
      )
    }

    const responses = await Promise.all(requests)
    treeData.value = responses[0]

    if (responses.length > 1 && responses[1]) {
      const progressData = responses[1]
      completedSet.value = new Set(progressData.completed_nodes || [])
      progressPercentage.value = progressData.percentage || 0
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

// 监听登录状态变化，登录后自动加载进度
watch(isLoggedIn, (val) => {
  if (val && treeData.value) {
    // 已加载树数据，只需补充加载进度
    api.getKnowledgeGraphProgress()
      .then(data => {
        if (data) {
          completedSet.value = new Set(data.completed_nodes || [])
          progressPercentage.value = data.percentage || 0
        }
      }).catch(() => {})
  }
})
</script>

<style scoped>
/* ── 统计面板 ── */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1px;
  background: var(--line);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  overflow: hidden;
}
.stat-cell {
  background: var(--bg);
  padding: 22px 24px;
}
.stat-cell__label { font-size: 12px; color: var(--text-3); }
.stat-cell__value {
  font-size: 28px;
  font-weight: 600;
  letter-spacing: -.03em;
  margin-top: 8px;
}
.stat-cell__sub {
  font-size: 12px;
  color: var(--text-3);
  margin-top: 4px;
}

/* 迷你进度条 */
.progress-bar-mini {
  width: 100%;
  height: 6px;
  background: var(--bg-muted);
  border-radius: 3px;
  overflow: hidden;
  margin-top: 4px;
}
.progress-bar-mini__fill {
  height: 100%;
  background: var(--accent);
  border-radius: 3px;
  transition: width 0.4s ease;
}

/* ── 图例 ── */
.legend-row {
  display: flex;
  justify-content: center;
  gap: 24px;
  padding: 12px 0;
  border-top: 1px solid var(--line);
  margin-top: 8px;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-2);
}
.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}
.legend-dot--normal { background: #4F46E5; }
.legend-dot--completed { background: #10B981; }
.legend-dot--category { background: #F59E0B; }

/* ── 分类详情 ── */
.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}
.category-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.doc-list {
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  overflow: hidden;
}
.doc-item {
  padding: 10px 14px;
  border-bottom: 1px solid var(--line);
  transition: background 0.2s;
}
.doc-item:last-child { border-bottom: none; }
.doc-item--completed { background: rgba(16, 185, 129, 0.04); }
.doc-item__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.doc-item__info {
  flex: 1;
  min-width: 0;
}
.doc-item__title {
  font-size: 13px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
}
.doc-item__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dot--theory { background: var(--accent); }
.dot--practice { background: var(--ok); }
.dot--standards { background: var(--warn); }
.check-mark {
  color: var(--ok);
  font-weight: bold;
  font-size: 14px;
}
.doc-item__meta {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-top: 4px;
  font-size: 11px;
  color: var(--text-3);
}
.doc-item__tag {
  display: inline-block;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  background: var(--bg-muted);
  color: var(--text-3);
  font-weight: 500;
}

/* ── 标记按钮 ── */
.mark-btn {
  flex-shrink: 0;
  padding: 4px 12px;
  border: 1px solid var(--accent);
  border-radius: 4px;
  background: transparent;
  color: var(--accent);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}
.mark-btn:hover {
  background: var(--accent);
  color: #fff;
}
.mark-btn:disabled {
  opacity: .5;
  cursor: not-allowed;
}
.mark-btn--learned {
  border-color: var(--ok);
  color: var(--ok);
}
.mark-btn--learned:hover {
  background: var(--ok);
  color: #fff;
}

@media (max-width: 760px) {
  .stats-row { grid-template-columns: 1fr 1fr; }
  .dashboard-grid { grid-template-columns: 1fr; }
}
</style>
