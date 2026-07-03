<script setup lang="ts">
import { knowledgeProgressApi } from '@/api/knowledgeProgress'
import type { LearnerProgress, TreeNode } from '@/api/knowledgeProgress'
import { PeopleOutline, SchoolOutline } from '@vicons/ionicons5'
import { NIcon, NProgress, NButton, NTag, NDataTable, NCard, NGrid, NGi, NSpin, NEmpty } from 'naive-ui'
import { h } from 'vue'

const loading = ref(true)
const allData = ref<{ total_learners: number; total_knowledge_points: number; learners: LearnerProgress[] }>({
  total_learners: 0,
  total_knowledge_points: 0,
  learners: [],
})
const treeData = ref<TreeNode | null>(null)
const selectedLearner = ref<string | null>(null)
const selectedCompletedNodes = ref<Set<string>>(new Set())

// 加载数据
async function loadData() {
  loading.value = true
  try {
    const [progressRes, treeRes] = await Promise.all([
      knowledgeProgressApi.getAllProgress(),
      knowledgeProgressApi.getTree(),
    ])
    allData.value = progressRes
    treeData.value = treeRes
  } catch (err: any) {
    console.error('加载知识图谱进度数据失败:', err)
  } finally {
    loading.value = false
  }
}

// 选择学员 → 展开详情
function selectLearner(username: string) {
  if (selectedLearner.value === username) {
    selectedLearner.value = null
    selectedCompletedNodes.value = new Set()
    return
  }
  selectedLearner.value = username
  const learner = allData.value.learners.find(l => l.username === username)
  selectedCompletedNodes.value = new Set(learner?.completed_nodes || [])
}

// 获取学员已完成节点列表
function getCompletedNodesForLearner(username: string): string[] {
  const learner = allData.value.learners.find(l => l.username === username)
  return learner?.completed_nodes || []
}

// 递归查找节点名
function findNodeName(nodeId: string): string {
  function search(node: TreeNode): string | null {
    if (node.id === nodeId) return node.name
    if (node.children) {
      for (const child of node.children) {
        const found = search(child)
        if (found) return found
      }
    }
    return null
  }
  if (!treeData.value) return nodeId
  return search(treeData.value) || nodeId
}

// 表格列定义
const columns = [
  { title: '学员', key: 'username', width: 140 },
  { title: '已学知识点', key: 'completed_count', align: 'center' as const, width: 120 },
  { title: '总知识点', key: 'total', align: 'center' as const, width: 120 },
  {
    title: '学习进度', key: 'percentage', width: 220,
    render(row: LearnerProgress) {
      return h('div', { style: 'display: flex; align-items: center; gap: 10px' }, [
        h(NProgress, {
          percentage: row.percentage,
          indicatorPlacement: 'inside',
          height: 20,
          borderRadius: 4,
          railColor: '#ECECEF',
          color: row.percentage >= 80 ? '#10B981' : row.percentage >= 40 ? '#F59E0B' : '#6366F1',
        }),
      ])
    },
  },
  {
    title: '操作', key: 'actions', width: 100, align: 'center' as const,
    render(row: LearnerProgress) {
      return h(NButton, {
        size: 'small',
        type: selectedLearner.value === row.username ? 'info' : 'default',
        onClick: () => selectLearner(row.username),
      }, { default: () => selectedLearner.value === row.username ? '收起' : '查看详情' })
    },
  },
]

// 详细已学节点表格列
const detailColumns = [
  { title: '知识点', key: 'name', ellipsis: { tooltip: true } },
  {
    title: '状态', key: 'completed', width: 80, align: 'center' as const,
    render(row: { completed: boolean }) {
      return h(NTag, {
        type: row.completed ? 'success' : 'default',
        size: 'small',
        bordered: false,
      }, { default: () => row.completed ? '已学' : '未学' })
    },
  },
]

// 获取所有叶子节点
function getAllLeafNodes(): { id: string; name: string }[] {
  const leaves: { id: string; name: string }[] = []
  function collect(node: TreeNode) {
    if (node.is_leaf) {
      leaves.push({ id: node.id, name: node.name })
    }
    if (node.children) {
      node.children.forEach(collect)
    }
  }
  if (treeData.value) collect(treeData.value)
  return leaves
}

