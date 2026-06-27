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

    <!-- 参考来源汇总 -->
    <UCard v-if="allSources.length > 0" class="mt-6">
      <template #header>
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-semibold">📚 参考来源汇总</h2>
          <UBadge variant="subtle">{{ allSources.length }} 个来源</UBadge>
        </div>
      </template>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div
          v-for="(src, idx) in allSources"
          :key="idx"
          class="p-3 rounded-lg border hover:border-primary/50 transition-colors group"
        >
          <div class="flex items-start gap-3">
            <span class="text-2xl flex-shrink-0">{{ src.icon }}</span>
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <span class="text-sm font-semibold text-gray-800 truncate">
                  {{ src.type === '书籍' ? '《' + src.name + '》' : src.name }}
                </span>
                <UBadge variant="subtle" size="xs">{{ src.type }}</UBadge>
              </div>
              <div class="mt-1 text-xs text-gray-500 space-y-0.5">
                <p v-if="src.author">作者：{{ src.author }}</p>
                <p v-if="src.year">年份：{{ src.year }}</p>
                <p v-if="src.chapter">章节：{{ src.chapter }}</p>
                <a
                  v-if="src.url"
                  :href="src.url"
                  target="_blank"
                  class="text-primary hover:underline inline-flex items-center gap-1"
                >
                  🔗 查看链接
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </UCard>
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

// ── 来源解析 ──
interface SourceInfo {
  icon: string
  type: string
  name: string
  author: string
  year: string
  chapter: string
  url: string
  raw: string
}

const allSources = ref<SourceInfo[]>([])

/** 从生成内容中解析所有来源标注 */
const parseSources = (content: string): SourceInfo[] => {
  if (!content) return []
  const sources: SourceInfo[] = []
  const seen = new Set<string>()

  // 匹配 📚 来源：《书名》(作者, 年份) 章节
  const bookRegex = /📚\s*来源[：:]\s*《([^》]+)》\s*\(([^,)]+)(?:,\s*([^)]+))?\)\s*(.*)?/g
  // 匹配 📄 来源：论文名
  const paperRegex = /📄\s*来源[：:]\s*(.+)/g
  // 匹配 📋 来源：标准名
  const standardRegex = /📋\s*来源[：:]\s*(.+)/g
  // 匹配 🔗 链接：URL
  const urlRegex = /🔗\s*(?:链接|URL)[：:]\s*(https?:\/\/[^\s<]+)/g

  // 提取书籍来源
  let match
  while ((match = bookRegex.exec(content)) !== null) {
    const key = match[1]
    if (seen.has(key)) continue
    seen.add(key)
    sources.push({
      icon: '📚',
      type: '书籍',
      name: match[1],
      author: match[2]?.trim() || '',
      year: match[3]?.trim() || '',
      chapter: match[4]?.trim() || '',
      url: '',
      raw: match[0],
    })
  }

  // 提取论文来源
  while ((match = paperRegex.exec(content)) !== null) {
    const name = match[1].trim()
    if (seen.has(name)) continue
    seen.add(name)
    sources.push({
      icon: '📄',
      type: '论文',
      name,
      author: '',
      year: '',
      chapter: '',
      url: '',
      raw: match[0],
    })
  }

  // 提取标准来源
  while ((match = standardRegex.exec(content)) !== null) {
    const name = match[1].trim()
    if (seen.has(name)) continue
    seen.add(name)
    sources.push({
      icon: '📋',
      type: '标准',
      name,
      author: '',
      year: '',
      chapter: '',
      url: '',
      raw: match[0],
    })
  }

  // 提取 URL（关联到已有来源）
  while ((match = urlRegex.exec(content)) !== null) {
    const url = match[1]
    // 尝试关联到最近的来源
    if (sources.length > 0 && !sources[sources.length - 1].url) {
      sources[sources.length - 1].url = url
    } else {
      sources.push({
        icon: '🔗',
        type: '网页',
        name: url,
        author: '',
        year: '',
        chapter: '',
        url,
        raw: match[0],
      })
    }
  }

  return sources
}

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
    // 来源标注高亮
    .replace(
      /(📚\s*来源[：:].+?)(?=\n|<br>|$)/g,
      '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-blue-50 text-blue-700 text-sm border border-blue-200 my-1">$1</span>'
    )
    .replace(
      /(📄\s*来源[：:].+?)(?=\n|<br>|$)/g,
      '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-purple-50 text-purple-700 text-sm border border-purple-200 my-1">$1</span>'
    )
    .replace(
      /(📋\s*来源[：:].+?)(?=\n|<br>|$)/g,
      '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-green-50 text-green-700 text-sm border border-green-200 my-1">$1</span>'
    )
    .replace(
      /(🔗\s*(?:链接|URL)[：:].+?)(?=\n|<br>|$)/g,
      '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-gray-50 text-gray-700 text-sm border border-gray-200 my-1">$1</span>'
    )
    .replace(
      /(权威度[：:]\s*★+)/g,
      '<span class="text-yellow-500 font-medium">$1</span>'
    )
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

    // 汇总所有资源中的来源标注
    const rawContents = [lectureContent.value, guideContent.value, projectContent.value].filter(Boolean)
    const combinedContent = rawContents.join('\n')
    allSources.value = parseSources(combinedContent)
  } catch (err: any) {
    console.warn('获取资源失败:', err)
    // 资源页面加载失败不弹 toast，显示空状态即可
  } finally {
    loading.value = false
  }
})
</script>
