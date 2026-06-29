<template>
  <div class="page page--wide">
    <div class="page-head">
      <p class="page-head__eyebrow">Step 5</p>
      <h1 class="page-head__title">分阶试题 · 答题反馈</h1>
      <p class="page-head__desc">答题正确直接进入下一题；答错时系统会通过苏格拉底式追问引导你思考，并将反馈用于动态调整学习路径。</p>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="flex flex-col items-center justify-center py-20">
      <div class="animate-spin" style="width: 48px; height: 48px; border: 4px solid var(--line); border-top-color: var(--accent); border-radius: 50%;"></div>
      <p class="mt-4 text-text-2">正在生成试题，请稍候...</p>
    </div>

    <!-- 加载失败 -->
    <div v-else-if="loadError" class="flex flex-col items-center justify-center py-20">
      <p class="text-err mb-4">{{ loadError }}</p>
      <button class="btn btn--primary" @click="fetchQuestions">重新加载</button>
    </div>

    <!-- 无试题 -->
    <div v-else-if="questions.length === 0" class="flex flex-col items-center justify-center py-20">
      <p class="text-text-3 mb-4">暂无试题</p>
      <button class="btn btn--primary" @click="fetchQuestions">生成试题</button>
    </div>

    <!-- 答题区域 -->
    <div v-else class="quiz-grid">
      <!-- 答题区 -->
      <div class="card">
        <div style="display: flex; align-items: center; justify-content: space-between">
          <span style="font-family: var(--mono); font-size: 12px; color: var(--text-3)">第 {{ currentIndex + 1 }} / {{ questions.length }} 题</span>
          <span class="badge badge--accent">{{ currentQuestion.question_type === 'multiple_choice' ? '选择题' : currentQuestion.question_type === 'true_false' ? '判断题' : '实操题' }}</span>
        </div>

        <div style="font-size: 18px; font-weight: 600; line-height: 1.5; margin: 18px 0 24px; letter-spacing: -.01em">
          {{ currentQuestion.question }}
        </div>

        <!-- 选择题/判断题选项 -->
        <template v-if="currentQuestion.question_type !== 'practical'">
          <div
            v-for="(opt, idx) in currentQuestion.options"
            :key="idx"
            class="opt-big"
            :class="optionClass(idx)"
            @click="selectOption(idx)"
          >
            <div class="opt-big__key" :class="optionClass(idx)">{{ String.fromCharCode(65 + idx) }}</div>
            <div style="font-size: 14px">{{ stripOptionPrefix(opt) }}</div>
          </div>
        </template>

        <!-- 实操题：文本输入 -->
        <template v-else>
          <div class="practical-input-box">
            <p class="practical-hint">请在下方输入你的答案（G 代码、操作步骤、工艺分析等）：</p>
            <textarea
              v-model="practicalAnswer"
              class="practical-textarea"
              :disabled="practicalGraded"
              placeholder="在此输入你的答案..."
              rows="8"
            />
            <div style="display: flex; justify-content: flex-end; margin-top: 12px">
              <button
                class="btn btn--primary"
                :disabled="!practicalAnswer.trim() || practicalGrading || practicalGraded"
                @click="submitPractical"
              >
                {{ practicalGrading ? '批改中...' : '提交批改' }}
              </button>
            </div>
          </div>
        </template>

        <!-- 反馈区（选择题/判断题） -->
        <div v-if="showFeedback && currentQuestion.question_type !== 'practical'" class="feedback-box" :class="isCorrect ? 'ok' : 'err'">
          <div style="font-weight: 600; margin-bottom: 6px">{{ isCorrect ? '回答正确！' : '回答错误' }}</div>

          <!-- 答对 或 追问耗尽时显示解析 -->
          <div v-if="answered">{{ currentQuestion.explanation }}</div>

          <!-- 苏格拉底式追问提示 -->
          <div v-if="!isCorrect && !answered" class="socratic-box">
            <div v-for="(h, idx) in socraticHistory" :key="idx" style="padding: 10px 0" :style="{ borderBottom: idx < socraticHistory.length - 1 ? '1px solid var(--line)' : 'none' }">
              <div style="font-size: 12px; font-weight: 600; color: var(--accent); margin-bottom: 4px">💡 提示（第 {{ h.round }} 轮）：</div>
              <div>{{ h.hint }}</div>
            </div>
            <div v-if="socraticLoading" class="flex items-center gap-2 text-sm text-text-3 mt-2">
              <div class="animate-spin" style="width: 16px; height: 16px; border: 2px solid var(--line); border-top-color: var(--accent); border-radius: 50%;"></div>
              正在生成提示...
            </div>
            <p class="text-sm text-accent font-medium mt-2">
              👆 请阅读提示后，重新选择一个答案
            </p>
          </div>

          <!-- 揭示答案（追问耗尽） -->
          <div v-if="revealAnswer" style="margin-top: 12px; padding: 12px; background: var(--warn-soft); border-radius: var(--radius-sm); border: 1px solid #FDE68A;">
            <p class="text-sm font-medium" style="color: var(--warn)">📌 正确答案：{{ currentQuestion.correctAnswer }}</p>
            <p class="text-sm mt-1 text-text-2">{{ currentQuestion.explanation }}</p>
          </div>
        </div>

        <!-- 实操题批改结果 -->
        <div v-if="practicalGraded" class="feedback-box" :class="practicalResult?.is_correct ? 'ok' : 'err'">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px">
            <div style="font-weight: 600">{{ practicalResult?.is_correct ? '✅ 通过' : '❌ 未通过' }}</div>
            <div class="practical-score" :class="practicalResult?.is_correct ? 'pass' : 'fail'">
              {{ practicalResult?.score }}<span style="font-size: 14px; opacity: .6">/100</span>
            </div>
          </div>

          <!-- 评分条 -->
          <div class="bar" style="margin-bottom: 16px">
            <div
              class="bar__fill"
              :class="practicalResult?.is_correct ? 'ok' : 'err'"
              :style="{ width: (practicalResult?.score || 0) + '%' }"
            />
          </div>

          <!-- 详细反馈 -->
          <div style="font-size: 13.5px; line-height: 1.7; margin-bottom: 14px">
            {{ practicalResult?.feedback }}
          </div>

          <!-- 关键要点 -->
          <div v-if="practicalResult?.key_points?.length" class="socratic-box" style="margin-bottom: 14px">
            <div style="font-size: 12px; font-weight: 600; color: var(--accent); margin-bottom: 8px">📋 关键要点</div>
            <ul style="margin: 0; padding-left: 18px; font-size: 13px; line-height: 1.8">
              <li v-for="(kp, idx) in practicalResult?.key_points" :key="idx">{{ kp }}</li>
            </ul>
          </div>

          <!-- 参考答案 -->
          <details style="margin-top: 8px">
            <summary style="font-size: 13px; font-weight: 600; color: var(--text-2); cursor: pointer; padding: 8px 0">📖 查看参考答案</summary>
            <pre class="reference-answer-block"><code>{{ practicalResult?.reference_answer }}</code></pre>
          </details>
        </div>

        <div style="display: flex; justify-content: space-between; margin-top: 28px; padding-top: 20px; border-top: 1px solid var(--line)">
          <button class="btn btn--ghost" :disabled="currentIndex === 0" @click="prevQuestion">← 上一题</button>
          <button class="btn btn--primary" :disabled="!answered" @click="nextQuestion">
            {{ currentIndex === questions.length - 1 ? '查看报告' : '下一题 →' }}
          </button>
        </div>
      </div>

      <!-- 统计区 -->
      <div>
        <div class="card" style="margin-bottom: 24px">
          <div class="card__head"><div class="card__title">答题统计</div></div>
          <div style="text-align: center; padding: 8px 0">
            <div style="font-size: 36px; font-weight: 600; letter-spacing: -.03em; color: var(--accent)">
              {{ correctCount }}<span style="font-size: 18px; color: var(--text-3)">/{{ questions.length }}</span>
            </div>
            <div style="font-size: 12px; color: var(--text-3); margin-top: 4px">
              正确率 {{ questions.length ? (correctCount / questions.length * 100).toFixed(0) : 0 }}%
            </div>
          </div>
          <div class="bar" style="margin-top: 16px">
            <div class="bar__fill ok" :style="{ width: questions.length ? (correctCount / questions.length * 100) + '%' : '0%' }"></div>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 16px">
            <div class="mini-stat ok">
              <span style="font-size: 13px; color: var(--ok)">正确</span>
              <span style="font-size: 20px; font-weight: 600; font-family: var(--mono); color: var(--ok)">{{ correctCount }}</span>
            </div>
            <div class="mini-stat err">
              <span style="font-size: 13px; color: var(--err)">错误</span>
              <span style="font-size: 20px; font-weight: 600; font-family: var(--mono); color: var(--err)">{{ wrongCount }}</span>
            </div>
          </div>
          <!-- 重新生成按钮 -->
          <button class="btn btn--ghost" style="width: 100%; margin-top: 16px;" @click="fetchQuestions">
            重新生成试题
          </button>
        </div>

        <div class="card">
          <div class="card__head"><div class="card__title">动态调整记录</div></div>
          <div style="font-size: 13px; color: var(--text-2); line-height: 1.8">
            <div v-for="(record, idx) in adjustRecords" :key="idx" style="padding: 10px 0" :style="{ borderBottom: idx < adjustRecords.length - 1 ? '1px solid var(--line)' : 'none' }">
              <span class="badge" :class="record.badgeClass">{{ record.label }}</span>
              {{ record.text }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const router = useRouter()
const api = useApi()
const { sessionId } = useSession()
const { isLoggedIn } = useAuth()

// === 状态 ===
const loading = ref(true)
const loadError = ref('')
const questions = ref<any[]>([])
const currentIndex = ref(0)
const answered = ref(false)
const showFeedback = ref(false)
const isCorrect = ref(false)

// === 多轮追问状态 ===
const socraticRound = ref(0)
const socraticHistory = ref<{round: number, hint: string}[]>([])
const revealAnswer = ref(false)
const socraticLoading = ref(false)

// === 实操题状态 ===
const practicalAnswer = ref('')
const practicalGrading = ref(false)
const practicalGraded = ref(false)
const practicalResult = ref<{score: number; is_correct: boolean; feedback: string; key_points: string[]; reference_answer: string} | null>(null)

// === 计算属性 ===
const currentQuestion = computed(() => questions.value[currentIndex.value])
const correctCount = computed(() => questions.value.filter(q => q.finalCorrect === true).length)
const wrongCount = computed(() => questions.value.filter(q => q.answered && q.finalCorrect === false).length)

// 动态调整记录
const adjustRecords = computed(() => {
  const records: {label: string, badgeClass: string, text: string}[] = []
  questions.value.forEach((q, idx) => {
    if (q.answered) {
      if (q.finalCorrect) {
        records.push({
          label: `第 ${idx + 1} 题`,
          badgeClass: 'badge--ok',
          text: '答对 → 维持当前难度',
        })
      } else {
        records.push({
          label: `第 ${idx + 1} 题`,
          badgeClass: 'badge--warn',
          text: '答错 → 触发苏格拉底追问，推荐复习',
        })
      }
    }
  })
  return records
})

// === 辅助函数 ===
const stripOptionPrefix = (option: string) => {
  return option.replace(/^[A-Da-d][.\s、]+/, '')
}

const resolveCorrectIndex = (q: any): number => {
  const answer = q.correct_answer || ''
  if (/^[A-D]$/.test(answer)) {
    return answer.charCodeAt(0) - 65
  }
  const stripped = answer.replace(/^[A-Da-d][.\s、]+/, '')
  const idx = q.options?.findIndex((opt: string) => {
    const optStripped = stripOptionPrefix(opt)
    return optStripped === stripped || opt === answer
  }) ?? -1
  return idx >= 0 ? idx : 0
}

// === 获取试题 ===
const fetchQuestions = async () => {
  if (!sessionId.value) {
    loadError.value = '请先完成学情诊断'
    loading.value = false
    return
  }
  loading.value = true
  loadError.value = ''
  try {
    const result = await api.getQuestions(sessionId.value)
    questions.value = (result.questions || []).map((q: any) => ({
      ...q,
      correctIndex: resolveCorrectIndex(q),
      selectedIndex: -1,
      answered: false,
      finalCorrect: null,
      correctAnswer: q.correct_answer || '',
      practicalAnswer: '',
      practicalGraded: false,
      practicalResult: null,
    }))
    currentIndex.value = 0
    resetState()

    // 尝试恢复之前的答题进度
    if (sessionId.value) {
      try {
        const saved = await api.getPracticeState(sessionId.value)
        if (saved?.questions?.length > 0) {
          questions.value = questions.value.map((q: any) => {
            const match = saved.questions.find((s: any) => s.question === q.question)
            if (match) {
              return { ...q,
                selectedIndex: match.selectedIndex ?? -1,
                answered: match.answered ?? false,
                finalCorrect: match.finalCorrect ?? null,
                practicalAnswer: match.practicalAnswer || '',
                practicalGraded: match.practicalGraded ?? false,
                practicalResult: match.practicalResult || null,
              }
            }
            return q
          })
          if (typeof saved.current_index === 'number') {
            currentIndex.value = saved.current_index
          }
          resetState()
        }
      } catch { /* 没有已保存的进度 */ }
    }
  } catch (err: any) {
    loadError.value = '试题加载失败，请稍后重试'
    console.error('获取试题失败:', err)
  } finally {
    loading.value = false
  }
}

// === 请求苏格拉底追问 ===
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

    socraticRound.value = round
    revealAnswer.value = result.reveal_answer || false

    if (result.heuristic_question) {
      socraticHistory.value.push({ round, hint: result.heuristic_question })
    }

    if (result.reveal_answer) {
      lockQuestion(false)
    }
  } catch (err) {
    console.error('追问 API 失败:', err)
    const fallbackHint = `提示：正确答案是 ${currentQuestion.value.correctAnswer}，看看解析吧。`
    socraticHistory.value.push({ round, hint: fallbackHint })
    socraticRound.value = round
    revealAnswer.value = true
    lockQuestion(false)
  } finally {
    socraticLoading.value = false
  }
}

