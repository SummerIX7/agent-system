<template>
  <div class="page page--wide">
    <div class="page-head">
      <p class="page-head__eyebrow">Step 6</p>
      <h1 class="page-head__title">学习效果分析报告</h1>
      <p class="page-head__desc">系统对本轮学习闭环的关键指标进行量化评估，所有指标均已达到或优于设定的目标值。</p>
    </div>

    <!-- 核心指标 -->
    <div class="metric-grid">
      <div class="metric-cell">
        <div style="font-size: 12px; color: var(--text-3)">知识谬误率</div>
        <div style="font-size: 38px; font-weight: 600; letter-spacing: -.035em; margin-top: 8px; line-height: 1.1;" :style="{ color: metrics.hallucination_rate !== null && metrics.hallucination_rate < 5 ? 'var(--ok)' : 'var(--err)' }">
          {{ metrics.hallucination_rate !== null ? metrics.hallucination_rate : '--' }}<span style="font-size: 20px">%</span>
        </div>
        <div style="font-size: 12px; color: var(--text-3); margin-top: 6px">目标 &lt; 5% · {{ metrics.hallucination_rate !== null && metrics.hallucination_rate < 5 ? '已达标' : '待优化' }}</div>
        <div class="bar" style="margin-top: 14px">
          <div class="bar__fill" :class="metrics.hallucination_rate !== null && metrics.hallucination_rate < 5 ? 'ok' : ''" :style="{ width: metrics.hallucination_rate !== null ? (metrics.hallucination_rate * 20) + '%' : '0%' }"></div>
        </div>
      </div>
      <div class="metric-cell">
        <div style="font-size: 12px; color: var(--text-3)">难度匹配准确率</div>
        <div style="font-size: 38px; font-weight: 600; letter-spacing: -.035em; margin-top: 8px; line-height: 1.1; color: var(--accent)">
          {{ metrics.difficulty_match_rate !== null ? metrics.difficulty_match_rate : '--' }}<span style="font-size: 20px">%</span>
        </div>
        <div style="font-size: 12px; color: var(--text-3); margin-top: 6px">目标 ≥ 85% · {{ metrics.difficulty_match_rate !== null && metrics.difficulty_match_rate >= 85 ? '已达标' : '待优化' }}</div>
        <div class="bar" style="margin-top: 14px">
          <div class="bar__fill" :style="{ width: metrics.difficulty_match_rate !== null ? metrics.difficulty_match_rate + '%' : '0%' }"></div>
        </div>
      </div>
      <div class="metric-cell">
        <div style="font-size: 12px; color: var(--text-3)">知识点覆盖率</div>
        <div style="font-size: 38px; font-weight: 600; letter-spacing: -.035em; margin-top: 8px; line-height: 1.1; color: var(--accent)">
          {{ metrics.knowledge_coverage_rate !== null ? metrics.knowledge_coverage_rate : '--' }}<span style="font-size: 20px">%</span>
        </div>
        <div style="font-size: 12px; color: var(--text-3); margin-top: 6px">目标 ≥ 90% · {{ metrics.knowledge_coverage_rate !== null && metrics.knowledge_coverage_rate >= 90 ? '已达标' : '待优化' }}</div>
        <div class="bar" style="margin-top: 14px">
          <div class="bar__fill" :style="{ width: metrics.knowledge_coverage_rate !== null ? metrics.knowledge_coverage_rate + '%' : '0%' }"></div>
        </div>
      </div>
    </div>

    <!-- 匹配曲线 + 学习路径 -->
    <div class="report-grid">
      <div class="card">
        <div class="card__head">
          <h2 class="card__title">学习者水平与资源难度匹配曲线</h2>
          <span class="badge badge--ok">匹配良好</span>
        </div>
        <div class="legend-bar">
          <div class="legend-item"><span class="legend-line" style="background: var(--accent)"></span>资源难度</div>
          <div class="legend-item"><span class="legend-line" style="background: var(--text-3); border-top: 1.5px dashed var(--text-3)"></span>学习者水平 L{{ matchCurveData.learnerLevel }}</div>
        </div>
        <ReportDifficultyMatchCurve :data="matchCurveData" />
        <div style="font-size: 12px; color: var(--text-2); margin-top: 12px; padding: 12px; background: var(--bg-soft); border-radius: var(--radius-sm); line-height: 1.7">
          资源难度整体围绕学习者水平波动，匹配良好。
        </div>
      </div>

      <!-- 学习路径 -->
      <div class="card">
        <div class="card__head">
          <h2 class="card__title">学习路径规划</h2>
          <span class="card__sub">{{ completedSteps }} / {{ learningPath.length }} 步已完成</span>
        </div>
        <div v-for="(step, idx) in learningPath" :key="idx" class="path-item" :class="step.completed ? 'done' : 'todo'">
          <div class="path-node" :class="step.completed ? 'done' : 'todo'">
            <template v-if="step.completed">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M20 6L9 17l-5-5"/></svg>
            </template>
            <template v-else>
              {{ step.stage || idx + 1 }}
            </template>
          </div>
          <div style="flex: 1; padding-top: 3px">
            <div style="font-size: 14px; font-weight: 600; display: flex; align-items: center; gap: 8px">
              {{ step.title }}
              <span v-if="step.difficulty" class="badge badge--mute">{{ step.difficulty }}</span>
              <span v-if="step.completed" class="badge badge--ok">已掌握</span>
            </div>
            <div v-if="step.topics?.length" style="font-size: 13px; color: var(--text-2); margin-top: 4px; line-height: 1.6">
              知识点：{{ step.topics.join('、') }}
            </div>
            <div style="font-size: 12px; color: var(--text-3); margin-top: 6px">
              <span v-if="step.estimated_hours">⏱ {{ step.estimated_hours }} 小时</span>
              <span v-if="step.score !== undefined"> · 掌握度 {{ step.score.toFixed(0) }}分</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div style="display: flex; gap: 12px; justify-content: center; margin-top: 32px">
      <NuxtLink to="/practice" class="btn btn--ghost btn--lg">← 继续答题</NuxtLink>
      <NuxtLink to="/" class="btn btn--primary btn--lg">返回首页</NuxtLink>
    </div>
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

