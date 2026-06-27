<template>
  <div class="page page--wide">
    <div class="page-head">
      <p class="page-head__eyebrow">Step 4</p>
      <h1 class="page-head__title">个性化学习资源</h1>
      <p class="page-head__desc">系统已为你生成多类资源，每条知识点均标注来源出处，难度适配你的当前水平。</p>
    </div>

    <div v-if="loading" class="text-center py-12">
      <div class="animate-spin" style="width: 32px; height: 32px; margin: 0 auto; border: 3px solid var(--line); border-top-color: var(--accent); border-radius: 50%;"></div>
      <p class="mt-4 text-text-2">正在加载资源...</p>
    </div>

    <div v-else-if="resources.length === 0" class="text-center py-12">
      <p class="text-text-3">暂无生成资源，请先提交画像并触发生成</p>
      <NuxtLink to="/profile" class="btn btn--primary mt-4">去提交画像</NuxtLink>
    </div>

    <div v-else>
      <!-- Tabs -->
      <div class="tabs-bar">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="tab-btn"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </div>

      <!-- 讲义 -->
      <div v-if="activeTab === 'lecture'" class="card">
        <div class="res-meta">
          <span class="badge badge--accent">L2 进阶</span>
          <span>·</span><span>约 12 分钟阅读</span>
          <span>·</span><span>已通过审核纠偏</span>
        </div>
        <div class="prose" v-html="renderMarkdown(lectureContent)" />
      </div>

      <!-- 实验指导 -->
      <div v-if="activeTab === 'guide'" class="card">
        <div class="res-meta">
          <span class="badge badge--accent">L2 进阶</span>
          <span>·</span><span>预计 30 分钟</span>
          <span>·</span><span>含完整代码与数据集</span>
        </div>
        <div class="prose" v-html="renderMarkdown(guideContent)" />
      </div>

      <!-- 项目案例 -->
      <div v-if="activeTab === 'project'" class="card">
        <div class="res-meta">
          <span class="badge badge--accent">L2 进阶</span>
          <span>·</span><span>综合项目</span>
          <span>·</span><span>含完整数据集与解答</span>
        </div>
        <div class="prose" v-html="renderMarkdown(projectContent)" />
      </div>

      <!-- 试题 -->
      <div v-if="activeTab === 'test'">
        <div v-for="(q, idx) in testQuestions" :key="idx" class="q-card">
          <div class="q-head">
            <span style="font-family: var(--mono); font-size: 13px; color: var(--text-3)">Q{{ idx + 1 }}</span>
            <span class="badge" :class="getQuestionBadgeClass(q.question_type)">{{ getQuestionTypeText(q.question_type) }}</span>
            <span style="font-size: 14.5px; font-weight: 600">{{ q.question }}</span>
          </div>

          <!-- 选择题/判断题选项 -->
          <template v-if="q.question_type !== 'practical'">
            <div
              v-for="(opt, oIdx) in q.options"
              :key="oIdx"
              class="opt-row"
              :class="{
                'correct': q.answered && oIdx === q.correctIndex,
                'wrong': q.answered && q.selectedIndex === oIdx && oIdx !== q.correctIndex,
              }"
              @click="selectAnswer(idx, oIdx)"
            >
              <div class="opt-key">{{ String.fromCharCode(65 + oIdx) }}</div>
              <span>{{ opt }}</span>
            </div>
          </template>

          <!-- 实操题 -->
          <div v-else class="p-4" style="background: var(--bg-muted); border-radius: var(--radius-sm);">
            <p class="text-sm text-text-2 mb-2">请在编辑器中完成以下操作：</p>
            <pre style="background: var(--bg); padding: 12px; border-radius: var(--radius-sm); border: 1px solid var(--line); font-size: 13px; overflow-x: auto;"><code>{{ q.correct_answer }}</code></pre>
          </div>

          <!-- 解析 -->
          <div v-if="q.answered || q.question_type === 'practical'" class="explain-box">
            <strong>解析</strong>：{{ q.explanation }}
          </div>
        </div>
      </div>

      <!-- 参考来源汇总 -->
      <div v-if="allSources.length > 0" class="card" style="margin-top: 24px;">
        <div class="card__head">
          <h2 class="card__title">📚 参考来源汇总</h2>
          <span class="badge badge--mute">{{ allSources.length }} 个来源</span>
        </div>

        <div class="sources-grid">
          <div v-for="(src, idx) in allSources" :key="idx" class="source-item">
            <div style="display: flex; align-items: start; gap: 12px;">
              <span style="font-size: 24px; flex-shrink: 0;">{{ src.icon }}</span>
              <div style="min-width: 0; flex: 1;">
                <div style="display: flex; align-items: center; gap: 8px;">
                  <span class="text-sm font-semibold text-text truncate">
                    {{ src.type === '书籍' ? '《' + src.name + '》' : src.name }}
                  </span>
                  <span class="badge badge--mute" style="font-size: 10px;">{{ src.type }}</span>
                </div>
                <div class="mt-1 text-xs text-text-3" style="line-height: 1.6;">
                  <p v-if="src.author">作者：{{ src.author }}</p>
                  <p v-if="src.year">年份：{{ src.year }}</p>
                  <p v-if="src.chapter">章节：{{ src.chapter }}</p>
                  <a
                    v-if="src.url"
                    :href="src.url"
                    target="_blank"
                    class="text-accent hover:underline"
                  >
                    🔗 查看链接
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const api = useApi()
const { sessionId } = useSession()