// === 锁定本题 ===
const lockQuestion = (correct: boolean) => {
  answered.value = true
  currentQuestion.value.answered = true
  currentQuestion.value.finalCorrect = correct
  isCorrect.value = correct
  showFeedback.value = true
  saveProgress()
}

// === 提交实操题答案 ===
const submitPractical = async () => {
  if (!practicalAnswer.value.trim()) return
  practicalGrading.value = true
  try {
    const result = await api.submitPracticalFeedback({
      session_id: sessionId.value || 'demo',
      topic: currentQuestion.value.topic || '专业知识',
      question: currentQuestion.value.question,
      user_answer: practicalAnswer.value,
      correct_answer: currentQuestion.value.correctAnswer,
      explanation: currentQuestion.value.explanation || '',
    })
    practicalResult.value = result
    practicalGraded.value = true
    // 保存状态到 question 对象（翻页后恢复）
    currentQuestion.value.practicalAnswer = practicalAnswer.value
    currentQuestion.value.practicalGraded = true
    currentQuestion.value.practicalResult = result
    // 锁定本题
    lockQuestion(result.is_correct)
  } catch (err) {
    console.error('实操题批改失败:', err)
    practicalResult.value = {
      score: 0,
      is_correct: false,
      feedback: '批改服务暂时不可用，请稍后重试。',
      key_points: [],
      reference_answer: currentQuestion.value.correctAnswer || '',
    }
    practicalGraded.value = true
    currentQuestion.value.practicalGraded = true
    currentQuestion.value.practicalResult = practicalResult.value
    lockQuestion(false)
  } finally {
    practicalGrading.value = false
  }
}