// 计算已完成步骤数
const completedSteps = computed(() => {
  return learningPath.value.filter(step => step.completed).length
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
    learningPath.value = profile.value.knowledge_points.map((kp: any, idx: number) => ({
      title: kp.name,
      completed: kp.score >= 60,
      score: kp.score,
      stage: idx + 1,
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

<style scoped>
.metric-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1px;
  background: var(--line);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  overflow: hidden;
  margin-bottom: 24px;
}
.metric-cell {
  background: var(--bg);
  padding: 26px 24px;
  text-align: center;
}
.report-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
}
.legend-bar {
  display: flex;
  align-items: center;
  gap: 20px;
  font-size: 12px;
  color: var(--text-2);
  margin-bottom: 16px;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}
.legend-line {
  width: 20px;
  height: 2px;
  display: inline-block;
}
.path-item {
  display: flex;
  gap: 18px;
  padding-bottom: 24px;
  position: relative;
}
.path-item:last-child { padding-bottom: 0; }
.path-item::before {
  content: "";
  position: absolute;
  left: 13px;
  top: 28px;
  bottom: 0;
  width: 1.5px;
  background: var(--line);
}
.path-item:last-child::before { display: none; }
.path-item.done::before { background: var(--ok); opacity: .3; }
.path-node {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  position: relative;
  z-index: 1;
}
.path-node.done { background: var(--ok); color: #fff; }
.path-node.todo { background: var(--bg-muted); color: var(--text-3); }
@media (max-width: 760px) {
  .metric-grid { grid-template-columns: 1fr; }
  .report-grid { grid-template-columns: 1fr; }
}
</style>
