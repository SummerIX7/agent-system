<template>
  <div class="page page--wide">
    <div class="page-head">
      <p class="page-head__eyebrow">步骤 5</p>
      <h1 class="page-head__title">{{ testLabel }}</h1>
      <p class="page-head__desc">{{ testDescription }}</p>
    </div>

    <div v-if="nodes.length > 0" class="practice-path">
      <div class="node-selector">
        <button
          v-for="node in nodes"
          :key="node.stage"
          class="node-selector__card"
          :class="{ active: testLevel === 'node' && Number(node.stage) === selectedStage }"
          @click="switchStage(Number(node.stage))"
        >
          <span class="node-selector__stage">节点 {{ node.stage }}</span>
          <strong>{{ node.title }}</strong>
          <span class="node-selector__meta">
            {{ node.topics?.length || 0 }} 个知识点
            <template v-if="node.estimated_hours"> · {{ node.estimated_hours }} 小时</template>
          </span>
        </button>
      </div>

      <button
        class="comprehensive-node"
        :class="{ active: testLevel === 'comprehensive' }"
        @click="switchLevel('comprehensive')"
      >
        <span class="comprehensive-node__index">最终</span>
        <span class="comprehensive-node__body">
          <strong>综合练习</strong>
          <span>独立于 5 个学习节点，综合运用安全、装夹、检测、刀具、程序识读与异常处理知识</span>
        </span>
        <span class="comprehensive-node__action">
          {{ testLevel === 'comprehensive' ? '当前练习' : '进入综合练习' }}
          <span aria-hidden="true">→</span>
        </span>
      </button>
    </div>

    <section v-if="testLevel === 'comprehensive' && scenarioMarkdown && !loading" class="card scenario-card">
      <div class="scenario-card__head">
        <div>
          <span class="scenario-card__eyebrow">共享生产场景</span>
          <h2>{{ comprehensiveScenario?.title || '最终综合练习场景' }}</h2>
        </div>
        <span class="badge badge--accent">5 题共用此场景</span>
      </div>
      <MarkdownRenderer :content="scenarioMarkdown" />
    </section>

    <!-- 加载中 -->
    <div v-if="loading" class="flex flex-col items-center justify-center py-20">
      <div class="spinner"></div>
      <p class="mt-4 text-text-2">正在读取学习节点并加载试题...</p>
    </div>

    <!-- 加载失败 -->
    <div v-else-if="loadError" class="flex flex-col items-center justify-center py-20">
      <p class="text-err mb-4">{{ loadError }}</p>
      <button class="btn btn--primary" @click="initQuestions">重新加载</button>
    </div>

    <!-- 练习完成结果页 -->
    <div v-else-if="testCompleted" class="card" style="max-width: 600px; margin: 0 auto; text-align: center; padding: 40px">
      <div style="font-size: 56px; margin-bottom: 16px">{{ resultEmoji }}</div>
      <h2 style="font-size: 22px; font-weight: 600; margin-bottom: 8px">{{ resultTitle }}</h2>
      <p class="text-text-2 mb-6">{{ resultMessage }}</p>

      <!-- 分数展示 -->
      <div class="result-score">
        <span class="result-score__num">{{ accuracy }}%</span>
        <span class="result-score__label">正确率（{{ correctCount }}/{{ questions.length }}）</span>
      </div>
      <div class="bar" style="margin: 16px 0 24px">
        <div class="bar__fill" :class="passed ? 'ok' : 'err'" :style="{ width: accuracy + '%' }"></div>
      </div>

      <!-- 操作按钮 -->
      <div class="result-actions">
        <button v-if="testLevel === 'node'" class="btn btn--primary" @click="goResources">
          返回学习资源
        </button>
        <button v-if="testLevel === 'comprehensive'" class="btn btn--primary" @click="goReport">
          查看分析报告
        </button>
        <button v-else class="btn btn--ghost" @click="goReport">查看分析报告</button>
        <button class="btn btn--ghost" @click="retryTest">重新答题</button>
      </div>
      <p v-if="resultSaveError" class="text-sm text-err mt-2">{{ resultSaveError }}</p>
    </div>

    <!-- 答题区域 -->
    <div v-else-if="questions.length > 0" class="quiz-grid">
      <!-- 答题区 -->
      <div class="card">
        <div style="display: flex; align-items: center; justify-content: space-between">
          <span style="font-family: var(--mono); font-size: 12px; color: var(--text-3)">第 {{ currentIndex + 1 }} / {{ questions.length }} 题</span>
          <span class="badge" :class="levelBadgeClass">
            {{ testLabel }}
          </span>
          <span class="badge badge--mute">{{ currentQuestion.question_type === 'multiple_choice' ? '选择题' : currentQuestion.question_type === 'true_false' ? '判断题' : '简答题' }}</span>
        </div>

        <div style="font-size: 18px; font-weight: 600; line-height: 1.5; margin: 18px 0 24px; letter-spacing: -.01em">
          {{ currentQuestion.question }}
        </div>

        <!-- 选择题/判断题选项 -->
        <template v-if="currentQuestion.question_type !== 'practical'">
          <div v-for="(opt, idx) in currentQuestion.options" :key="idx" class="opt-big" :class="optionClass(idx)" @click="selectOption(idx)">
            <div class="opt-big__key" :class="optionClass(idx)">{{ String.fromCharCode(65 + idx) }}</div>
            <div style="font-size: 14px">{{ stripOptionPrefix(opt) }}</div>
          </div>
        </template>

        <!-- 简答题 -->
        <template v-else>
          <div class="practical-input-box">
            <p class="practical-hint">请在下方输入你的答案：</p>
            <textarea v-model="practicalAnswer" class="practical-textarea" :disabled="practicalGraded" placeholder="在此输入你的答案..." rows="8" />
            <div style="display: flex; justify-content: flex-end; margin-top: 12px">
              <button class="btn btn--primary" :disabled="!practicalAnswer.trim() || practicalGrading || practicalGraded" @click="submitPractical">
                {{ practicalGrading ? '批改中...' : '提交批改' }}
              </button>
            </div>
          </div>
        </template>

        <!-- 反馈区 -->
        <div v-if="showFeedback && currentQuestion.question_type !== 'practical'" class="feedback-box" :class="isCorrect ? 'ok' : 'err'">
          <div style="font-weight: 600; margin-bottom: 6px">{{ isCorrect ? '回答正确！' : '回答错误' }}</div>
          <div v-if="answered">{{ currentQuestion.explanation }}</div>
          <div v-if="!isCorrect && !answered" class="socratic-box">
            <div v-for="(h, idx) in socraticHistory" :key="idx" style="padding: 10px 0" :style="{ borderBottom: idx < socraticHistory.length - 1 ? '1px solid var(--line)' : 'none' }">
              <div style="font-size: 12px; font-weight: 600; color: var(--accent); margin-bottom: 4px"> 提示（第 {{ h.round }} 轮）：</div>
              <div>{{ h.hint }}</div>
            </div>
            <div v-if="socraticLoading" class="flex items-center gap-2 text-sm text-text-3 mt-2"><div class="spinner-inline"></div>正在生成提示...</div>
            <p class="text-sm text-accent font-medium mt-2"> 请阅读提示后，重新选择一个答案</p>
          </div>
          <div v-if="revealAnswer" style="margin-top: 12px; padding: 12px; background: var(--warn-soft); border-radius: var(--radius-sm); border: 1px solid #FDE68A;">
            <p class="text-sm font-medium" style="color: var(--warn)"> 正确答案：{{ currentQuestion.correctAnswer }}</p>
            <p class="text-sm mt-1 text-text-2">{{ currentQuestion.explanation }}</p>
          </div>
        </div>

        <!-- 简答题批改结果 -->
        <div v-if="practicalGraded" class="feedback-box" :class="practicalResult?.is_correct ? 'ok' : 'err'">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px">
            <div style="font-weight: 600">{{ practicalResult?.is_correct ? ' 通过' : ' 未通过' }}</div>
            <div class="practical-score" :class="practicalResult?.is_correct ? 'pass' : 'fail'">{{ practicalResult?.score }}<span style="font-size: 14px; opacity: .6">/100</span></div>
          </div>
          <div class="bar" style="margin-bottom: 16px"><div class="bar__fill" :class="practicalResult?.is_correct ? 'ok' : 'err'" :style="{ width: (practicalResult?.score || 0) + '%' }" /></div>
          <div style="font-size: 13.5px; line-height: 1.7; margin-bottom: 14px">{{ practicalResult?.feedback }}</div>
          <div v-if="practicalResult?.key_points?.length" class="socratic-box" style="margin-bottom: 14px">
            <div style="font-size: 12px; font-weight: 600; color: var(--accent); margin-bottom: 8px"> 关键要点</div>
            <ul style="margin: 0; padding-left: 18px; font-size: 13px; line-height: 1.8"><li v-for="(kp, idx) in practicalResult?.key_points" :key="idx">{{ kp }}</li></ul>
          </div>
          <details style="margin-top: 8px"><summary style="font-size: 13px; font-weight: 600; color: var(--text-2); cursor: pointer; padding: 8px 0"> 查看参考答案</summary><pre class="reference-answer-block"><code>{{ practicalResult?.reference_answer }}</code></pre></details>
        </div>

        <div style="display: flex; justify-content: space-between; margin-top: 28px; padding-top: 20px; border-top: 1px solid var(--line)">
          <button class="btn btn--ghost" :disabled="currentIndex === 0" @click="prevQuestion">← 上一题</button>
          <button class="btn btn--primary" :disabled="!answered" @click="nextQuestion">
            {{ currentIndex === questions.length - 1 ? '完成练习' : '下一题 →' }}
          </button>
        </div>
      </div>

      <!-- 统计区 -->
      <div>
        <div class="card" style="margin-bottom: 24px">
          <div class="card__head"><div class="card__title">答题统计</div></div>
          <div style="text-align: center; padding: 8px 0">
            <div style="font-size: 36px; font-weight: 600; letter-spacing: -.03em; color: var(--accent)">{{ correctCount }}<span style="font-size: 18px; color: var(--text-3)">/{{ questions.length }}</span></div>
            <div style="font-size: 12px; color: var(--text-3); margin-top: 4px">正确率 {{ accuracy }}%</div>
          </div>
          <div class="bar" style="margin-top: 16px"><div class="bar__fill ok" :style="{ width: accuracy + '%' }"></div></div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 16px">
            <div class="mini-stat ok"><span style="font-size: 13px; color: var(--ok)">正确</span><span style="font-size: 20px; font-weight: 600; font-family: var(--mono); color: var(--ok)">{{ correctCount }}</span></div>
            <div class="mini-stat err"><span style="font-size: 13px; color: var(--err)">错误</span><span style="font-size: 20px; font-weight: 600; font-family: var(--mono); color: var(--err)">{{ wrongCount }}</span></div>
          </div>
          <div style="font-size: 12px; color: var(--text-3); margin-top: 12px; text-align: center">达标参考线：{{ PASS_THRESHOLD }}%</div>
        </div>
      </div>
    </div>

    <div v-else class="flex flex-col items-center justify-center py-20">
      <p class="text-text-3 mb-4">暂无可用试题，请先完成 Agent 协同生成学习资源。</p>
      <div class="result-actions">
        <NuxtLink to="/workflow" class="btn btn--primary">前往 Agent 协同</NuxtLink>
        <NuxtLink to="/report" class="btn btn--ghost">查看分析报告</NuxtLink>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const router = useRouter()