const loading = ref(true)
const resources = ref<any[]>([])
const activeTab = ref('lecture')

const lectureContent = ref('')
const guideContent = ref('')
const projectContent = ref('')
const testQuestions = ref<any[]>([])

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

const tabs = [
  { key: 'lecture', label: '定制讲义' },
  { key: 'guide', label: '实验指导' },
  { key: 'project', label: '项目案例' },
  { key: 'test', label: '分阶试题' },
]

// 获取试题类型徽章样式
const getQuestionBadgeClass = (type: string): string => {
  const map: Record<string, string> = {
    multiple_choice: 'badge--accent',
    true_false: 'badge--ok',
    practical: 'badge--warn',
  }
  return map[type] || 'badge--mute'
}

// 获取试题类型文本
const getQuestionTypeText = (type: string): string => {
  const map: Record<string, string> = {
    multiple_choice: '选择题',
    true_false: '判断题',
    practical: '实操题',
  }
  return map[type] || '未知'
}

/** 从生成内容中解析所有来源标注 */
const parseSources = (content: string): SourceInfo[] => {
  if (!content) return []
  const sources: SourceInfo[] = []
  const seen = new Set<string>()

  const bookRegex = /📚\s*来源[：:]\s*《([^》]+)》\s*\(([^,)]+)(?:,\s*([^)]+))?\)\s*(.*)?/g
  const paperRegex = /📄\s*来源[：:]\s*(.+)/g
  const standardRegex = /📋\s*来源[：:]\s*(.+)/g
  const urlRegex = /🔗\s*(?:链接|URL)[：:]\s*(https?:\/\/[^\s<]+)/g

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

  while ((match = urlRegex.exec(content)) !== null) {
    const url = match[1]
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

const renderMarkdown = (md: string) => {
  if (!md) return '<p class="text-text-3">暂无内容</p>'
  return md
    .replace(/^### (.*$)/gm, '<h3>$1</h3>')
    .replace(/^## (.*$)/gm, '<h2>$1</h2>')
    .replace(/^# (.*$)/gm, '<h1>$1</h1>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>')
    .replace(
      /(📚\s*来源[：:].+?)(?=\n|<br>|$)/g,
      '<span class="source-tag">$1</span>'
    )
    .replace(
      /(📄\s*来源[：:].+?)(?=\n|<br>|$)/g,
      '<span class="source-tag">$1</span>'
    )
    .replace(
      /(📋\s*来源[：:].+?)(?=\n|<br>|$)/g,
      '<span class="source-tag">$1</span>'
    )
    .replace(
      /(🔗\s*(?:链接|URL)[：:].+?)(?=\n|<br>|$)/g,
      '<span class="source-tag">$1</span>'
    )
    .replace(
      /(权威度[：:]\s*★+)/g,
      '<span style="color: var(--warn); font-weight: 500;">$1</span>'
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

    const rawContents = [lectureContent.value, guideContent.value, projectContent.value].filter(Boolean)
    const combinedContent = rawContents.join('\n')
    allSources.value = parseSources(combinedContent)
  } catch (err: any) {
    console.warn('获取资源失败:', err)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.tabs-bar {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 28px;
}
.tab-btn {
  font-size: 13px;
  color: var(--text-2);
  font-weight: 500;
  padding: 12px 16px;
  position: relative;
  transition: color .15s;
  background: none;
  border: none;
  cursor: pointer;
}
.tab-btn:hover { color: var(--text); }
.tab-btn.active { color: var(--text); }
.tab-btn.active::after {
  content: "";
  position: absolute;
  left: 16px;
  right: 16px;
  bottom: -1px;
  height: 2px;
  background: var(--accent);
  border-radius: 99px;
}
.res-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: var(--text-3);
  margin-bottom: 20px;
}
.source-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11.5px;
  color: var(--accent);
  background: var(--accent-soft);
  padding: 3px 9px;
  border-radius: 4px;
  margin: 0 4px;
}
.q-card {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 22px 24px;
  margin-bottom: 16px;
}
.q-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}
.opt-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  margin-bottom: 8px;
  cursor: pointer;
  transition: all .15s;
}
.opt-row:hover {
  border-color: var(--line-2);
  background: var(--bg-soft);
}
.opt-row.correct {
  border-color: var(--ok);
  background: var(--ok-soft);
}
.opt-row.correct .opt-key {
  background: var(--ok);
  color: #fff;
  border-color: var(--ok);
}
.opt-row.wrong {
  border-color: var(--err);
  background: var(--err-soft);
}
.opt-row.wrong .opt-key {
  background: var(--err);
  color: #fff;
  border-color: var(--err);
}
.opt-key {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 1px solid var(--line-2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-2);
  flex-shrink: 0;
}
.explain-box {
  margin-top: 14px;
  padding: 14px 16px;
  background: var(--accent-soft);
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: var(--text-2);
  line-height: 1.7;
}
.sources-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}
.source-item {
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  transition: border-color .15s;
}
.source-item:hover {
  border-color: var(--accent);
}
.animate-spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
@media (max-width: 760px) {
  .sources-grid { grid-template-columns: 1fr; }
}
</style>
