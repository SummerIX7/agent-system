<template>
  <div class="container mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold mb-6">学情诊断仪表盘</h1>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <!-- 知识雷达图 -->
      <UCard>
        <template #header>
          <h2 class="text-lg font-semibold">知识掌握雷达图</h2>
        </template>
        <DashboardKnowledgeRadar
          v-if="knowledgePoints.length > 0"
          :key="radarKey"
          :knowledge-points="knowledgePoints"
        />
        <p v-else class="text-gray-400 text-center py-12">暂无诊断数据</p>
      </UCard>

      <!-- 知识盲区 -->
      <UCard>
        <template #header>
          <h2 class="text-lg font-semibold">知识盲区定位</h2>
        </template>
        <div class="space-y-3">
          <div
            v-for="spot in blindSpots"
            :key="spot.name"
            class="flex items-center justify-between p-3 rounded-lg bg-red-50 border border-red-200"
          >
            <span class="font-medium text-red-800">{{ spot.name }}</span>
            <UBadge :color="spot.severity > 0.7 ? 'red' : 'orange'">
              严重度 {{ (spot.severity * 100).toFixed(0) }}%
            </UBadge>
          </div>
          <p v-if="blindSpots.length === 0" class="text-gray-500 text-center py-4">
            暂无检测到的知识盲区
          </p>
        </div>
      </UCard>
    </div>

    <!-- 能力维度分析 -->
    <UCard class="mt-8">
      <template #header>
        <h2 class="text-lg font-semibold">能力维度分析</h2>
      </template>
      <div v-if="knowledgePoints.length > 0" class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div
          v-for="kp in knowledgePoints"
          :key="kp.name"
          class="text-center p-4 rounded-lg border"
        >
          <p class="text-sm text-gray-500">{{ kp.name }}</p>
          <p class="text-2xl font-bold mt-1">{{ kp.score.toFixed(0) }}</p>
          <UBadge class="mt-2" variant="subtle">{{ kp.level }}</UBadge>
        </div>
      </div>
      <p v-else class="text-gray-400 text-center py-8">暂无能力维度数据</p>
    </UCard>

    <!-- 操作按钮 -->
    <div class="mt-8 flex justify-center gap-4">
      <UButton to="/workflow" size="lg">
        查看 Agent 协同过程
      </UButton>
      <UButton to="/resources" variant="outline" size="lg">
        查看生成资源
      </UButton>
    </div>
  </div>
</template>

<script setup lang="ts">
const api = useApi()
const { sessionId, profile } = useSession()

const knowledgePoints = ref<any[]>([])
const blindSpots = ref<any[]>([])
const radarKey = ref(0)

const sanitizeKnowledgePoints = (kps: any[]): any[] => {
  if (!Array.isArray(kps)) return []
  return kps
    .filter((kp) => kp && typeof kp === 'object' && kp.name)
    .map((kp) => ({
      name: String(kp.name),
      score: typeof kp.score === 'number' ? kp.score : Number(kp.score) || 0,
      level: kp.level || 'beginner',
    }))
}

onMounted(async () => {
  // 先从全局 profile 加载
  if (profile.value?.knowledge_points?.length) {
    knowledgePoints.value = sanitizeKnowledgePoints(profile.value.knowledge_points)
    blindSpots.value = (profile.value.blind_spots || []).map((bs: any) => {
      if (typeof bs === 'string') return { name: bs, severity: 0.7 }
      return { name: bs.name || '未知', severity: bs.severity || 0.7 }
    })
    radarKey.value++
  }

  // 再从后端获取最新数据
  if (sessionId.value) {
    try {
      const viz = await api.getVisualization(sessionId.value)
      if (viz.knowledge_points?.length) {
        knowledgePoints.value = sanitizeKnowledgePoints(viz.knowledge_points)
        radarKey.value++
      }
      if (viz.blind_spots?.length) {
        blindSpots.value = viz.blind_spots.map((bs: any) => ({
          name: bs.name || '未知',
          severity: typeof bs.severity === 'number' ? bs.severity : 0.7,
        }))
      }
    } catch (err) {
      console.warn('获取可视化数据失败，使用画像数据:', err)
    }
  }
})
</script>