const route = useRoute()
const api = useApi()
const { sessionId } = useSession()
const { nodes, fetchLearningPath } = useLearningPath()
const { isLoggedIn, isLoading: authLoading } = useAuth()

const PASS_THRESHOLD = 70
type TestLevel = 'node' | 'comprehensive'

const normalizeTestLevel = (value: unknown): TestLevel | '' => {
  const raw = Array.isArray(value) ? value[0] : value
  if (raw === 'basic' || raw === 'advanced') return 'node'
  return raw === 'node' || raw === 'comprehensive' ? raw : ''
}

// === 练习等级 ===
const testLevel = ref<TestLevel | ''>(normalizeTestLevel(route.query.level))
const levelLabels: Record<TestLevel, string> = {
  node: '节点练习',
  comprehensive: '综合练习',
}
const testLabel = computed(() => testLevel.value ? levelLabels[testLevel.value] : '答题练习')
const testDescription = computed(() =>
  testLevel.value === 'comprehensive'
    ? '一个完整生产场景下设置 2 道选择题和 3 道简答题，覆盖 5 个学习节点的关键能力。'
    : '可在 5 个学习节点间自由切换节点练习。每个节点包含 4 道选择题、3 道判断题、2 道简答题，结果用于报告分析和知识图谱掌握度。'
)
const levelBadgeClass = computed(() =>
  testLevel.value === 'comprehensive' ? 'badge--err' : 'badge--accent'
)

