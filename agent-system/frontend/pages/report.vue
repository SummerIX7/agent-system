<template>
  <div class="page page--wide">
    <div class="page-head">
      <p class="page-head__eyebrow">Step 6</p>
      <h1 class="page-head__title">学习分析报告</h1>
      <p class="page-head__desc">查看完整学习路径及各节点进度，根据需要进入学习或考核环节。</p>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="flex flex-col items-center justify-center py-20">
      <div class="spinner"></div>
      <p class="mt-4 text-text-2">加载学习路径...</p>
    </div>

    <!-- 学习路径时间线（主视图） -->
    <div v-else-if="nodes.length > 0" class="path-main">
      <div class="card" style="margin-bottom: 24px">
        <div class="card__head">
          <h2 class="card__title"> 学习路径 — 共 {{ nodes.length }} 个节点</h2>
          <span v-if="allCompleted" class="badge badge--ok">全部完成 </span>
          <span v-else class="badge badge--accent">进度 {{ completedCount }} / {{ nodes.length }}</span>
        </div>
        <p v-if="pathMeta.recommended_order" class="text-sm text-text-2 mb-4">{{ pathMeta.recommended_order }}</p>
      </div>

      <!-- 节点列表 -->
      <div class="path-timeline">
        <div
          v-for="node in nodes"
          :key="node.stage"
          class="path-node-card"
          :class="{
            'is-current': node.stage === currentStage,
            'is-done': node.advanced_test_passed || node.completed,
            'is-active': node.basic_test_passed && !node.advanced_test_passed,
          }"
        >
          <!-- 节点编号 -->
          <div class="path-node-badge" :class="nodeBadgeClass(node)">
            <template v-if="node.advanced_test_passed"></template>
            <template v-else>{{ node.stage }}</template>
          </div>

          <!-- 节点内容 -->
          <div class="path-node-body">
            <div class="path-node-header">
              <span class="path-node-title">{{ node.title }}</span>
              <span v-if="node.difficulty" class="badge" :class="difficultyBadgeClass(node.difficulty)">
                {{ difficultyLabel(node.difficulty) }}
              </span>
              <span v-if="node.advanced_test_passed" class="badge badge--ok">已通过</span>
              <span v-else-if="node.basic_test_passed" class="badge" style="background: var(--accent-soft); color: var(--accent)">基础已过</span>
              <span v-else-if="node.has_resources" class="badge badge--warn">待考核</span>
            </div>

            <div v-if="node.topics?.length" class="path-node-topics">
              {{ node.topics.join(' · ') }}
            </div>

            <div class="path-node-meta">
              <span v-if="node.estimated_hours"> {{ node.estimated_hours }} 小时</span>
              <span v-if="node.prerequisites?.length"> 前置：{{ node.prerequisites.join('、') }}</span>
            </div>

            <!-- 当前节点操作区 -->
            <div v-if="node.stage === currentStage && !node.advanced_test_passed && !allCompleted" class="path-node-actions">
              <button v-if="node.has_resources" class="btn btn--primary" @click="goToResources(node)">
                 查看学习资源
              </button>
              <button
                v-if="node.has_resources && !node.basic_test_passed"
                class="btn btn--accent"
                @click="goToPractice('basic')"
              >
                 开始基础考核
              </button>
              <button
                v-if="node.basic_test_passed && !node.advanced_test_passed"
                class="btn btn--accent"
                @click="goToPractice('advanced')"
              >
                 开始提升考核
              </button>
            </div>

            <!-- 已完成节点提示 -->
            <div v-if="node.advanced_test_passed" class="path-node-actions">
              <span class="text-sm" style="color: var(--ok)"> 本节点已通过考核</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 全部完成 -->
      <div v-if="allCompleted" class="card" style="margin-top: 24px; text-align: center; padding: 40px">
        <div style="font-size: 48px; margin-bottom: 12px"></div>
        <h2 style="font-size: 20px; font-weight: 600; margin-bottom: 8px">学习路径全部完成！</h2>
        <p class="text-text-2 mb-6">你已通过所有节点的考核，建议回顾薄弱环节或探索更深入的主题。</p>
        <NuxtLink to="/" class="btn btn--primary">返回首页</NuxtLink>
      </div>
    </div>

    <!-- 无学习路径时的降级显示 -->
    <div v-else-if="!loading" class="card" style="text-align: center; padding: 40px">
      <p class="text-text-2 mb-4">暂未生成学习路径，请先完成 Agent 协同生成。</p>
      <NuxtLink to="/workflow" class="btn btn--primary">前往 Agent 协同</NuxtLink>
    </div>

    <!-- 分隔 -->
    <hr class="section-divider" />

    <!-- 核心指标（保留原有） -->
    <div class="section-head">
      <h2 class="section-head__title">核心指标评估</h2>
      <p class="section-head__desc">系统对本轮学习闭环的关键指标进行量化评估</p>
    </div>

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

    <!-- 匹配曲线 -->
    <div class="report-grid" style="margin-top: 24px">
      <div class="card">
        <div class="card__head">
          <h2 class="card__title">学习者水平与资源难度匹配曲线</h2>
        </div>
        <div class="legend-bar">
          <div class="legend-item"><span class="legend-line" style="background: var(--accent)"></span>资源难度</div>
          <div class="legend-item"><span class="legend-line" style="background: var(--text-3); border-top: 1.5px dashed var(--text-3)"></span>学习者水平</div>
        </div>
        <ReportDifficultyMatchCurve :data="matchCurveData" />
      </div>

      <!-- 匹配曲线说明 -->
      <div class="card">
        <div class="card__head">
          <h2 class="card__title">学习统计</h2>
        </div>
        <div style="font-size: 13px; color: var(--text-2); line-height: 2">
          <div> 学习路径节点：<strong>{{ nodes.length }}</strong> 个</div>
          <div> 已完成节点：<strong>{{ completedCount }}</strong> 个</div>
          <div> 当前节点：<strong>{{ currentNodeTitle }}</strong></div>
          <div> 预估总时长：<strong>{{ pathMeta.total_estimated_hours || '--' }}</strong> 小时</div>
          <div> 整体进度：<strong>{{ nodes.length ? Math.round(completedCount / nodes.length * 100) : 0 }}%</strong></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const router = useRouter()
