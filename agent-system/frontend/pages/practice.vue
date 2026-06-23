<template>
  <div class="container mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold mb-6">反馈交互</h1>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
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
                <span>{{ option }}</span>
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

const questions = ref([
  {
    question: 'Pandas 中，如何选取 DataFrame 中 age 列大于 25 的行？',
    options: ['df[df.age > 25]', 'df.select(age > 25)', 'df.where(age > 25)', 'df.filter(age > 25)'],
    correctIndex: 0,
    explanation: '使用布尔索引 df[df.age > 25] 是 Pandas 中筛选行的标准方式。',
    selectedIndex: -1,
    answered: false,
    correctAnswer: 'A',
  },
  {
    question: 'NumPy 中，创建一个 3x3 全零矩阵的正确方法是？',
    options: ['np.zeros(3, 3)', 'np.zeros((3, 3))', 'np.zero(3,3)', 'np.create_zeros(3,3)'],
    correctIndex: 1,
    explanation: 'np.zeros() 接受一个元组作为形状参数，所以是 np.zeros((3, 3))。',
    selectedIndex: -1,
    answered: false,
    correctAnswer: 'B',
  },
  {
    question: 'Matplotlib 中，用于绘制折线图的方法是？',
    options: ['plt.line()', 'plt.plot()', 'plt.draw()', 'plt.chart()'],
    correctIndex: 1,
    explanation: 'plt.plot() 是 Matplotlib 中绘制折线图的主要方法。',
    selectedIndex: -1,
    answered: false,
    correctAnswer: 'B',
  },
])

const currentIndex = ref(0)
const answered = ref(false)
const showFeedback = ref(false)
const isCorrect = ref(false)
const heuristicQuestion = ref('')

const currentQuestion = computed(() => questions.value[currentIndex.value])
const correctCount = computed(() => questions.value.filter(q => q.answered && q.selectedIndex === q.correctIndex).length)
const wrongCount = computed(() => questions.value.filter(q => q.answered && q.selectedIndex !== q.correctIndex).length)

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
    // 调用后端 API 获取苏格拉底式追问
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
  answered.value = currentQuestion.value.answered
  showFeedback.value = answered.value
  isCorrect.value = currentQuestion.value.selectedIndex === currentQuestion.value.correctIndex
  heuristicQuestion.value = ''
}
</script>