// === 状态 ===
const loading = ref(true)
const loadError = ref('')
const questions = ref<any[]>([])
const comprehensiveScenario = ref<any>(null)
const selectedStage = ref(Number(route.query.stage) || 1)
const currentIndex = ref(0)
const answered = ref(false)
const showFeedback = ref(false)
const isCorrect = ref(false)
const testCompleted = ref(false)

// 多轮追问
const socraticRound = ref(0)
const socraticHistory = ref<{ round: number; hint: string }[]>([])
const revealAnswer = ref(false)
const socraticLoading = ref(false)

// 简答题
const practicalAnswer = ref('')
const practicalGrading = ref(false)
const practicalGraded = ref(false)
const practicalResult = ref<any>(null)

const resultSaving = ref(false)
const resultSaved = ref(false)
const resultSaveError = ref('')

// 计算
const currentQuestion = computed(() => questions.value[currentIndex.value] || {})
const markdownCell = (value: unknown) => String(value ?? '').replace(/\|/g, '\\|').replace(/\r?\n/g, '<br>')
const markdownList = (items: unknown) => Array.isArray(items) && items.length
  ? items.map(item => `- ${markdownCell(item)}`).join('\n')
  : '- 暂无'
const markdownTable = (headers: string[], rows: string[][]) => {
  if (!rows.length) return '暂无'
  return [
    `| ${headers.join(' | ')} |`,
    `| ${headers.map(() => '---').join(' | ')} |`,
    ...rows.map(row => `| ${row.map(markdownCell).join(' | ')} |`),
  ].join('\n')
}
const scenarioMarkdown = computed(() => {
  const s = comprehensiveScenario.value
  if (!s) return ''
  const facts = [
    ['岗位身份', s.role],
    ['生产任务', s.production_task],
    ['机床/系统', [s.machine, s.controller].filter(Boolean).join(' / ')],
    ['材料/毛坯', [s.material, s.blank_size].filter(Boolean).join(' / ')],
    ['批量', s.batch_size],
    ['装夹/坐标系', [s.clamping, s.work_coordinate].filter(Boolean).join(' / ')],
  ].filter(row => row[1]) as string[][]
  const requirements = Array.isArray(s.drawing_requirements)
    ? s.drawing_requirements.map((item: any) => [item.item, item.requirement])
    : []
  const results = Array.isArray(s.first_article_results)
    ? s.first_article_results.map((item: any) => [item.item, item.requirement, item.measured])
    : []
  return [
    '## 生产任务资料',
    markdownTable(['项目', '内容'], facts),
    '## 图纸与质量要求',
    markdownTable(['检测项目', '要求'], requirements),
    '## 刀具信息',
    markdownList(s.tools),
    '## 关键程序片段',
    `\`\`\`nc\n${String(s.program_excerpt || '暂无').trim()}\n\`\`\``,
    '## 开工前现场状态',
    markdownList(s.site_conditions),
    '## 首件检测数据',
    markdownTable(['检测项目', '要求', '实测值'], results),
    '## 加工中异常现象',
    markdownList(s.runtime_symptoms),
  ].join('\n\n')
})
const questionWithScenario = computed(() => {
  if (testLevel.value !== 'comprehensive' || !scenarioMarkdown.value) return currentQuestion.value.question
  return `${scenarioMarkdown.value}\n\n## 当前问题\n${currentQuestion.value.question}`
})
const correctCount = computed(() => questions.value.filter(q => q.finalCorrect === true).length)
const wrongCount = computed(() => questions.value.filter(q => q.answered && q.finalCorrect === false).length)
const accuracy = computed(() => questions.value.length ? Math.round(correctCount.value / questions.value.length * 100) : 0)
const passed = computed(() => accuracy.value >= PASS_THRESHOLD)
const resultEmoji = computed(() => passed.value ? '' : '')
const resultTitle = computed(() => {
  if (testLevel.value === 'comprehensive') return passed.value ? '综合练习已达标' : '综合练习已完成'
  if (passed.value) return `${testLabel.value}已达标`
  return `${testLabel.value}已完成`
})
const resultMessage = computed(() => {
  if (testLevel.value === 'comprehensive') return passed.value ? '你已经能综合处理完整业务场景。' : '建议根据错题复盘装夹、检测、程序识读和异常处理环节。'
  if (passed.value) return '本轮练习表现达标，可继续学习资源或进入综合练习。'
  return '建议回到学习资源复习薄弱内容后再练一次。'
})