const allLeafNodes = computed(() => getAllLeafNodes())

// 选定学员的详情列表
const learnerDetailData = computed(() => {
  return allLeafNodes.value.map(node => ({
    name: node.name,
    completed: selectedCompletedNodes.value.has(node.id),
  }))
})

// 统计卡片
const statCards = computed(() => [
  { label: '学员总数', value: allData.value.total_learners, icon: PeopleOutline, color: '#4F46E5' },
  { label: '知识点总数', value: allData.value.total_knowledge_points, icon: SchoolOutline, color: '#059669' },
  {
    label: '平均进度',
    value: allData.value.learners.length > 0
      ? `${Math.round(allData.value.learners.reduce((s, l) => s + l.percentage, 0) / allData.value.learners.length)}%`
      : '--',
    icon: SchoolOutline,
    color: '#D97706',
  },
])

onMounted(() => {
  loadData()
})
</script>

<template>
  <div>
    <div style="margin-bottom: 24px">
      <h1 style="font-size: 22px; font-weight: 600; letter-spacing: -.03em; color: #111827; margin-bottom: 8px">
        学员知识图谱进度
      </h1>
      <p style="font-size: 14px; color: #9CA3AF">查看所有学员的知识图谱学习进度</p>
    </div>

    <NSpin :show="loading">
      <!-- 统计卡片 -->
      <NGrid :cols="3" :x-gap="24" :y-gap="16" responsive="screen">
        <NGi v-for="card in statCards" :key="card.label" :span="1">
          <NCard :bordered="true" size="small">
            <div style="display: flex; align-items: flex-start; justify-content: space-between">
              <div>
                <div style="font-size: 13px; color: #9CA3AF; margin-bottom: 8px">{{ card.label }}</div>
                <div style="font-size: 28px; font-weight: 600; letter-spacing: -.03em; color: #111827">
                  {{ card.value }}
                </div>
              </div>
              <div :style="{ width: '40px', height: '40px', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center', background: card.color + '15' }">
                <NIcon :size="20" :color="card.color"><component :is="card.icon" /></NIcon>
              </div>
            </div>
          </NCard>
        </NGi>
      </NGrid>

      <!-- 学员列表 -->
      <NCard title="学员学习进度列表" :bordered="true" size="small" style="margin-top: 24px">
        <template #header-extra>
          <NTag size="small" :bordered="false" type="info">{{ allData.total_learners }} 名学员</NTag>
        </template>
        <NDataTable
          :columns="columns"
          :data="allData.learners"
          :bordered="false"
          size="small"
          :max-height="500"
        />
      </NCard>

      <!-- 学员详情 -->
      <NCard
        v-if="selectedLearner"
        :title="`${selectedLearner} — 知识点学习详情`"
        :bordered="true"
        size="small"
        style="margin-top: 24px"
      >
        <NGrid :cols="2" :x-gap="24" responsive="screen">
          <NGi :span="1">
            <div style="font-size: 14px; font-weight: 600; margin-bottom: 12px; color: #4B5563">已学知识点列表</div>
            <div v-if="getCompletedNodesForLearner(selectedLearner).length > 0">
              <NTag
                v-for="nodeId in getCompletedNodesForLearner(selectedLearner)"
                :key="nodeId"
                type="success"
                size="small"
                :bordered="false"
                style="margin-right: 8px; margin-bottom: 8px"
              >
                {{ findNodeName(nodeId) }}
              </NTag>
            </div>
            <NEmpty v-else description="该学员暂无已学知识点" />
          </NGi>
          <NGi :span="1">
            <div style="font-size: 14px; font-weight: 600; margin-bottom: 12px; color: #4B5563">全部知识点状态</div>
            <NDataTable
              :columns="detailColumns"
              :data="learnerDetailData"
              :bordered="false"
              size="small"
              :max-height="400"
              virtual-scroll
            />
          </NGi>
        </NGrid>
      </NCard>
    </NSpin>
  </div>
</template>
