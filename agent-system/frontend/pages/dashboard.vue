<template>
  <div class="container mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold mb-6">学情诊断仪表盘</h1>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <!-- 知识雷达图 -->
      <UCard>
        <template #header>
          <h2 class="text-lg font-semibold">知识掌握雷达图</h2>
        </template>
        <DashboardKnowledgeRadar :knowledge-points="knowledgePoints" />
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
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
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

// 从全局状态获取画像数据
if (profile.value?.knowledge_points) {
  knowledgePoints.value = profile.value.knowledge_points
  blindSpots.value = (profile.value.blind_spots || []).map((bs: string) => ({
    name: bs,
    severity: 0.7,
  }))
}

// 尝试从后端获取最新可视化数据
onMounted(async () => {
  if (sessionId.value) {
    try {
      const viz = await api.getVisualization(sessionId.value)
      if (viz.knowledge_points?.length) {
        knowledgePoints.value = viz.knowledge_points
      }
      if (viz.blind_spots?.length) {
        blindSpots.value = viz.blind_spots
      }
    } catch (err) {
      console.warn('获取可视化数据失败，使用画像数据:', err)
    }
  }
})
</script>