// === 选项点击 ===
const selectOption = async (index: number) => {
  if (answered.value) return
  if (socraticLoading.value) return

  const correct = index === currentQuestion.value.correctIndex
  currentQuestion.value.selectedIndex = index
  showFeedback.value = true
  isCorrect.value = correct

  if (correct) {
    lockQuestion(true)
  } else {
    const nextRound = socraticRound.value + 1
    await fetchHeuristic(nextRound, index)
  }
}

// === 选项样式 ===
const optionClass = (index: number) => {
  if (answered.value) {
    if (index === currentQuestion.value.correctIndex) return 'correct'
    if (index === currentQuestion.value.selectedIndex && !isCorrect.value) return 'wrong'
    return ''
  }
  if (showFeedback.value && !isCorrect.value && !revealAnswer.value) {
    if (index === currentQuestion.value.selectedIndex) return 'wrong'
    return ''
  }
  if (currentQuestion.value.selectedIndex === index) return 'selected'
  return ''
}

// === 翻页 ===
const prevQuestion = () => {
  if (currentIndex.value > 0) {
    currentIndex.value--
    resetState()
    saveProgress()
  }
}

const nextQuestion = () => {
  if (currentIndex.value < questions.value.length - 1) {
    currentIndex.value++
    resetState()
    saveProgress()
  } else {
    saveProgress()
    router.push('/report')
  }
}

