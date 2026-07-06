<template>
  <div class="page page--wide">
    <div class="page-head">
      <p class="page-head__eyebrow">步骤 6</p>
      <h1 class="page-head__title">学习分析报告</h1>
      <p class="page-head__desc">汇总学习完成情况、练习表现、资源匹配质量和后续改进建议。</p>
    </div>

    <div v-if="loading" class="flex flex-col items-center justify-center py-20">
      <div class="spinner"></div>
      <p class="mt-4 text-text-2">正在生成分析报告...</p>
    </div>

    <template v-else>
      <div v-if="nodes.length === 0" class="card empty-card">
        <p class="text-text-2 mb-4">暂未生成学习数据，请先完成 Agent 协同生成。</p>
        <NuxtLink to="/workflow" class="btn btn--primary">前往 Agent 协同</NuxtLink>
      </div>

      <div class="summary-grid">
        <div class="summary-card">
          <div class="summary-card__label">学习节点完成度</div>
          <div class="summary-card__value">{{ completedCount }}/{{ nodes.length || 0 }}</div>
          <div class="bar"><div class="bar__fill ok" :style="{ width: progressPercent + '%' }"></div></div>
          <div class="summary-card__hint">{{ progressPercent }}% · {{ allCompleted ? '已完成全部节点' : `当前第 ${currentStage} 节` }}</div>
        </div>
        <div class="summary-card">
          <div class="summary-card__label">练习轮次</div>
          <div class="summary-card__value">{{ practiceResults.length }}</div>
          <div class="summary-card__hint">节点练习和综合练习累计次数</div>
        </div>
        <div class="summary-card">
          <div class="summary-card__label">平均正确率</div>
          <div class="summary-card__value">{{ averagePracticeScore }}%</div>
          <div class="summary-card__hint">{{ averagePracticeScore >= 70 ? '整体达标' : '建议继续巩固' }}</div>
        </div>
        <div class="summary-card">
          <div class="summary-card__label">综合练习</div>
          <div class="summary-card__value">{{ comprehensiveResult ? `${comprehensiveResult.score}%` : '--' }}</div>
          <div class="summary-card__hint">{{ comprehensiveHint }}</div>
        </div>
      </div>

      <div class="report-grid" style="margin-top: 24px">
        <div class="card">
          <div class="card__head">
            <h2 class="card__title">练习表现分析</h2>
            <span class="badge badge--mute">{{ latestResults.length }} 条近期记录</span>
          </div>
          <div v-if="latestResults.length" class="practice-list">
            <div v-for="item in latestResults" :key="item.created_at" class="practice-item">
              <div>
                <div class="practice-item__title">{{ levelName(item.level) }}</div>
                <div class="practice-item__meta">
                  {{ item.stage ? `节点 ${item.stage}` : '最终综合' }} · {{ formatDate(item.created_at) }}
                </div>
              </div>
              <div class="practice-item__score" :class="{ ok: item.score >= 70, warn: item.score < 70 }">{{ item.score }}%</div>
            </div>
          </div>
          <div v-else class="muted-box">暂无练习记录，完成一轮答题后这里会展示得分趋势。</div>
        </div>

        <div class="card">
          <div class="card__head">
            <h2 class="card__title">综合练习结果</h2>
          </div>
          <template v-if="comprehensiveResult">
            <div class="final-score" :class="{ ok: comprehensiveResult.score >= 70 }">{{ comprehensiveResult.score }}%</div>
            <p class="text-text-2" style="line-height: 1.8">
              综合练习覆盖真实业务场景，包含图纸/工艺理解、装夹找正、程序识读、首件检测和异常处理。
              本次答对 {{ comprehensiveResult.correct_count }}/{{ comprehensiveResult.question_count }} 题。
            </p>
          </template>
          <template v-else>
            <div class="muted-box">
              {{ allCompleted ? '全部节点已完成，建议进入综合练习验证真实场景处理能力。' : '完成全部学习节点后解锁最终综合练习。' }}
            </div>
            <NuxtLink v-if="allCompleted" to="/practice?level=comprehensive" class="btn btn--primary mt-4">进入综合练习</NuxtLink>
          </template>
        </div>
      </div>

      <div class="report-grid" style="margin-top: 24px">
        <div class="card">
          <div class="card__head">
            <h2 class="card__title">薄弱项与复习建议</h2>
          </div>
          <div v-if="weakItems.length" class="weak-list">
            <div v-for="item in weakItems" :key="item.question" class="weak-item">
              <span class="weak-item__count">{{ item.count }}次</span>
              <span>{{ item.question }}</span>
            </div>
          </div>
          <div v-else class="muted-box">暂无明显薄弱项。后续练习错误会在这里聚合。</div>
        </div>

        <div class="card">
          <div class="card__head">
            <h2 class="card__title">后续建议</h2>
          </div>
          <div class="advice-list">
            <div v-if="!allCompleted">继续学习第 {{ currentStage }} 节资源，完成后在学习资源页解锁下一节点。</div>
            <div v-else-if="!comprehensiveResult">进入综合练习，验证完整业务场景处理能力。</div>
            <div v-else-if="comprehensiveResult.score < 70">复盘综合练习错题，重点回看测量、报警和程序识读相关资源。</div>
            <div v-else>综合练习已达标，可准备提交机台使用申请或进入实操训练。</div>
          </div>
          <div v-if="allCompleted" class="machine-block">
            <button
              v-if="machineStatus === 'none' || machineStatus === 'rejected'"
              class="btn btn--primary"
              :disabled="applyingMachine"
              @click="handleApplyMachine"
            >
              {{ applyingMachine ? '提交中...' : '申请机台使用' }}
            </button>
            <div v-else class="machine-status" :class="machineStatus === 'approved' ? 'machine-status--approved' : 'machine-status--pending'">
              {{ machineStatus === 'approved' ? '机台使用权限已批准' : '机台使用申请审批中' }}
            </div>
          </div>
        </div>
      </div>

      <hr class="section-divider" />

      <div class="section-head">
        <h2 class="section-head__title">资源质量与匹配评估</h2>
        <p class="section-head__desc">系统对本轮学习闭环的关键指标进行量化评估</p>
      </div>

      <div class="metric-grid">
        <div class="metric-cell">
          <div class="metric-cell__label">知识谬误率</div>
          <div class="metric-cell__value" :style="{ color: metrics.hallucination_rate !== null && metrics.hallucination_rate < 5 ? 'var(--ok)' : 'var(--err)' }">
            {{ metrics.hallucination_rate !== null ? metrics.hallucination_rate : '--' }}<span>%</span>
          </div>
          <div class="metric-cell__hint">目标 &lt; 5% · {{ metrics.hallucination_rate !== null && metrics.hallucination_rate < 5 ? '已达标' : '待优化' }}</div>
        </div>
        <div class="metric-cell">
          <div class="metric-cell__label">难度匹配准确率</div>
          <div class="metric-cell__value accent">{{ metrics.difficulty_match_rate !== null ? metrics.difficulty_match_rate : '--' }}<span>%</span></div>
          <div class="metric-cell__hint">目标 ≥ 85% · {{ metrics.difficulty_match_rate !== null && metrics.difficulty_match_rate >= 85 ? '已达标' : '待优化' }}</div>
        </div>
        <div class="metric-cell">
          <div class="metric-cell__label">知识点覆盖率</div>
          <div class="metric-cell__value accent">{{ metrics.knowledge_coverage_rate !== null ? metrics.knowledge_coverage_rate : '--' }}<span>%</span></div>
          <div class="metric-cell__hint">目标 ≥ 90% · {{ metrics.knowledge_coverage_rate !== null && metrics.knowledge_coverage_rate >= 90 ? '已达标' : '待优化' }}</div>
        </div>
      </div>

      <div class="card" style="margin-top: 24px">
        <div class="card__head">
          <h2 class="card__title">学习者水平与资源难度匹配曲线</h2>
        </div>
        <div class="legend-bar">
          <div class="legend-item"><span class="legend-line" style="background: var(--accent)"></span>资源难度</div>
          <div class="legend-item"><span class="legend-line" style="background: var(--text-3); border-top: 1.5px dashed var(--text-3)"></span>学习者水平</div>
        </div>
        <ClientOnly>
          <ReportDifficultyMatchCurve :data="matchCurveData" />
          <template #fallback>
            <div class="chart-fallback">加载图表中...</div>
          </template>
        </ClientOnly>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