// === 辅助 ===
const stripOptionPrefix = (o: string) => o.replace(/^[A-Da-d][.\s、]+/, '')
const resolveCorrectIndex = (q: any): number => {
  const answer = q.correct_answer || ''
  if (/^[A-D]$/.test(answer)) return answer.charCodeAt(0) - 65
  const stripped = answer.replace(/^[A-Da-d][.\s、]+/, '')
  return q.options?.findIndex((opt: string) => stripOptionPrefix(opt) === stripped || opt === answer) ?? 0
}

const resolveSelectedStage = () => {
  let stage = Number(route.query.stage) || selectedStage.value || 1
  if (nodes.value.length > 0 && !nodes.value.some((n: any) => Number(n.stage) === stage)) {
    stage = Number(nodes.value[0].stage) || 1
  }
  selectedStage.value = stage
  return stage
}

// === 初始化 ===
const initQuestions = async () => {
  if (!sessionId.value) {
    loading.value = false; loadError.value = '缺少会话信息，请先完成学习者画像和 Agent 协同生成'; return
  }
  loading.value = true; loadError.value = ''
  questions.value = []
  resultSaved.value = false
  resultSaveError.value = ''

  try {
    await fetchLearningPath()

    let resolvedLevel = normalizeTestLevel(route.query.level) || 'node'
    if (resolvedLevel === 'comprehensive') {
      testLevel.value = resolvedLevel
      const result = await api.getTieredQuestions(sessionId.value, resolvedLevel)
      if (!result?.questions?.length) {
        loadError.value = (result as any)?.error || '综合练习暂不可用'
        loading.value = false
        return
      }
      applyQuestions(result)
      return
    }

    comprehensiveScenario.value = null
    const stage = resolveSelectedStage()
    const node = nodes.value.find((n: any) => Number(n.stage) === stage)
    if (!node) {
      loadError.value = '暂未找到学习节点，请先完成 Agent 协同生成'
      loading.value = false
      return
    }

    testLevel.value = resolvedLevel

    const result = await api.getTieredQuestions(sessionId.value, resolvedLevel, stage)
    if (!result?.questions?.length) {
      loadError.value = '试题尚未生成，请先完成 Agent 协同生成'
      loading.value = false
      return
    }
    applyQuestions(result)
  } catch (err: any) {
    loadError.value = '试题加载失败，请稍后重试'
    console.error('获取试题失败:', err)
  } finally { loading.value = false }
}

