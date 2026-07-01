<template>
  <div class="page page--wide">
    <div class="page-head">
      <p class="page-head__eyebrow">Step 5</p>
      <h1 class="page-head__title">{{ testLabel }}</h1>
      <p class="page-head__desc">{{ testDescription }}</p>
    </div>

    <!-- 未指定考核等级 -->
    <div v-if="!testLevel" class="text-center py-12">
      <p class="text-text-3 mb-4">请从学习路径报告中选择考核等级</p>
      <NuxtLink to="/report" class="btn btn--primary">前往学习报告</NuxtLink>
    </div>

    <!-- 加载中 -->
    <div v-else-if="loading" class="flex flex-col items-center justify-center py-20">
      <div class="spinner"></div>
      <p class="mt-4 text-text-2">正在生成试题，请稍候...</p>
    </div>

    <!-- 加载失败 -->
    <div v-else-if="loadError" class="flex flex-col items-center justify-center py-20">
      <p class="text-err mb-4">{{ loadError }}</p>
      <button class="btn btn--primary" @click="initQuestions">重新加载</button>
    </div>

    <!-- 考核完成结果页 -->
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
        <button v-if="testLevel === 'basic' && passed" class="btn btn--primary" @click="goAdvanced">
           进入提升考核
        </button>
        <button v-if="testLevel === 'basic' && !passed" class="btn btn--primary" @click="goResources">
           返回学习资源，重新学习
        </button>
        <button v-if="testLevel === 'advanced' && passed" class="btn btn--primary" @click="handleAdvance">
          {{ advanceResult?.all_completed ? ' 查看完整报告' : ' 推进到下一节点' }}
        </button>
        <button v-if="testLevel === 'advanced' && !passed" class="btn btn--ghost" @click="goReport">
          返回学习路径
        </button>
        <button class="btn btn--ghost" @click="retryTest">重新答题</button>
      </div>
      <p v-if="advancing" class="text-sm text-text-3 mt-4">正在更新学习进度...</p>
      <p v-if="advanceError" class="text-sm text-err mt-2">{{ advanceError }}</p>
    </div>

    <!-- 答题区域 -->
    <div v-else-if="questions.length > 0" class="quiz-grid">
      <!-- 答题区 -->
      <div class="card">
        <div style="display: flex; align-items: center; justify-content: space-between">
          <span style="font-family: var(--mono); font-size: 12px; color: var(--text-3)">第 {{ currentIndex + 1 }} / {{ questions.length }} 题</span>
          <span class="badge" :class="testLevel === 'basic' ? 'badge--accent' : 'badge--warn'">
            {{ testLevel === 'basic' ? '基础考核' : '提升考核' }}
          </span>
          <span class="badge badge--mute">{{ currentQuestion.question_type === 'multiple_choice' ? '选择题' : currentQuestion.question_type === 'true_false' ? '判断题' : '实操题' }}</span>
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

        <!-- 实操题 -->
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

        <!-- 实操题批改结果 -->
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
            {{ currentIndex === questions.length - 1 ? '完成考核' : '下一题 →' }}
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
          <div style="font-size: 12px; color: var(--text-3); margin-top: 12px; text-align: center">通过线：{{ PASS_THRESHOLD }}%</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const router = useRouter()
const route = useRoute()
const api = useApi()
const { sessionId } = useSession()
const { currentStage } = useLearningPath()
const { isLoggedIn } = useAuth()

const PASS_THRESHOLD = 70

// === 考核等级 ===
const testLevel = computed(() => (route.query.level as string) || '')
const testLabel = computed(() => testLevel.value === 'advanced' ? '提升考核' : '基础考核')
const testDescription = computed(() =>
  testLevel.value === 'advanced'
    ? '基础考核已通过，现在进行更高难度的提升考核。'
    : '请完成基础考核，答对率达 70% 即可解锁提升考核。'
)

// === 状态 ===
const loading = ref(true)
const loadError = ref('')
const questions = ref<any[]>([])
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

// 实操题
const practicalAnswer = ref('')
const practicalGrading = ref(false)
const practicalGraded = ref(false)
const practicalResult = ref<any>(null)

// 节点推进
const advancing = ref(false)
const advanceError = ref('')
const advanceResult = ref<any>(null)