const api = useApi()
const { sessionId } = useSession()
const { nodes, currentStage, allCompleted } = useLearningPath()

const loading = ref(true)
const practiceResults = ref<any[]>([])
const machineStatus = ref<string>('none')
const applyingMachine = ref(false)

const matchCurveData = ref({
  learnerLevel: 2.5,
  resources: [] as any[],
})

const metrics = ref({
  hallucination_rate: null as number | null,
  difficulty_match_rate: null as number | null,
  knowledge_coverage_rate: null as number | null,
})

const completedCount = computed(() =>
  nodes.value.filter(n => n.completed || n.advanced_test_passed).length
)
const progressPercent = computed(() => nodes.value.length ? Math.round(completedCount.value / nodes.value.length * 100) : 0)
const averagePracticeScore = computed(() => {
  if (!practiceResults.value.length) return 0
  const total = practiceResults.value.reduce((sum, item) => sum + Number(item.score || 0), 0)
  return Math.round(total / practiceResults.value.length)
})
const latestResults = computed(() => [...practiceResults.value].reverse().slice(0, 6))
const comprehensiveResult = computed(() =>
  [...practiceResults.value].reverse().find(item => item.level === 'comprehensive')
)
const comprehensiveHint = computed(() => {
  if (comprehensiveResult.value) return comprehensiveResult.value.score >= 70 ? '最终场景练习已达标' : '最终场景练习需复盘'
  return allCompleted.value ? '已解锁，待完成' : '完成全部节点后解锁'
})
const weakItems = computed(() => {
  const counter = new Map<string, number>()
  practiceResults.value.forEach(item => {
    ;(item.questions || []).forEach((q: any) => {
      if (q.is_correct === false && q.question) {
        counter.set(q.question, (counter.get(q.question) || 0) + 1)
      }
    })
  })
  return Array.from(counter.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([question, count]) => ({ question, count }))
})

