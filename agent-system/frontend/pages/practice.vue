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
              <p class="text-sm">{{ currentQuestion.explanation }}</p>

              <!-- 苏格拉底式追问（多轮） -->
              <div v-if="!isCorrect && (heuristicQuestion || revealAnswer)" class="mt-3 space-y-3">
                <!-- 追问历史 -->
                <div v-for="(h, idx) in socraticHistory" :key="idx" class="p-3 bg-white rounded border">
                  <p class="text-sm font-medium text-blue-800">💡 第 {{ h.round }} 轮提示：</p>
                  <p class="text-sm mt-1">{{ h.question }}</p>
                  <p class="text-sm mt-1 text-gray-600">你的回答：{{ h.answer }}</p>
                </div>

                <!-- 当前追问 -->
                <div v-if="heuristicQuestion && !revealAnswer" class="p-3 bg-white rounded border">
                  <p class="text-sm font-medium text-blue-800">💡 第 {{ socraticRound }} 轮思考：</p>
                  <p class="text-sm mt-1">{{ heuristicQuestion }}</p>

                  <!-- 追问回答输入框 -->
                  <div class="mt-3 flex gap-2">
                    <UInput
                      v-model="socraticInput"
                      placeholder="输入你的思考..."
                      class="flex-1"
                      @keyup.enter="submitSocraticAnswer"
                    />
                    <UButton size="sm" @click="submitSocraticAnswer">提交</UButton>
                  </div>
                </div>

                <!-- 揭示答案 -->
                <div v-if="revealAnswer" class="p-3 bg-yellow-50 rounded border border-yellow-200">
                  <p class="text-sm font-medium text-yellow-800">📌 正确答案：</p>
                  <p class="text-sm mt-1 font-semibold">{{ currentQuestion.correctAnswer }}</p>
                  <p class="text-sm mt-1 text-gray-600">{{ currentQuestion.explanation }}</p>
                </div>
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
const answered = ref(false)
const showFeedback = ref(false)
const isCorrect = ref(false)
const heuristicQuestion = ref('')

// === 多轮追问状态 ===
const socraticRound = ref(1)
const socraticHistory = ref<{round: number, question: string, answer: string}[]>([])
const socraticInput = ref('')
const revealAnswer = ref(false)

// === 计算属性 ===
const currentQuestion = computed(() => questions.value[currentIndex.value])
const correctCount = computed(() => questions.value.filter(q => q.answered && q.selectedIndex === q.correctIndex).length)
const wrongCount = computed(() => questions.value.filter(q => q.answered && q.selectedIndex !== q.correctIndex).length)

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

// === 追问 API 调用 ===
const fetchHeuristic = async (round: number, prevContext: string, optionIndex?: number) => {
  try {
    const result = await api.submitFeedback({
      session_id: sessionId.value || 'demo',
      topic: currentQuestion.value.topic || 'Python 数据分析',
      question: currentQuestion.value.question,
      user_answer: optionIndex !== undefined
        ? String.fromCharCode(65 + optionIndex)
        : socraticInput.value,
      correct_answer: currentQuestion.value.correctAnswer,
      round,
      heuristic_context: prevContext,
    })

    socraticRound.value = round
    revealAnswer.value = result.reveal_answer || false

    if (result.heuristic_question) {
      heuristicQuestion.value = result.heuristic_question
    }

    if (result.reveal_answer) {
      heuristicQuestion.value = ''
      answered.value = true
    }
  } catch {
    heuristicQuestion.value = '试着从函数参数的角度思考一下。'
  }
}

// === 追问回答提交 ===
const submitSocraticAnswer = async () => {
  if (!socraticInput.value.trim()) return

  socraticHistory.value.push({
    round: socraticRound.value,
    question: heuristicQuestion.value,
    answer: socraticInput.value,
  })

  const prevContext = socraticHistory.value
    .map(h => `问：${h.question}\n答：${h.answer}`)
    .join('\n')

  socraticInput.value = ''
  await fetchHeuristic(socraticRound.value + 1, prevContext)
}

// === 答题逻辑 ===
const optionClass = (index: number) => {
  if (!showFeedback.value) {
    return currentQuestion.value.selectedIndex === index
      ? 'border-primary bg-primary/5'
      : 'border-gray-200 hover:border-gray-300'
  }
  if (index === currentQuestion.value.correctIndex) return 'border-green-400 bg-green-50'
  if (index === currentQuestion.value.selectedIndex && index !== currentQuestion.value.correctIndex) return 'border-red-400 bg-red-50'
  return 'border-gray-200'
}

const feedbackClass = computed(() =>
  isCorrect.value ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
)

const selectOption = async (index: number) => {
  if (answered.value) return
  currentQuestion.value.selectedIndex = index
  currentQuestion.value.answered = true
  isCorrect.value = index === currentQuestion.value.correctIndex

  if (!isCorrect.value) {
    showFeedback.value = true
    await fetchHeuristic(1, '', index)
  } else {
    showFeedback.value = true
    answered.value = true
  }
}

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
  answered.value = currentQuestion.value?.answered ?? false
  showFeedback.value = answered.value
  isCorrect.value = currentQuestion.value?.selectedIndex === currentQuestion.value?.correctIndex
  heuristicQuestion.value = ''
  // 重置追问状态
  socraticRound.value = 1
  socraticHistory.value = []
  socraticInput.value = ''
  revealAnswer.value = false
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