const api = useApi()
const { sessionId, profile } = useSession()
const { nodes, currentStage, allCompleted, fetchLearningPath } = useLearningPath()

const loading = ref(true)

const pathMeta = ref({
  total_estimated_hours: 0,
  recommended_order: '',
})

const matchCurveData = ref({
  learnerLevel: 2.5,
  resources: [] as any[],
})

const metrics = ref({
  hallucination_rate: null as number | null,
  difficulty_match_rate: null as number | null,
  knowledge_coverage_rate: null as number | null,
})

// 计算属性
const completedCount = computed(() =>
  nodes.value.filter(n => n.advanced_test_passed || n.completed).length
)

const currentNodeTitle = computed(() => {
  const node = nodes.value.find(n => n.stage === currentStage.value)
  return node?.title || '暂无'
})

// 节点徽章样式
const nodeBadgeClass = (node: any) => ({
  'done': node.advanced_test_passed,
  'active': node.basic_test_passed && !node.advanced_test_passed,
  'current': node.stage === currentStage.value && !node.advanced_test_passed,
})

// 难度标签
const difficultyLabel = (d: string) => {
  const map: Record<string, string> = { beginner: '初级', intermediate: '中级', advanced: '高级', expert: '专家' }
  return map[d] || d
}
const difficultyBadgeClass = (d: string) => {
  const map: Record<string, string> = { beginner: 'badge--mute', intermediate: 'badge--accent', advanced: 'badge--warn', expert: 'badge--err' }
  return map[d] || 'badge--mute'
}

// 导航
const goToResources = (node: any) => {
  router.push({
    path: '/resources',
    query: { stage: String(node.stage) },
  })
}

const goToPractice = (level: string) => {
  router.push({
    path: '/practice',
    query: { level },
  })
}

