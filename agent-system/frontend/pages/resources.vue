<template>
  <div class="container mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold mb-6">个性化资源展示</h1>

    <div v-if="loading" class="text-center py-12">
      <UIcon name="i-heroicons-arrow-path" class="w-8 h-8 animate-spin text-primary mx-auto" />
      <p class="mt-2 text-gray-500">正在加载资源...</p>
    </div>

    <div v-else-if="resources.length === 0" class="text-center py-12">
      <p class="text-gray-500">暂无生成资源，请先提交画像并触发生成</p>
      <UButton to="/profile" class="mt-4">去提交画像</UButton>
    </div>

    <UTabs v-else :items="tabs" class="w-full">
      <!-- 讲义 Tab -->
      <template #lecture>
        <UCard>
          <div class="prose max-w-none" v-html="renderMarkdown(lectureContent)" />
        </UCard>
      </template>

      <!-- 实验指导 Tab -->
      <template #guide>
        <UCard>
          <div class="prose max-w-none" v-html="renderMarkdown(guideContent)" />
        </UCard>
      </template>

      <!-- 项目案例 Tab -->
      <template #project>
        <UCard>
          <div class="prose max-w-none" v-html="renderMarkdown(projectContent)" />
        </UCard>
      </template>

      <!-- 试题 Tab -->
      <template #test>
        <div class="space-y-4">
          <UCard v-for="(q, index) in testQuestions" :key="index">
            <div class="flex items-center gap-2 mb-3">
              <UBadge :color="q.question_type === 'multiple_choice' ? 'blue' : q.question_type === 'true_false' ? 'green' : 'orange'" variant="subtle" size="xs">
                {{ q.question_type === 'multiple_choice' ? '选择题' : q.question_type === 'true_false' ? '判断题' : '实操题' }}
              </UBadge>
              <h3 class="font-semibold">{{ index + 1 }}. {{ q.question }}</h3>
            </div>

            <!-- 选择题/判断题选项 -->
            <div v-if="q.question_type !== 'practical'" class="space-y-2">
              <div
                v-for="(option, oIndex) in q.options"
                :key="oIndex"
                class="flex items-center gap-2 p-2 rounded border cursor-pointer hover:bg-gray-50"
                :class="{
                  'border-green-400 bg-green-50': q.answered && oIndex === q.correctIndex,
                  'border-red-400 bg-red-50': q.answered && q.selectedIndex === oIndex && oIndex !== q.correctIndex,
                }"
                @click="selectAnswer(index, oIndex)"
              >
                <span class="font-medium text-gray-500">{{ String.fromCharCode(65 + oIndex) }}.</span>
                <span>{{ option }}</span>
              </div>
            </div>

            <!-- 实操题 -->
            <div v-else class="p-4 bg-gray-50 rounded-lg">
              <p class="text-sm text-gray-600 mb-2">请在编辑器中完成以下操作：</p>
              <pre class="bg-white p-3 rounded border text-sm overflow-x-auto"><code>{{ q.correct_answer }}</code></pre>
            </div>

            <!-- 解析 -->
            <div v-if="q.answered || q.question_type === 'practical'" class="mt-3 p-3 rounded bg-blue-50 text-sm text-blue-800">
              <strong>解析：</strong>{{ q.explanation }}
            </div>
          </UCard>
        </div>
      </template>
    </UTabs>
  </div>
</template>

<script setup lang="ts">
const api = useApi()
const { sessionId } = useSession()

const loading = ref(true)
const resources = ref<any[]>([])

const lectureContent = ref('')
const guideContent = ref('')
const projectContent = ref('')
const testQuestions = ref<any[]>([])

const tabs = [
  { key: 'lecture', label: '定制讲义', slot: 'lecture' },
  { key: 'guide', label: '实验指导', slot: 'guide' },
  { key: 'project', label: '项目案例', slot: 'project' },
  { key: 'test', label: '分阶试题', slot: 'test' },
]

const renderMarkdown = (md: string) => {
  if (!md) return '<p class="text-gray-400">暂无内容</p>'
  return md
    .replace(/^### (.*$)/gm, '<h3>$1</h3>')
    .replace(/^## (.*$)/gm, '<h2>$1</h2>')
    .replace(/^# (.*$)/gm, '<h1>$1</h1>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>')
    .replace(/\n/g, '<br>')
}

const selectAnswer = (questionIndex: number, optionIndex: number) => {
  const q = testQuestions.value[questionIndex]
  if (q.answered || q.question_type === 'practical') return
  q.selectedIndex = optionIndex
  q.answered = true
}

onMounted(async () => {
  if (!sessionId.value) {
    loading.value = false
    return
  }

  try {
    const data = await api.getResources(sessionId.value)
    resources.value = data

    for (const res of data) {
      const content = typeof res.content === 'string' ? res.content : JSON.stringify(res.content)

      if (res.type === 'lecture') {
        lectureContent.value = content
      } else if (res.type === 'guide') {
        guideContent.value = content
      } else if (res.type === 'project') {
        projectContent.value = content
      } else if (res.type === 'test') {
        // 试题可能是嵌套结构 {questions: [...]}
        let questions: any[] = []
        if (typeof res.content === 'string') {
          try { questions = JSON.parse(res.content).questions || [] } catch { questions = [] }
        } else if (res.content?.questions) {
          questions = res.content.questions
        } else if (Array.isArray(res.content)) {
          questions = res.content
        }

        testQuestions.value = questions.map((q: any) => ({
          ...q,
          correctIndex: q.options?.findIndex((o: string) => o === q.correct_answer || o.startsWith(q.correct_answer)) ?? 0,
          selectedIndex: -1,
          answered: false,
        }))
      }
    }
  } catch (err) {
    console.warn('获取资源失败:', err)
  } finally {
    loading.value = false
  }
})
</script>