const resetState = () => {
  const q = currentQuestion.value
  answered.value = q?.answered ?? false
  showFeedback.value = q?.answered ?? false
  isCorrect.value = q?.finalCorrect ?? false
  socraticRound.value = 0
  socraticHistory.value = []
  revealAnswer.value = false
  socraticLoading.value = false
  // 实操题状态
  practicalAnswer.value = q?.practicalAnswer || ''
  practicalGrading.value = false
  practicalGraded.value = q?.practicalGraded ?? false
  practicalResult.value = q?.practicalResult || null
}

// === 答题进度持久化 ===
const saveProgress = async () => {
  if (!sessionId.value) return
  try {
    await api.savePracticeState(sessionId.value, {
      current_index: currentIndex.value,
      questions: questions.value.map((q: any) => ({
        question: q.question,
        selectedIndex: q.selectedIndex,
        answered: q.answered,
        finalCorrect: q.finalCorrect,
        practicalAnswer: q.practicalAnswer,
        practicalGraded: q.practicalGraded,
        practicalResult: q.practicalResult,
      })),
    })
  } catch { /* 静默失败，不影响答题流程 */ }
}

// === 初始化 ===
onMounted(() => {
  if (isLoggedIn.value && sessionId.value) {
    fetchQuestions()
  } else if (!isLoggedIn.value) {
    loading.value = false
    loadError.value = '请先登录'
  } else {
    loading.value = false
    loadError.value = '请先完成学情诊断'
  }
})
</script>

