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

              <!-- 苏格拉底式追问 -->
              <div v-if="!isCorrect && heuristicQuestion" class="mt-3 p-3 bg-white rounded border">
                <p class="text-sm font-medium text-blue-800">💡 思考一下：</p>
                <p class="text-sm mt-1">{{ heuristicQuestion }}</p>
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
  // 如果是字母（A/B/C/D），转为索引
  if (/^[A-D]$/.test(answer)) {
    return answer.charCodeAt(0) - 65
  }
  // 如果是选项文本，找匹配的索引（去掉前缀后比较）
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
  answered.value = true
  showFeedback.value = true
  isCorrect.value = index === currentQuestion.value.correctIndex

  if (!isCorrect.value) {
    try {
      const result = await api.submitFeedback({
        session_id: sessionId.value || 'demo',
        topic: 'Python 数据分析',
        question: currentQuestion.value.question,
        user_answer: String.fromCharCode(65 + index),
        correct_answer: currentQuestion.value.correctAnswer,
      })
      heuristicQuestion.value = result.heuristic_question || '试着从函数参数的角度思考一下。'
    } catch {
      heuristicQuestion.value = '试着从函数参数的角度思考一下。'
    }
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
