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
        <MarkdownRenderer :content="lectureContent" />
      </div>

      <!-- 实验指导 -->
      <div v-if="activeTab === 'guide'" class="card">
        <div class="res-meta">
          <span class="badge badge--accent">L2 进阶</span>
          <span>·</span><span>预计 30 分钟</span>
          <span>·</span><span>含完整代码与数据集</span>
        </div>
        <MarkdownRenderer :content="guideContent" />
      </div>

      <!-- 项目案例 -->
      <div v-if="activeTab === 'project'" class="card">
        <div class="res-meta">
          <span class="badge badge--accent">L2 进阶</span>
          <span>·</span><span>综合项目</span>
          <span>·</span><span>含完整数据集与解答</span>
        </div>
        <MarkdownRenderer :content="projectContent" />
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

          <!-- 实操题：文本输入 + 批改 -->
          <div v-else class="practical-input-box">
            <p class="text-sm text-text-2 mb-2">请在下方输入你的答案（G 代码、操作步骤、工艺分析等）：</p>
            <textarea
              v-model="q.practicalAnswer"
              class="practical-textarea"
              :disabled="q.practicalGraded"
              placeholder="在此输入你的答案..."
              rows="6"
            />
            <div style="display: flex; justify-content: flex-end; margin-top: 12px">
              <button
                class="btn btn--primary"
                :disabled="!q.practicalAnswer?.trim() || q.practicalGrading || q.practicalGraded"
                @click="submitPracticalAnswer(idx)"
              >
                {{ q.practicalGrading ? '批改中...' : '提交批改' }}
              </button>
            </div>

            <!-- 批改结果 -->
            <div v-if="q.practicalGraded" style="margin-top: 16px">
              <div class="feedback-box" :class="q.practicalResult?.is_correct ? 'ok' : 'err'">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px">
                  <div style="font-weight: 600">{{ q.practicalResult?.is_correct ? '✅ 通过' : '❌ 未通过' }}</div>
                  <div class="practical-score" :class="q.practicalResult?.is_correct ? 'pass' : 'fail'">
                    {{ q.practicalResult?.score }}<span style="font-size: 14px; opacity: .6">/100</span>
                  </div>
                </div>
                <div class="bar" style="margin-bottom: 14px">
                  <div class="bar__fill" :class="q.practicalResult?.is_correct ? 'ok' : 'err'" :style="{ width: (q.practicalResult?.score || 0) + '%' }" />
                </div>
                <div style="font-size: 13.5px; line-height: 1.7; margin-bottom: 12px">{{ q.practicalResult?.feedback }}</div>
                <div v-if="q.practicalResult?.key_points?.length" style="font-size: 13px; line-height: 1.8; margin-bottom: 12px">
                  <div style="font-weight: 600; font-size: 12px; color: var(--accent); margin-bottom: 6px">📋 关键要点</div>
                  <ul style="margin: 0; padding-left: 18px">
                    <li v-for="(kp, kIdx) in q.practicalResult?.key_points" :key="kIdx">{{ kp }}</li>
                  </ul>
                </div>
                <details>
                  <summary style="font-size: 13px; font-weight: 600; color: var(--text-2); cursor: pointer; padding: 4px 0">📖 查看参考答案</summary>
                  <pre class="reference-answer-block"><code>{{ q.practicalResult?.reference_answer }}</code></pre>
                </details>
              </div>
            </div>
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

    <!-- 底部导航：进入答题练习 -->
    <div v-if="!loading && resources.length > 0" style="display: flex; gap: 12px; justify-content: center; margin-top: 32px">
      <NuxtLink to="/workflow" class="btn btn--ghost btn--lg">← 重新生成资源</NuxtLink>
      <NuxtLink to="/practice" class="btn btn--primary btn--lg">进入答题练习 →</NuxtLink>
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
const currentTopic = ref('')

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

const selectAnswer = (questionIndex: number, optionIndex: number) => {
  const q = testQuestions.value[questionIndex]
  if (q.answered || q.question_type === 'practical') return
  q.selectedIndex = optionIndex
  q.answered = true
}

// === 实操题批改 ===
const submitPracticalAnswer = async (questionIndex: number) => {
  const q = testQuestions.value[questionIndex]
  if (!q.practicalAnswer?.trim() || q.practicalGrading || q.practicalGraded) return
  q.practicalGrading = true
  try {
    const result = await api.submitPracticalFeedback({
      session_id: sessionId.value || 'demo',
      topic: currentTopic.value || q.topic || '基础知识',
      question: q.question,
      user_answer: q.practicalAnswer,
      correct_answer: q.correct_answer || '',
      explanation: q.explanation || '',
    })
    q.practicalResult = result
    q.practicalGraded = true
    q.answered = true
  } catch (err) {
    console.error('实操题批改失败:', err)
    q.practicalResult = {
      score: 0,
      is_correct: false,
      feedback: '批改服务暂时不可用，请稍后重试。',
      key_points: [],
      reference_answer: q.correct_answer || '',
    }
    q.practicalGraded = true
    q.answered = true
  } finally {
    q.practicalGrading = false
  }
}

onMounted(async () => {
  if (!sessionId.value) {
    loading.value = false
    return
  }

  try {
    const data = await api.getResources(sessionId.value)
    resources.value = data

    // 从第一个资源的 topic 获取当前主题
    if (data.length > 0 && data[0].topic) {
      currentTopic.value = data[0].topic
    }

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
          practicalAnswer: '',
          practicalGrading: false,
          practicalGraded: false,
          practicalResult: null,
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
.practical-input-box {
  background: var(--bg-muted, #f7f8fa);
  border-radius: var(--radius-sm);
  padding: 16px;
}
.practical-textarea {
  width: 100%;
  min-height: 120px;
  padding: 12px 14px;
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
  font-size: 24px;
  font-weight: 700;
  font-family: var(--mono);
  letter-spacing: -.02em;
}
.practical-score.pass { color: var(--ok); }
.practical-score.fail { color: var(--err); }
.feedback-box {
  padding: 16px 18px;
  border-radius: var(--radius-sm);
  font-size: 13.5px;
  line-height: 1.7;
}
.feedback-box.ok { background: var(--ok-soft); border: 1px solid #A7F3D0; }
.feedback-box.err { background: var(--err-soft); border: 1px solid #FECACA; }
.bar {
  height: 6px;
  background: var(--line);
  border-radius: 3px;
  overflow: hidden;
}
.bar__fill {
  height: 100%;
  border-radius: 3px;
  transition: width .4s ease;
}
.bar__fill.ok { background: var(--ok); }
.bar__fill.err { background: var(--err); }
.reference-answer-block {
  background: var(--bg, #fff);
  padding: 12px 14px;
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