<style scoped>
.quiz-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 24px;
}
.opt-big {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 18px;
  border: 1px solid var(--line-2);
  border-radius: var(--radius-sm);
  margin-bottom: 10px;
  cursor: pointer;
  transition: all .15s;
}
.opt-big:hover { border-color: var(--text-3); }
.opt-big.correct { border-color: var(--ok); background: var(--ok-soft); }
.opt-big.wrong { border-color: var(--err); background: var(--err-soft); }
.opt-big.selected { border-color: var(--accent); background: var(--accent-soft); }
.opt-big__key {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid var(--line-2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
  transition: all .15s;
}
.opt-big.correct .opt-big__key { background: var(--ok); color: #fff; border-color: var(--ok); }
.opt-big.wrong .opt-big__key { background: var(--err); color: #fff; border-color: var(--err); }
.opt-big.selected .opt-big__key { background: var(--accent); color: #fff; border-color: var(--accent); }
.feedback-box {
  margin-top: 20px;
  padding: 18px 20px;
  border-radius: var(--radius-sm);
  font-size: 13.5px;
  line-height: 1.7;
}
.feedback-box.ok { background: var(--ok-soft); border: 1px solid #A7F3D0; }
.feedback-box.err { background: var(--err-soft); border: 1px solid #FECACA; }
.socratic-box {
  margin-top: 12px;
  padding: 14px 16px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
}
.mini-stat {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-radius: var(--radius-sm);
}
.mini-stat.ok { background: var(--ok-soft); }
.mini-stat.err { background: var(--err-soft); }
.animate-spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
@media (max-width: 900px) {
  .quiz-grid { grid-template-columns: 1fr; }
}
.practical-input-box {
  background: var(--bg-muted, #f7f8fa);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  padding: 18px 20px;
}
.practical-hint {
  font-size: 13px;
  color: var(--text-2);
  margin-bottom: 12px;
}
.practical-textarea {
  width: 100%;
  min-height: 160px;
  padding: 14px 16px;
  border: 1px solid var(--line-2);
  border-radius: var(--radius-sm);
  font-family: var(--mono), 'Consolas', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  resize: vertical;
  background: var(--bg, #fff);
  color: var(--text);
  transition: border-color .15s;
}
.practical-textarea:focus {
  outline: none;
  border-color: var(--accent);
}
.practical-textarea:disabled {
  opacity: .7;
  cursor: not-allowed;
}
.practical-score {
  font-size: 28px;
  font-weight: 700;
  font-family: var(--mono);
  letter-spacing: -.02em;
}
.practical-score.pass { color: var(--ok); }
.practical-score.fail { color: var(--err); }
.reference-answer-block {
  background: var(--bg, #fff);
  padding: 14px 16px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--line);
  font-size: 13px;
  font-family: var(--mono), 'Consolas', 'Courier New', monospace;
  line-height: 1.6;
  overflow-x: auto;
  white-space: pre-wrap;
  margin-top: 8px;
}
</style>