const applyQuestions = (result: any) => {
  comprehensiveScenario.value = testLevel.value === 'comprehensive' ? (result.scenario || null) : null
  questions.value = (result.questions || []).map((q: any) => ({
    ...q,
    correctIndex: resolveCorrectIndex(q),
    selectedIndex: -1, answered: false, finalCorrect: null,
    correctAnswer: q.correct_answer || '',
    practicalAnswer: '', practicalGraded: false, practicalResult: null,
  }))
  currentIndex.value = 0; testCompleted.value = false
  resetState()
  // 尝试恢复进度
  if (sessionId.value) {
    api.getPracticeState(
      sessionId.value,
      testLevel.value || undefined,
      testLevel.value === 'comprehensive' ? null : selectedStage.value,
    ).then(saved => {
      if (saved?.questions?.length) {
        let matched = 0
        questions.value = questions.value.map((q: any) => {
          const match = saved.questions.find((s: any) => s.question === q.question)
          if (match) matched += 1
          return match ? { ...q, selectedIndex: match.selectedIndex ?? -1, answered: match.answered ?? false, finalCorrect: match.finalCorrect ?? null, practicalAnswer: match.practicalAnswer || '', practicalGraded: match.practicalGraded ?? false, practicalResult: match.practicalResult || null } : q
        })
        if (matched > 0 && typeof saved.current_index === 'number') currentIndex.value = saved.current_index
        resetState()
      }
    }).catch(() => {})
  }
}

// === 苏格拉底追问 ===
const fetchHeuristic = async (round: number, optionIndex: number) => {
  socraticLoading.value = true
  try {
    const result = await api.submitFeedback({
      session_id: sessionId.value || 'demo',
      topic: currentQuestion.value.topic || '专业知识',
      question: questionWithScenario.value,
      user_answer: String.fromCharCode(65 + optionIndex),
      correct_answer: currentQuestion.value.correctAnswer,
      round,
      heuristic_context: socraticHistory.value.map(h => h.hint).join('\n'),
    })
    socraticRound.value = round; revealAnswer.value = result.reveal_answer || false
    if (result.heuristic_question) socraticHistory.value.push({ round, hint: result.heuristic_question })
    if (result.reveal_answer) lockQuestion(false)
  } catch {
    socraticHistory.value.push({ round, hint: `提示：正确答案是 ${currentQuestion.value.correctAnswer}，看看解析吧。` })
    socraticRound.value = round; revealAnswer.value = true; lockQuestion(false)
  } finally { socraticLoading.value = false }
}

const lockQuestion = (correct: boolean) => {
  answered.value = true; currentQuestion.value.answered = true; currentQuestion.value.finalCorrect = correct
  isCorrect.value = correct; showFeedback.value = true; saveProgress()
}

