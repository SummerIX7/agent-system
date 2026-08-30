/**
 * 知识图谱页面逻辑（从 pages/knowledge-graph.vue 抽出）。
 *
 * 页面文件只保留模板、样式与 ECharts 组件注册；
 * 数据加载、掌握度状态、分类展开、图表配置构建均在此维护。
 */
import { use } from 'echarts/core'
import { GraphChart } from 'echarts/charts'
import { CanvasRenderer } from 'echarts/renderers'
import { TooltipComponent } from 'echarts/components'

use([GraphChart, CanvasRenderer, TooltipComponent])

import { useAuth } from './useAuth'
import { useApi } from './useApi'

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

export function useKnowledgeGraph() {
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

  return {
    // 状态
    loading,
    errorMsg,
    isLoggedIn,
    graphData,
    selectedNodeId,
    markingNodes,
    // 计算属性
    stats,
    legendItems,
    selectedNode,
    categoryDetails,
    graphChartOption,
    // 方法
    handleChartClick,
    toggleMark,
    isCategoryExpanded,
    toggleCategory,
    expandAllCategories,
    collapseAllCategories,
    getNodeColor,
  }
}