// 初始化
onMounted(async () => {
  loading.value = true

  // 并行加载学习路径和可视化数据
  if (sessionId.value) {
    try {
      const [pathData, vizData] = await Promise.allSettled([
        api.getLearningPath(sessionId.value),
        api.getVisualization(sessionId.value).catch(() => null),
      ])

      // 学习路径
      if (pathData.status === 'fulfilled' && pathData.value) {
        nodes.value = pathData.value.nodes || []
        currentStage.value = pathData.value.current_stage || 1
        allCompleted.value = pathData.value.all_completed || false
        pathMeta.value = {
          total_estimated_hours: pathData.value.total_estimated_hours || 0,
          recommended_order: pathData.value.recommended_order || '',
        }
      }

      // 可视化数据（指标 + 匹配曲线）
      const viz = vizData.status === 'fulfilled' ? vizData.value : null
      if (viz) {
        if (viz.match_curve) {
          matchCurveData.value = {
            learnerLevel: viz.match_curve.learner_level === 'advanced' ? 4 :
                          viz.match_curve.learner_level === 'intermediate' ? 3 : 2,
            resources: viz.match_curve.resources || [],
          }
        }
        if (viz.metrics) {
          metrics.value = viz.metrics
        }
      }
    } catch (err) {
      console.warn('获取报告数据失败:', err)
    }
  }

  // 降级：从 profile 填充
  if (!nodes.value.length && profile.value?.knowledge_points) {
    nodes.value = profile.value.knowledge_points.map((kp: any, idx: number) => ({
      stage: idx + 1,
      title: kp.name,
      difficulty: kp.level || 'beginner',
      topics: [kp.name],
      estimated_hours: 4,
      has_resources: true,
      basic_test_passed: kp.score >= 60,
      advanced_test_passed: kp.score >= 80,
      completed: kp.score >= 80,
    }))
    currentStage.value = 1
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

  loading.value = false
})
</script>

<style scoped>
/* ── 学习路径时间线 ── */
.path-main {
  margin-bottom: 8px;
}
.path-timeline {
  position: relative;
  padding-left: 0;
}
.path-node-card {
  display: flex;
  gap: 20px;
  padding: 20px 24px;
  margin-bottom: 0;
  border-left: 2px solid var(--line);
  position: relative;
  transition: border-color .2s;
}
.path-node-card:last-child {
  border-left-color: transparent;
}
.path-node-card.is-done {
  border-left-color: var(--ok);
}
.path-node-card.is-active {
  border-left-color: var(--accent);
}
.path-node-card.is-current {
  border-left-color: var(--accent);
  background: linear-gradient(90deg, var(--accent-soft) 0%, transparent 100%);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}

/* 节点徽章 */
.path-node-badge {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  background: var(--bg-muted);
  color: var(--text-3);
  border: 2px solid var(--line);
  position: relative;
  z-index: 1;
  margin-left: -20px;
}
.path-node-badge.done {
  background: var(--ok);
  color: #fff;
  border-color: var(--ok);
}
.path-node-badge.active {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}
.path-node-badge.current {
  background: #fff;
  color: var(--accent);
  border-color: var(--accent);
  box-shadow: 0 0 0 4px var(--accent-soft);
}

/* 节点内容 */
.path-node-body {
  flex: 1;
  min-width: 0;
  padding-top: 2px;
}
.path-node-header {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.path-node-title {
  font-size: 15px;
  font-weight: 600;
}
.path-node-topics {
  font-size: 13px;
  color: var(--text-2);
  margin-top: 6px;
  line-height: 1.6;
}
.path-node-meta {
  font-size: 12px;
  color: var(--text-3);
  margin-top: 8px;
  display: flex;
  gap: 16px;
}

/* 当前节点操作按钮 */
.path-node-actions {
  display: flex;
  gap: 10px;
  margin-top: 14px;
  flex-wrap: wrap;
}

.btn--accent {
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  padding: 10px 20px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity .15s;
}
.btn--accent:hover { opacity: .85; }

/* ── 分隔线 ── */
.section-divider {
  border: none;
  border-top: 1px solid var(--line);
  margin: 32px 0;
}
.section-head {
  margin-bottom: 20px;
}
.section-head__title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 4px;
}
.section-head__desc {
  font-size: 13px;
  color: var(--text-2);
}

/* ── 指标卡片 ── */
.metric-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1px;
  background: var(--line);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  overflow: hidden;
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

/* ── spinner ── */
.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid var(--line);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@media (max-width: 760px) {
  .metric-grid { grid-template-columns: 1fr; }
  .report-grid { grid-template-columns: 1fr; }
}
</style>