const levelName = (level: string) => {
  const map: Record<string, string> = { node: '节点练习', basic: '节点练习', advanced: '节点练习', comprehensive: '综合练习' }
  return map[level] || level
}

const formatDate = (value: string) => {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return `${date.getMonth() + 1}/${date.getDate()} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

const handleApplyMachine = async () => {
  applyingMachine.value = true
  try {
    const result = await api.applyMachine()
    machineStatus.value = result.status
  } catch (err: any) {
    console.warn('机台申请失败:', err)
  } finally {
    applyingMachine.value = false
  }
}

onMounted(async () => {
  loading.value = true
  if (sessionId.value) {
    try {
      const [pathData, vizData, practiceData] = await Promise.allSettled([
        api.getLearningPath(sessionId.value),
        api.getVisualization(sessionId.value).catch(() => null),
        api.getPracticeResults(sessionId.value).catch(() => ({ results: [] })),
      ])

      if (pathData.status === 'fulfilled' && pathData.value) {
        nodes.value = pathData.value.nodes || []
        currentStage.value = pathData.value.current_stage || 1
        allCompleted.value = pathData.value.all_completed || false
      }

      const viz = vizData.status === 'fulfilled' ? vizData.value : null
      if (viz) {
        if (viz.match_curve) {
          matchCurveData.value = {
            learnerLevel: viz.match_curve.learner_level === 'advanced' ? 4 :
                          viz.match_curve.learner_level === 'intermediate' ? 3 : 2,
            resources: viz.match_curve.resources || [],
          }
        }
        if (viz.metrics) metrics.value = viz.metrics
      }

      if (practiceData.status === 'fulfilled') {
        practiceResults.value = practiceData.value.results || []
      }
    } catch (err) {
      console.warn('获取报告数据失败:', err)
    }

    try {
      const profile = await api.getMyProfile()
      machineStatus.value = (profile as any).machine_approval_status || 'none'
    } catch {
      // 用户尚未建档时忽略
    }
  }
  loading.value = false
})
</script>

<style scoped>
.empty-card { text-align: center; padding: 40px; }
.summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.summary-card { background: var(--bg); border: 1px solid var(--line); border-radius: var(--radius); padding: 22px 20px; }
.summary-card__label { font-size: 12px; color: var(--text-3); margin-bottom: 10px; }
.summary-card__value { font-size: 34px; font-weight: 700; letter-spacing: -.04em; color: var(--text); line-height: 1.1; }
.summary-card__hint { font-size: 12px; color: var(--text-2); margin-top: 10px; }
.report-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 24px; }
.practice-list { display: flex; flex-direction: column; gap: 10px; }
.practice-item { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 14px; border: 1px solid var(--line); border-radius: var(--radius-sm); }
.practice-item__title { font-size: 14px; font-weight: 600; }
.practice-item__meta { font-size: 12px; color: var(--text-3); margin-top: 3px; }
.practice-item__score { font-family: var(--mono); font-size: 20px; font-weight: 700; }
.practice-item__score.ok { color: var(--ok); }
.practice-item__score.warn { color: var(--warn); }
.final-score { font-family: var(--mono); font-size: 52px; font-weight: 800; letter-spacing: -.05em; color: var(--warn); margin-bottom: 12px; }
.final-score.ok { color: var(--ok); }
.muted-box { color: var(--text-2); background: var(--bg-muted); border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 16px; line-height: 1.7; font-size: 13px; }
.weak-list { display: flex; flex-direction: column; gap: 10px; }
.weak-item { display: flex; align-items: flex-start; gap: 10px; padding: 12px; border: 1px solid var(--line); border-radius: var(--radius-sm); font-size: 13px; line-height: 1.6; }
.weak-item__count { flex-shrink: 0; font-family: var(--mono); color: var(--err); background: var(--err-soft); border-radius: 99px; padding: 2px 8px; font-size: 12px; }
.advice-list { color: var(--text-2); line-height: 1.8; font-size: 14px; }
.machine-block { margin-top: 18px; }
.machine-status { display: inline-flex; align-items: center; padding: 10px 16px; border-radius: var(--radius-sm); font-size: 13px; font-weight: 600; }
.machine-status--pending { background: #FFFBEB; color: #D97706; border: 1px solid #FDE68A; }
.machine-status--approved { background: #ECFDF5; color: #059669; border: 1px solid #A7F3D0; }
.section-divider { border: none; border-top: 1px solid var(--line); margin: 32px 0; }
.section-head { margin-bottom: 20px; }
.section-head__title { font-size: 18px; font-weight: 600; margin-bottom: 4px; }
.section-head__desc { font-size: 13px; color: var(--text-2); }
.metric-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1px; background: var(--line); border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; }
.metric-cell { background: var(--bg); padding: 26px 24px; text-align: center; }
.metric-cell__label { font-size: 12px; color: var(--text-3); }
.metric-cell__value { font-size: 38px; font-weight: 700; letter-spacing: -.04em; margin-top: 8px; line-height: 1.1; }
.metric-cell__value span { font-size: 20px; }
.metric-cell__value.accent { color: var(--accent); }
.metric-cell__hint { font-size: 12px; color: var(--text-3); margin-top: 6px; }
.legend-bar { display: flex; align-items: center; gap: 20px; font-size: 12px; color: var(--text-2); margin-bottom: 16px; }
.legend-item { display: flex; align-items: center; gap: 6px; }
.legend-line { width: 20px; height: 2px; display: inline-block; }
.chart-fallback { height: 300px; display: flex; align-items: center; justify-content: center; color: var(--text-3); font-size: 14px; }
.spinner { width: 48px; height: 48px; border: 4px solid var(--line); border-top-color: var(--accent); border-radius: 50%; animation: spin 1s linear infinite; }
.bar { height: 6px; background: var(--line); border-radius: 3px; overflow: hidden; margin-top: 12px; }
.bar__fill { height: 100%; border-radius: 3px; transition: width .4s ease; background: var(--accent); }
.bar__fill.ok { background: var(--ok); }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@media (max-width: 960px) {
  .summary-grid { grid-template-columns: repeat(2, 1fr); }
  .report-grid { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
  .summary-grid, .metric-grid { grid-template-columns: 1fr; }
}
</style>
