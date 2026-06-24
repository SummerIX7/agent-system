<template>
  <div class="container mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold mb-6">分析报告</h1>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <!-- 匹配曲线 -->
      <UCard>
        <template #header>
          <h2 class="text-lg font-semibold">学习者水平与资源难度匹配曲线</h2>
        </template>
        <ReportDifficultyMatchCurve :data="matchCurveData" />
      </UCard>

      <!-- 学习路径规划 -->
      <UCard>
        <template #header>
          <h2 class="text-lg font-semibold">学习路径规划</h2>
        </template>
        <div class="space-y-4">
          <div v-for="(step, index) in learningPath" :key="index" class="flex gap-4">
            <div class="flex flex-col items-center">
              <div
                class="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold"
                :class="step.completed ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-600'"
              >
                {{ index + 1 }}
              </div>
              <div v-if="index < learningPath.length - 1" class="w-0.5 h-full bg-gray-200 mt-1" />
            </div>
            <div class="pb-4">
              <p class="font-semibold" :class="step.completed ? 'text-green-700' : ''">
                {{ step.title }}
              </p>
              <p v-if="step.score !== undefined" class="text-sm text-gray-500 mt-1">
                掌握度: {{ step.score.toFixed(0) }}分
              </p>
              <UBadge v-if="step.completed" color="green" variant="subtle" class="mt-1">
                已掌握
              </UBadge>
            </div>
          </div>
        </div>
      </UCard>
    </div>

    <!-- 综合报告 -->
    <UCard class="mt-8">
      <template #header>
        <h2 class="text-lg font-semibold">综合报告</h2>
      </template>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="text-center p-4 rounded-lg border">
          <p class="text-sm text-gray-500">知识谬误率</p>
          <p class="text-3xl font-bold" :class="(metrics.hallucination_rate ?? 100) < 5 ? 'text-green-600' : 'text-red-600'">
            {{ metrics.hallucination_rate !== null ? metrics.hallucination_rate + '%' : '--' }}
          </p>
          <p class="text-xs text-gray-400 mt-1">目标 < 5%</p>
        </div>
        <div class="text-center p-4 rounded-lg border">
          <p class="text-sm text-gray-500">难度匹配准确率</p>
          <p class="text-3xl font-bold" :class="(metrics.difficulty_match_rate ?? 0) >= 85 ? 'text-primary' : 'text-red-600'">
            {{ metrics.difficulty_match_rate !== null ? metrics.difficulty_match_rate + '%' : '--' }}
          </p>
          <p class="text-xs text-gray-400 mt-1">目标 ≥ 85%</p>
        </div>
        <div class="text-center p-4 rounded-lg border">
          <p class="text-sm text-gray-500">知识点覆盖率</p>
          <p class="text-3xl font-bold" :class="(metrics.knowledge_coverage_rate ?? 0) >= 90 ? 'text-primary' : 'text-red-600'">
            {{ metrics.knowledge_coverage_rate !== null ? metrics.knowledge_coverage_rate + '%' : '--' }}
          </p>
          <p class="text-xs text-gray-400 mt-1">目标 ≥ 90%</p>
        </div>
      </div>
    </UCard>
  </div>
</template>

<script setup lang="ts">
const api = useApi()
const { sessionId, profile } = useSession()

const matchCurveData = ref({
  learnerLevel: 2.5,
  resources: [] as any[],
})

const learningPath = ref<any[]>([])

const metrics = ref({
  hallucination_rate: null as number | null,
  difficulty_match_rate: null as number | null,
  knowledge_coverage_rate: null as number | null,
})

onMounted(async () => {
  if (sessionId.value) {
    try {
      const viz = await api.getVisualization(sessionId.value)

      // 学习路径
      if (viz.learning_path?.length) {
        learningPath.value = viz.learning_path
      }

      // 匹配曲线
      if (viz.match_curve) {
        matchCurveData.value = {
          learnerLevel: viz.match_curve.learner_level === 'advanced' ? 4 :
                        viz.match_curve.learner_level === 'intermediate' ? 3 : 2,
          resources: viz.match_curve.resources || [],
        }
      }

      // 核心指标
      if (viz.metrics) {
        metrics.value = viz.metrics
      }
    } catch (err) {
      console.warn('获取报告数据失败:', err)
    }
  }

  // 如果没有数据，使用默认值
  if (!learningPath.value.length && profile.value?.knowledge_points) {
    learningPath.value = profile.value.knowledge_points.map((kp: any) => ({
      title: kp.name,
      completed: kp.score >= 60,
      score: kp.score,
    }))
  }

  if (!matchCurveData.value.resources.length && profile.value?.knowledge_points) {
    matchCurveData.value = {
      learnerLevel: 2.5,
      resources: profile.value.knowledge_points.map((kp: any) => ({
        name: kp.name,
        difficulty: kp.score / 20,
        match: Math.min(1, kp.score / 80),
      })),
    }
  }
})
</script>