const submitPractical = async () => {
  if (!practicalAnswer.value.trim()) return; practicalGrading.value = true
  try {
    const result = await api.submitPracticalFeedback({
      session_id: sessionId.value || 'demo', topic: currentQuestion.value.topic || '专业知识',
      question: questionWithScenario.value, user_answer: practicalAnswer.value,
      correct_answer: currentQuestion.value.correctAnswer, explanation: currentQuestion.value.explanation || '',
    })
    practicalResult.value = result; practicalGraded.value = true
    currentQuestion.value.practicalAnswer = practicalAnswer.value; currentQuestion.value.practicalGraded = true; currentQuestion.value.practicalResult = result
    lockQuestion(result.is_correct)
  } catch {
    practicalResult.value = { score: 0, is_correct: false, feedback: '批改服务暂不可用', key_points: [], reference_answer: currentQuestion.value.correctAnswer || '' }
    practicalGraded.value = true; currentQuestion.value.practicalGraded = true; currentQuestion.value.practicalResult = practicalResult.value
    lockQuestion(false)
  } finally { practicalGrading.value = false }
}

const selectOption = async (index: number) => {
  if (answered.value || socraticLoading.value) return
  const correct = index === currentQuestion.value.correctIndex
  currentQuestion.value.selectedIndex = index; showFeedback.value = true; isCorrect.value = correct
  if (correct) lockQuestion(true)
  else { const nr = socraticRound.value + 1; await fetchHeuristic(nr, index) }
}

const optionClass = (index: number) => {
  if (answered.value) {
    if (index === currentQuestion.value.correctIndex) return 'correct'
    if (index === currentQuestion.value.selectedIndex && !isCorrect.value) return 'wrong'
    return ''
  }
  if (showFeedback.value && !isCorrect.value && !revealAnswer.value && index === currentQuestion.value.selectedIndex) return 'wrong'
  if (currentQuestion.value.selectedIndex === index) return 'selected'
  return ''
}

// === 翻页 ===
const prevQuestion = () => { if (currentIndex.value > 0) { currentIndex.value--; resetState(); saveProgress() } }
const nextQuestion = async () => {
  if (currentIndex.value < questions.value.length - 1) { currentIndex.value++; resetState(); saveProgress() }
  else {
    saveProgress()
    await submitPracticeResult()
    testCompleted.value = true
  }
}

const resetState = () => {
  const q = currentQuestion.value
  answered.value = q?.answered ?? false; showFeedback.value = q?.answered ?? false; isCorrect.value = q?.finalCorrect ?? false
  socraticRound.value = 0; socraticHistory.value = []; revealAnswer.value = false; socraticLoading.value = false
  practicalAnswer.value = q?.practicalAnswer || ''; practicalGrading.value = false; practicalGraded.value = q?.practicalGraded ?? false; practicalResult.value = q?.practicalResult || null
}

const saveProgress = () => {
  if (!sessionId.value) return
  api.savePracticeState(sessionId.value, {
    current_index: currentIndex.value,
    level: testLevel.value || null,
    stage: testLevel.value === 'comprehensive' ? null : selectedStage.value,
    questions: questions.value.map((q: any) => ({ question: q.question, selectedIndex: q.selectedIndex, answered: q.answered, finalCorrect: q.finalCorrect, practicalAnswer: q.practicalAnswer, practicalGraded: q.practicalGraded, practicalResult: q.practicalResult })),
  }).catch(() => {})
}

const submitPracticeResult = async () => {
  if (!sessionId.value || !testLevel.value || resultSaved.value || resultSaving.value) return
  resultSaving.value = true
  resultSaveError.value = ''
  try {
    await api.savePracticeResult(sessionId.value, {
      level: testLevel.value,
      stage: testLevel.value === 'comprehensive' ? null : selectedStage.value,
      score: accuracy.value,
      correct_count: correctCount.value,
      wrong_count: wrongCount.value,
      question_count: questions.value.length,
      questions: questions.value.map((q: any) => ({
        topic: q.topic || '',
        question: q.question,
        question_type: q.question_type,
        is_correct: q.finalCorrect === true,
        user_answer: q.question_type === 'practical'
          ? q.practicalAnswer
          : q.selectedIndex >= 0 ? String.fromCharCode(65 + q.selectedIndex) : '',
        correct_answer: q.correctAnswer,
      })),
    })
    resultSaved.value = true
  } catch (err) {
    console.warn('保存练习结果失败:', err)
    resultSaveError.value = '练习结果保存失败，报告可能暂时无法显示本次成绩'
  } finally {
    resultSaving.value = false
  }
}