// 计算
const currentQuestion = computed(() => questions.value[currentIndex.value] || {})
const correctCount = computed(() => questions.value.filter(q => q.finalCorrect === true).length)
const wrongCount = computed(() => questions.value.filter(q => q.answered && q.finalCorrect === false).length)
const accuracy = computed(() => questions.value.length ? Math.round(correctCount.value / questions.value.length * 100) : 0)
const passed = computed(() => accuracy.value >= PASS_THRESHOLD)
const resultEmoji = computed(() => passed.value ? '' : '')
const resultTitle = computed(() => {
  if (passed.value && testLevel.value === 'advanced') return '恭喜！提升考核通过！'
  if (passed.value) return '基础考核通过！'
  return '考核未通过'
})
const resultMessage = computed(() => {
  if (passed.value && testLevel.value === 'advanced') return '你已掌握本节点知识，可以进入下一阶段学习了。'
  if (passed.value) return '基础扎实，可以进行更高难度的挑战了。'
  if (testLevel.value === 'advanced') return '提升考核有难度，建议回顾学习内容后重试。'
  return '建议重新学习相关资源后再来挑战。'
})

// === 辅助 ===
const stripOptionPrefix = (o: string) => o.replace(/^[A-Da-d][.\s、]+/, '')
const resolveCorrectIndex = (q: any): number => {
  const answer = q.correct_answer || ''
  if (/^[A-D]$/.test(answer)) return answer.charCodeAt(0) - 65
  const stripped = answer.replace(/^[A-Da-d][.\s、]+/, '')
  return q.options?.findIndex((opt: string) => stripOptionPrefix(opt) === stripped || opt === answer) ?? 0
}

// === 初始化 ===
const initQuestions = async () => {
  if (!sessionId.value || !testLevel.value) {
    loading.value = false; loadError.value = '缺少必要参数'; return
  }
  loading.value = true; loadError.value = ''

  try {
    const result = await api.getTieredQuestions(sessionId.value, testLevel.value as 'basic' | 'advanced', currentStage.value)
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
    api.getPracticeState(sessionId.value).then(saved => {
      if (saved?.questions?.length) {
        questions.value = questions.value.map((q: any) => {
          const match = saved.questions.find((s: any) => s.question === q.question)
          return match ? { ...q, selectedIndex: match.selectedIndex ?? -1, answered: match.answered ?? false, finalCorrect: match.finalCorrect ?? null, practicalAnswer: match.practicalAnswer || '', practicalGraded: match.practicalGraded ?? false, practicalResult: match.practicalResult || null } : q
        })
        if (typeof saved.current_index === 'number') currentIndex.value = saved.current_index
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
      question: currentQuestion.value.question,
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
      question: currentQuestion.value.question, user_answer: practicalAnswer.value,
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
const nextQuestion = () => {
  if (currentIndex.value < questions.value.length - 1) { currentIndex.value++; resetState(); saveProgress() }
  else { saveProgress(); testCompleted.value = true }
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
    questions: questions.value.map((q: any) => ({ question: q.question, selectedIndex: q.selectedIndex, answered: q.answered, finalCorrect: q.finalCorrect, practicalAnswer: q.practicalAnswer, practicalGraded: q.practicalGraded, practicalResult: q.practicalResult })),
  }).catch(() => {})
}

// === 结果页操作 ===
const goAdvanced = () => router.push({ path: '/practice', query: { level: 'advanced' } })
const goResources = () => router.push('/resources')
const goReport = () => router.push('/report')

const retryTest = () => {
  questions.value.forEach(q => { q.selectedIndex = -1; q.answered = false; q.finalCorrect = null; q.practicalAnswer = ''; q.practicalGraded = false; q.practicalResult = null })
  currentIndex.value = 0; testCompleted.value = false; resetState(); saveProgress()
}

const handleAdvance = async () => {
  advancing.value = true; advanceError.value = ''
  const feedback = questions.value.map(q => ({ topic: q.topic || '', question: q.question, is_correct: q.finalCorrect, finalCorrect: q.finalCorrect }))
  // 基础考核分数从当前 testLevel=advanced 时推断(基础已过)或用准确率
  const basicScore = testLevel.value === 'advanced' ? PASS_THRESHOLD : accuracy.value
  const result = await useLearningPath().advanceNode(basicScore, accuracy.value, feedback)
  advancing.value = false
  if (result) {
    advanceResult.value = result
    if (result.all_completed) setTimeout(() => router.push('/report'), 1500)
  } else {
    advanceError.value = '节点推进失败，请稍后重试'
  }
}

// === 初始化 ===
onMounted(() => {
  if (isLoggedIn.value && sessionId.value && testLevel.value) initQuestions()
  else if (!isLoggedIn.value) { loading.value = false; loadError.value = '请先登录' }
  else if (!testLevel.value) { loading.value = false }
  else { loading.value = false; loadError.value = '请先完成学情诊断' }
})

watch(testLevel, (newLevel, oldLevel) => {
  if (newLevel && newLevel !== oldLevel) {
    testCompleted.value = false
    loading.value = true
    loadError.value = ''
    initQuestions()
  }
})
</script>

<style scoped>
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
@media (max-width: 900px) { .quiz-grid { grid-template-columns: 1fr; } }
</style>
