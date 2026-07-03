<script setup lang="ts">
import { dashboardApi } from '@/api/dashboard'
import type { DashboardOverview } from '@/types/admin'
import { formatPercent, LEVEL_MAP } from '@/utils/format'
import {
  PeopleOutline,
  HourglassOutline,
  PulseOutline,
  TrophyOutline,
} from '@vicons/ionicons5'
import { NIcon } from 'naive-ui'

const loading = ref(true)
const overview = ref<DashboardOverview>({
  total_learners: 0,
  pending_approvals: 0,
  active_today: 0,
  avg_pass_rate: 0,
  knowledge_distribution: {},
})
const trends = ref<any>({})
const domainStats = ref<any>({})

const statCards = computed(() => [
  { label: '总学员数', value: overview.value.total_learners, icon: PeopleOutline, color: '#4F46E5' },
  { label: '待审批数', value: overview.value.pending_approvals, icon: HourglassOutline, color: '#D97706' },
  { label: '今日活跃', value: overview.value.active_today, icon: PulseOutline, color: '#059669' },
  { label: '平均通过率', value: formatPercent(overview.value.avg_pass_rate), icon: TrophyOutline, color: '#4F46E5' },
])

async function loadData() {
  loading.value = true
  try {
    const [ov, tr, ds] = await Promise.all([
      dashboardApi.getOverview(),
      dashboardApi.getTrends(30),
      dashboardApi.getDomainStats(),
    ])
    overview.value = ov
    trends.value = tr
    domainStats.value = ds
  } catch (err: any) {
    console.error('加载数据看板失败:', err)
  } finally {
    loading.value = false
  }
}

// 知识分布转换为柱状图数据
const knowledgeChartData = computed(() => {
  const dist = overview.value.knowledge_distribution
  if (!dist) return []
  return Object.entries(dist).map(([name, counts]) => ({
    name,
    low: counts.low,
    medium: counts.medium,
    high: counts.high,
  }))
})

// 趋势图数据
const trendDates = computed(() => {
  const daily = trends.value.new_learners_daily || {}
  return Object.keys(daily).sort()
})

// 等级分布
const levelData = computed(() => {
  const stats = domainStats.value.by_level || {}
  return Object.entries(stats).map(([name, value]) => ({ name, value: value as number }))
})

onMounted(() => {
  loadData()
})
</script>

<template>
  <div>
    <div class="page-head">
      <h1 class="page-head-title">数据看板</h1>
      <p class="page-head-desc">培训数据概览，实时掌握学员学习动态</p>
    </div>

    <NSpin :show="loading">
      <!-- 统计卡片 -->
      <NGrid :cols="4" :x-gap="24" :y-gap="16" responsive="screen">
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

      <!-- 图表区域 -->
      <NGrid :cols="2" :x-gap="24" style="margin-top: 24px" responsive="screen">
        <!-- 知识点分布 -->
        <NGi :span="1">
          <NCard title="知识点掌握分布" :bordered="true" size="small">
            <template #header-extra>
              <NTag size="small" :bordered="false" type="info">全部领域</NTag>
            </template>
            <div v-if="knowledgeChartData.length > 0">
              <NDataTable
                :columns="[
                  { title: '知识点', key: 'name', width: 140 },
                  { title: '初级', key: 'low', align: 'center' },
                  { title: '中级', key: 'medium', align: 'center' },
                  { title: '高级', key: 'high', align: 'center' },
                ]"
                :data="knowledgeChartData"
                :bordered="false"
                size="small"
                :max-height="300"
              />
            </div>
            <NEmpty v-else description="暂无数据" />
          </NCard>
        </NGi>

        <!-- 趋势图 -->
        <NGi :span="1">
          <NCard title="学习趋势（近30天）" :bordered="true" size="small">
            <div v-if="trendDates.length > 0">
              <NDataTable
                :columns="[
                  { title: '日期', key: 'date' },
                  { title: '新增学员', key: 'new', align: 'center' },
                  { title: '活跃学员', key: 'active', align: 'center' },
                ]"
                :data="trendDates.slice(-14).map(d => ({
                  date: d,
                  new: (trends.new_learners_daily || {})[d] || 0,
                  active: (trends.active_daily || {})[d] || 0,
                }))"
                :bordered="false"
                size="small"
                :max-height="300"
              />
            </div>
            <NEmpty v-else description="暂无数据" />
          </NCard>
        </NGi>
      </NGrid>

      <!-- 领域 + 等级分布 -->
      <NGrid :cols="2" :x-gap="24" style="margin-top: 24px" responsive="screen">
        <NGi :span="1">
          <NCard title="学历背景分布" :bordered="true" size="small">
            <div v-if="Object.keys(domainStats.by_education_background || {}).length > 0">
              <div
                v-for="(value, key) in domainStats.by_education_background"
                :key="key"
                style="display: flex; align-items: center; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #ECECEF"
              >
                <span style="font-size: 13px; color: #4B5563">{{ key }}</span>
                <NTag size="small" :bordered="false">{{ value }} 人</NTag>
              </div>
            </div>
            <NEmpty v-else description="暂无数据" />
          </NCard>
        </NGi>
        <NGi :span="1">
          <NCard title="能力等级分布" :bordered="true" size="small">
            <div v-if="levelData.length > 0">
              <div
                v-for="item in levelData"
                :key="item.name"
                style="display: flex; align-items: center; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #ECECEF"
              >
                <span style="font-size: 13px; color: #4B5563">{{ LEVEL_MAP[item.name] || item.name || '未知' }}</span>
                <NTag size="small" :bordered="false">{{ item.value }} 人</NTag>
              </div>
            </div>
            <NEmpty v-else description="暂无数据" />
          </NCard>
        </NGi>
      </NGrid>
    </NSpin>
  </div>
</template>

<style scoped>
.page-head { margin-bottom: 24px; }
.page-head-title {
  font-size: 22px; font-weight: 600; letter-spacing: -.03em;
  color: #111827; margin-bottom: 8px;
}
.page-head-desc { font-size: 14px; color: #9CA3AF; }
</style>
