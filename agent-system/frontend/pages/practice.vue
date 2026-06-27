<template>
  <div class="container mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold mb-6">反馈交互</h1>

    <!-- 加载中 -->
    <div v-if="loading" class="flex flex-col items-center justify-center py-20">
      <UIcon name="i-heroicons-arrow-path" class="w-12 h-12 text-primary animate-spin mb-4" />
      <p class="text-gray-500">正在生成试题，请稍候...</p>
    </div>

    <!-- 加载失败 -->
    <div v-else-if="loadError" class="flex flex-col items-center justify-center py-20">
      <UIcon name="i-heroicons-exclamation-triangle" class="w-12 h-12 text-red-400 mb-4" />
      <p class="text-red-500 mb-4">{{ loadError }}</p>
      <UButton @click="fetchQuestions">重新加载</UButton>
    </div>

    <!-- 无试题 -->
    <div v-else-if="questions.length === 0" class="flex flex-col items-center justify-center py-20">
      <UIcon name="i-heroicons-document-text" class="w-12 h-12 text-gray-300 mb-4" />
      <p class="text-gray-500 mb-4">暂无试题</p>
      <UButton @click="fetchQuestions">生成试题</UButton>
    </div>

    <!-- 答题区域 -->
    <div v-else class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- 答题区域 -->
      <div class="lg:col-span-2">
        <UCard>
          <template #header>
            <div class="flex items-center justify-between">
              <h2 class="text-lg font-semibold">当前题目</h2>
              <UBadge>第 {{ currentIndex + 1 }} / {{ questions.length }} 题</UBadge>
            </div>
          </template>

          <div class="space-y-6">
            <p class="text-lg">{{ currentQuestion.question }}</p>

            <div class="space-y-3">
              <div
                v-for="(option, index) in currentQuestion.options"
                :key="index"
                class="flex items-center gap-3 p-4 rounded-lg border cursor-pointer transition-all"
                :class="optionClass(index)"
                @click="selectOption(index)"
              >
                <span class="w-8 h-8 flex items-center justify-center rounded-full border font-medium">
                  {{ String.fromCharCode(65 + index) }}
                </span>
                <span>{{ stripOptionPrefix(option) }}</span>
              </div>
            </div>

            <!-- 反馈区域 -->
            <div v-if="showFeedback" class="p-4 rounded-lg" :class="feedbackClass">
              <p class="font-semibold mb-1">{{ isCorrect ? '✅ 回答正确！' : '❌ 回答错误' }}</p>

              <!-- 答对 或 追问耗尽时显示解析 -->
              <p v-if="answered" class="text-sm">{{ currentQuestion.explanation }}</p>

              <!-- 苏格拉底式追问提示 -->
              <div v-if="!isCorrect && !answered" class="mt-3 space-y-2">
                <div v-for="(h, idx) in socraticHistory" :key="idx"
                     class="p-3 bg-white rounded border"
                     :class="idx === socraticHistory.length - 1 ? 'border-blue-300' : ''">
                  <p class="text-sm font-medium text-blue-800">💡 提示（第 {{ h.round }} 轮）：</p>
                  <p class="text-sm mt-1">{{ h.hint }}</p>
                </div>
                <div v-if="socraticLoading" class="flex items-center gap-2 text-sm text-gray-500">
                  <UIcon name="i-heroicons-arrow-path" class="w-4 h-4 animate-spin" />
                  正在生成提示...
                </div>
                <p class="text-sm text-primary font-medium mt-2">
                  👆 请阅读提示后，重新选择一个答案
                </p>
              </div>

              <!-- 揭示答案（追问耗尽） -->
              <div v-if="revealAnswer" class="mt-3 p-3 bg-yellow-50 rounded border border-yellow-200">
                <p class="text-sm font-medium text-yellow-800">📌 正确答案：{{ currentQuestion.correctAnswer }}</p>
                <p class="text-sm mt-1 text-gray-600">{{ currentQuestion.explanation }}</p>
              </div>
            </div>
          </div>

          <template #footer>
            <div class="flex justify-between">
              <UButton variant="ghost" :disabled="currentIndex === 0" @click="prevQuestion">
                上一题
              </UButton>
              <UButton :disabled="!answered" @click="nextQuestion">
                {{ currentIndex === questions.length - 1 ? '查看报告' : '下一题' }}
              </UButton>
            </div>
          </template>
        </UCard>
      </div>

      <!-- 答题统计 -->
      <div>
        <UCard>
          <template #header>
            <h2 class="text-lg font-semibold">答题统计</h2>
          </template>

          <div class="space-y-4">
            <div class="text-center">
              <p class="text-3xl font-bold text-primary">{{ correctCount }}/{{ questions.length }}</p>
              <p class="text-sm text-gray-500">正确率 {{ questions.length ? (correctCount / questions.length * 100).toFixed(0) : 0 }}%</p>
            </div>

            <UProgress :value="questions.length ? (correctCount / questions.length) * 100 : 0" color="green" />

            <div class="grid grid-cols-2 gap-2 text-center text-sm">
              <div class="p-2 rounded bg-green-50">
                <p class="font-bold text-green-700">{{ correctCount }}</p>
                <p class="text-green-600">正确</p>
              </div>
              <div class="p-2 rounded bg-red-50">
                <p class="font-bold text-red-700">{{ wrongCount }}</p>
                <p class="text-red-600">错误</p>
              </div>
            </div>

            <!-- 重新生成按钮 -->
            <UButton block variant="outline" @click="fetchQuestions" :loading="loading">
              重新生成试题
            </UButton>
          </div>
        </UCard>
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
const answered = ref(false)         // true = 本题最终锁定（答对 或 追问耗尽）
const showFeedback = ref(false)
const isCorrect = ref(false)
const heuristicQuestion = ref('')