// === 结果页操作 ===
const goResources = () => router.push({ path: '/resources', query: { stage: String(selectedStage.value || 1) } })
const goReport = () => router.push('/report')

const switchLevel = (level: TestLevel) => {
  if (level === testLevel.value) return
  const query = level === 'comprehensive'
    ? { level }
    : { stage: String(selectedStage.value || 1), level }
  router.push({ path: '/practice', query })
}

const switchStage = (stage: number) => {
  if (!stage || (stage === selectedStage.value && testLevel.value !== 'comprehensive')) return
  router.push({
    path: '/practice',
    query: { stage: String(stage), level: testLevel.value && testLevel.value !== 'comprehensive' ? testLevel.value : 'node' },
  })
}

const retryTest = () => {
  questions.value.forEach(q => { q.selectedIndex = -1; q.answered = false; q.finalCorrect = null; q.practicalAnswer = ''; q.practicalGraded = false; q.practicalResult = null })
  currentIndex.value = 0; testCompleted.value = false; resultSaved.value = false; resetState(); saveProgress()
}

// === 初始化 ===
onMounted(() => {
  if (isLoggedIn.value && sessionId.value) initQuestions()
  else if (!isLoggedIn.value) { loading.value = false; loadError.value = '请先登录' }
  else { loading.value = false; loadError.value = '请先完成学情诊断' }
})

// F5 刷新时布局会异步恢复登录态和学习会话；恢复完成后自动加载，无需再点“重新加载”。
watch([authLoading, isLoggedIn, sessionId], ([isAuthLoading, loggedIn, sid]) => {
  if (!isAuthLoading && loggedIn && sid && !loading.value && questions.value.length === 0) {
    initQuestions()
  }
})

watch(() => [route.query.level, route.query.stage], ([newLevel, newStage], [oldLevel, oldStage]) => {
  if (newLevel !== oldLevel || newStage !== oldStage) {
    testCompleted.value = false
    loading.value = true
    loadError.value = ''
    questions.value = []
    currentIndex.value = 0
    initQuestions()
  }
})
</script>