// === 多轮追问状态 ===
const socraticRound = ref(0)        // 0 = 还没触发追问，1/2/3 = 追问轮次
const socraticHistory = ref<{round: number, hint: string}[]>([])
const revealAnswer = ref(false)
const socraticLoading = ref(false)

// === 计算属性 ===
const currentQuestion = computed(() => questions.value[currentIndex.value])
const correctCount = computed(() => questions.value.filter(q => q.finalCorrect === true).length)
const wrongCount = computed(() => questions.value.filter(q => q.answered && q.finalCorrect === false).length)

// 是否处于追问状态（答错了但还没锁定）
const inSocraticMode = computed(() =>
  showFeedback.value && !isCorrect.value && !revealAnswer.value
)

// === 辅助函数 ===

/** 去掉选项前面的 A. B. C. D. 前缀 */
const stripOptionPrefix = (option: string) => {
  return option.replace(/^[A-Da-d][.\s、]+/, '')
}

/** 将后端 correct_answer 转为数字索引 */
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
      finalCorrect: null,   // null=未作答, true=最终答对, false=最终答错
      correctAnswer: q.correct_answer || '',
    }))
    currentIndex.value = 0
    resetState()
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
      topic: currentQuestion.value.topic || 'CNC 数控编程',
      question: currentQuestion.value.question,
      user_answer: String.fromCharCode(65 + optionIndex),
      correct_answer: currentQuestion.value.correctAnswer,
      round,
      heuristic_context: socraticHistory.value.map(h => h.hint).join('\n'),
    })

    socraticRound.value = round
    revealAnswer.value = result.reveal_answer || false

    if (result.heuristic_question) {
      heuristicQuestion.value = result.heuristic_question
      socraticHistory.value.push({ round, hint: result.heuristic_question })
    }

    if (result.reveal_answer) {
      // 追问耗尽，揭示答案，锁定本题
      heuristicQuestion.value = ''
      lockQuestion(false)
    }
  } catch (err) {
    console.error('追问 API 失败:', err)
    // API 失败时也给一个通用提示，不要卡死
    const fallbackHint = `提示：正确答案是 ${currentQuestion.value.correctAnswer}，看看解析吧。`
    heuristicQuestion.value = fallbackHint
    socraticHistory.value.push({ round, hint: fallbackHint })
    socraticRound.value = round
    // API 失败也揭示答案
    revealAnswer.value = true
    lockQuestion(false)
  } finally {
    socraticLoading.value = false
  }
}

// === 锁定本题（答对或追问耗尽） ===
const lockQuestion = (correct: boolean) => {
  answered.value = true
  currentQuestion.value.answered = true
  currentQuestion.value.finalCorrect = correct
  isCorrect.value = correct
  showFeedback.value = true
}

// === 选项点击 ===
const selectOption = async (index: number) => {
  // 已锁定的题不可再选
  if (answered.value) return
  // 追问加载中不可选
  if (socraticLoading.value) return

  const correct = index === currentQuestion.value.correctIndex
  currentQuestion.value.selectedIndex = index
  showFeedback.value = true
  isCorrect.value = correct

  if (correct) {
    // 答对了，锁定
    lockQuestion(true)
  } else {
    // 答错了，发起追问
    const nextRound = socraticRound.value + 1
    await fetchHeuristic(nextRound, index)
  }
}

// === 选项样式 ===
const optionClass = (index: number) => {
  // 锁定后：显示最终结果
  if (answered.value) {
    if (index === currentQuestion.value.correctIndex) return 'border-green-400 bg-green-50'
    if (index === currentQuestion.value.selectedIndex && !isCorrect.value) return 'border-red-400 bg-red-50'
    return 'border-gray-200 opacity-60'
  }
  // 追问中：高亮当前选中的（用户可以重新选）
  if (showFeedback.value && inSocraticMode.value) {
    if (index === currentQuestion.value.selectedIndex) return 'border-red-400 bg-red-50'
    return 'border-gray-200 hover:border-primary hover:bg-primary/5 cursor-pointer'
  }
  // 未作答
  if (currentQuestion.value.selectedIndex === index) return 'border-primary bg-primary/5'
  return 'border-gray-200 hover:border-gray-300 cursor-pointer'
}

const feedbackClass = computed(() =>
  isCorrect.value ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
)

// === 翻页 ===
const prevQuestion = () => {
  if (currentIndex.value > 0) {
    currentIndex.value--
    resetState()
  }
}

const nextQuestion = () => {
  if (currentIndex.value < questions.value.length - 1) {
    currentIndex.value++
    resetState()
  } else {
    router.push('/report')
  }
}

const resetState = () => {
  const q = currentQuestion.value
  answered.value = q?.answered ?? false
  showFeedback.value = q?.answered ?? false
  isCorrect.value = q?.finalCorrect ?? false
  heuristicQuestion.value = ''
  socraticRound.value = 0
  socraticHistory.value = []
  revealAnswer.value = false
  socraticLoading.value = false
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