<style scoped>
.node-selector {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}
.node-selector__card {
  text-align: left;
  border: 1px solid var(--line);
  background: var(--bg);
  border-radius: var(--radius-sm);
  padding: 14px 16px;
  min-height: 112px;
  cursor: pointer;
  transition: all .15s;
}
.node-selector__card:hover {
  border-color: var(--accent);
  transform: translateY(-1px);
}
.node-selector__card.active {
  border-color: var(--accent);
  background: var(--accent-soft);
  box-shadow: 0 0 0 1px rgba(99, 102, 241, .12);
}
.node-selector__stage {
  display: inline-flex;
  margin-bottom: 8px;
  padding: 3px 8px;
  border-radius: 99px;
  background: rgba(99, 102, 241, .1);
  color: var(--accent);
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 600;
}
.node-selector__card strong {
  display: block;
  font-size: 14px;
  line-height: 1.45;
  color: var(--text);
}
.node-selector__meta {
  display: block;
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-3);
}
.practice-path { margin-bottom: 24px; }
.comprehensive-node {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 16px;
  text-align: left;
  border: 1px solid var(--line);
  background: linear-gradient(135deg, var(--bg) 0%, var(--bg-muted) 100%);
  border-radius: var(--radius-sm);
  padding: 18px 20px;
  cursor: pointer;
  transition: all .15s;
}
.comprehensive-node:hover {
  border-color: var(--accent);
  transform: translateY(-1px);
}
.comprehensive-node.active {
  border-color: var(--accent);
  background: var(--accent-soft);
  box-shadow: 0 0 0 1px rgba(99, 102, 241, .12);
}
.comprehensive-node__index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  flex-shrink: 0;
  border-radius: 14px;
  background: var(--accent);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
}
.comprehensive-node__body { min-width: 0; flex: 1; }
.comprehensive-node__body strong {
  display: block;
  margin-bottom: 5px;
  color: var(--text);
  font-size: 16px;
}
.comprehensive-node__body span {
  display: block;
  color: var(--text-2);
  font-size: 12px;
  line-height: 1.6;
}
.comprehensive-node__action {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  color: var(--accent);
  font-size: 13px;
  font-weight: 600;
}
.scenario-card {
  margin-bottom: 24px;
  padding: 24px 28px;
  border-color: rgba(99, 102, 241, .22);
  background: linear-gradient(180deg, rgba(99, 102, 241, .035), var(--bg) 180px);
}
.scenario-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 18px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--line);
}
.scenario-card__head h2 {
  margin-top: 4px;
  color: var(--text);
  font-size: 20px;
  font-weight: 650;
}
.scenario-card__eyebrow {
  color: var(--accent);
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .08em;
  text-transform: uppercase;
}
.quiz-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 24px; }
.opt-big { display: flex; align-items: center; gap: 14px; padding: 16px 18px; border: 1px solid var(--line-2); border-radius: var(--radius-sm); margin-bottom: 10px; cursor: pointer; transition: all .15s; }
.opt-big:hover { border-color: var(--text-3); }
.opt-big.correct { border-color: var(--ok); background: var(--ok-soft); }
.opt-big.wrong { border-color: var(--err); background: var(--err-soft); }
.opt-big.selected { border-color: var(--accent); background: var(--accent-soft); }
.opt-big__key { width: 32px; height: 32px; border-radius: 50%; border: 1px solid var(--line-2); display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 600; flex-shrink: 0; transition: all .15s; }
.opt-big.correct .opt-big__key { background: var(--ok); color: #fff; border-color: var(--ok); }
.opt-big.wrong .opt-big__key { background: var(--err); color: #fff; border-color: var(--err); }
.opt-big.selected .opt-big__key { background: var(--accent); color: #fff; border-color: var(--accent); }
.feedback-box { margin-top: 20px; padding: 18px 20px; border-radius: var(--radius-sm); font-size: 13.5px; line-height: 1.7; }
.feedback-box.ok { background: var(--ok-soft); border: 1px solid #A7F3D0; }
.feedback-box.err { background: var(--err-soft); border: 1px solid #FECACA; }
.socratic-box { margin-top: 12px; padding: 14px 16px; background: #fff; border: 1px solid var(--line); border-radius: var(--radius-sm); }
.mini-stat { display: flex; align-items: center; justify-content: space-between; padding: 12px 14px; border-radius: var(--radius-sm); }
.mini-stat.ok { background: var(--ok-soft); }
.mini-stat.err { background: var(--err-soft); }
.result-score { padding: 24px; background: var(--bg-muted); border-radius: var(--radius-sm); }
.result-score__num { font-size: 48px; font-weight: 700; font-family: var(--mono); letter-spacing: -.03em; color: var(--accent); }
.result-score__label { display: block; font-size: 13px; color: var(--text-2); margin-top: 4px; }
.result-actions { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; }
.practical-input-box { background: var(--bg-muted); border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 18px 20px; }
.practical-hint { font-size: 13px; color: var(--text-2); margin-bottom: 12px; }
.practical-textarea { width: 100%; min-height: 160px; padding: 14px 16px; border: 1px solid var(--line-2); border-radius: var(--radius-sm); font-family: var(--mono); font-size: 13px; line-height: 1.6; resize: vertical; background: var(--bg); color: var(--text); }
.practical-textarea:focus { outline: none; border-color: var(--accent); }
.practical-textarea:disabled { opacity: .7; cursor: not-allowed; }
.practical-score { font-size: 28px; font-weight: 700; font-family: var(--mono); }
.practical-score.pass { color: var(--ok); }
.practical-score.fail { color: var(--err); }
.reference-answer-block { background: var(--bg); padding: 14px 16px; border-radius: var(--radius-sm); border: 1px solid var(--line); font-size: 13px; font-family: var(--mono); line-height: 1.6; overflow-x: auto; white-space: pre-wrap; margin-top: 8px; }
.spinner { width: 48px; height: 48px; border: 4px solid var(--line); border-top-color: var(--accent); border-radius: 50%; animation: spin 1s linear infinite; }
.spinner-inline { width: 16px; height: 16px; border: 2px solid var(--line); border-top-color: var(--accent); border-radius: 50%; animation: spin 1s linear infinite; flex-shrink: 0; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.bar { height: 6px; background: var(--line); border-radius: 3px; overflow: hidden; }
.bar__fill { height: 100%; border-radius: 3px; transition: width .4s ease; }
.bar__fill.ok { background: var(--ok); }
.bar__fill.err { background: var(--err); }
@media (max-width: 900px) {
  .node-selector { grid-template-columns: 1fr; }
  .comprehensive-node { align-items: flex-start; }
  .comprehensive-node__action { display: none; }
  .scenario-card { padding: 18px; }
  .scenario-card__head { flex-direction: column; gap: 10px; }
  .quiz-grid { grid-template-columns: 1fr; }
}
</style>
