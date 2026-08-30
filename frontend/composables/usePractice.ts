/**
 * 答题练习页面逻辑（从 pages/practice.vue 抽出）。
 *
 * 页面文件只保留模板与样式；练习等级解析、试题加载与作答状态机、
 * 苏格拉底追问、简答题批改、进度恢复与结果提交均在此维护。
 */
export function usePractice() {
  const router = useRouter()
  const route = useRoute()
  const api = useApi()
  const { sessionId } = useSession()
  const { nodes, fetchLearningPath } = useLearningPath()
  const { isLoggedIn, isLoading: authLoading } = useAuth()

  const PASS_THRESHOLD = 70
  type TestLevel = 'node' | 'comprehensive'

  const normalizeTestLevel = (value: unknown): TestLevel | '' => {
    const raw = Array.isArray(value) ? value[0] : value
    if (raw === 'basic' || raw === 'advanced') return 'node'
    return raw === 'node' || raw === 'comprehensive' ? raw : ''
  }

  // === 练习等级 ===
  const testLevel = ref<TestLevel | ''>(normalizeTestLevel(route.query.level))
  const levelLabels: Record<TestLevel, string> = {
    node: '节点练习',
    comprehensive: '综合练习',
  }
  const testLabel = computed(() => testLevel.value ? levelLabels[testLevel.value] : '答题练习')
  const testDescription = computed(() =>
    testLevel.value === 'comprehensive'
      ? '一个完整生产场景下设置 2 道选择题和 3 道简答题，覆盖 5 个学习节点的关键能力。'
      : '可在 5 个学习节点间自由切换节点练习。每个节点包含 4 道选择题、3 道判断题、2 道简答题，结果用于报告分析和知识图谱掌握度。'
  )
  const levelBadgeClass = computed(() =>
    testLevel.value === 'comprehensive' ? 'badge--err' : 'badge--accent'
  )

  // === 状态 ===
  const loading = ref(true)
  const loadError = ref('')
  const questions = ref<any[]>([])
  const comprehensiveScenario = ref<any>(null)
  const selectedStage = ref(Number(route.query.stage) || 1)
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

  // 简答题
  const practicalAnswer = ref('')
  const practicalGrading = ref(false)
  const practicalGraded = ref(false)
  const practicalResult = ref<any>(null)

  const resultSaving = ref(false)
  const resultSaved = ref(false)
  const resultSaveError = ref('')

  // 计算
  const currentQuestion = computed(() => questions.value[currentIndex.value] || {})
  const markdownCell = (value: unknown) => String(value ?? '').replace(/\|/g, '\\|').replace(/\r?\n/g, '<br>')
  const markdownList = (items: unknown) => Array.isArray(items) && items.length
    ? items.map(item => `- ${markdownCell(item)}`).join('\n')
    : '- 暂无'
  const markdownTable = (headers: string[], rows: string[][]) => {
    if (!rows.length) return '暂无'
    return [
      `| ${headers.join(' | ')} |`,
      `| ${headers.map(() => '---').join(' | ')} |`,
      ...rows.map(row => `| ${row.map(markdownCell).join(' | ')} |`),
    ].join('\n')
  }
  const scenarioMarkdown = computed(() => {
    const s = comprehensiveScenario.value
    if (!s) return ''
    const facts = [
      ['岗位身份', s.role],
      ['生产任务', s.production_task],
      ['机床/系统', [s.machine, s.controller].filter(Boolean).join(' / ')],
      ['材料/毛坯', [s.material, s.blank_size].filter(Boolean).join(' / ')],
      ['批量', s.batch_size],
      ['装夹/坐标系', [s.clamping, s.work_coordinate].filter(Boolean).join(' / ')],
    ].filter(row => row[1]) as string[][]
    const requirements = Array.isArray(s.drawing_requirements)
      ? s.drawing_requirements.map((item: any) => [item.item, item.requirement])
      : []
    const results = Array.isArray(s.first_article_results)
      ? s.first_article_results.map((item: any) => [item.item, item.requirement, item.measured])
      : []
    return [
      '## 生产任务资料',
      markdownTable(['项目', '内容'], facts),
      '## 图纸与质量要求',
      markdownTable(['检测项目', '要求'], requirements),
      '## 刀具信息',
      markdownList(s.tools),
      '## 关键程序片段',
      `\`\`\`nc\n${String(s.program_excerpt || '暂无').trim()}\n\`\`\``,
      '## 开工前现场状态',
      markdownList(s.site_conditions),
      '## 首件检测数据',
      markdownTable(['检测项目', '要求', '实测值'], results),
      '## 加工中异常现象',
      markdownList(s.runtime_symptoms),
    ].join('\n\n')
  })
  const questionWithScenario = computed(() => {
    if (testLevel.value !== 'comprehensive' || !scenarioMarkdown.value) return currentQuestion.value.question
    return `${scenarioMarkdown.value}\n\n## 当前问题\n${currentQuestion.value.question}`
  })
  const correctCount = computed(() => questions.value.filter(q => q.finalCorrect === true).length)
  const wrongCount = computed(() => questions.value.filter(q => q.answered && q.finalCorrect === false).length)
  const accuracy = computed(() => questions.value.length ? Math.round(correctCount.value / questions.value.length * 100) : 0)
  const passed = computed(() => accuracy.value >= PASS_THRESHOLD)
  const resultEmoji = computed(() => passed.value ? '' : '')
  const resultTitle = computed(() => {
    if (testLevel.value === 'comprehensive') return passed.value ? '综合练习已达标' : '综合练习已完成'
    if (passed.value) return `${testLabel.value}已达标`
    return `${testLabel.value}已完成`
  })
  const resultMessage = computed(() => {
    if (testLevel.value === 'comprehensive') return passed.value ? '你已经能综合处理完整业务场景。' : '建议根据错题复盘装夹、检测、程序识读和异常处理环节。'
    if (passed.value) return '本轮练习表现达标，可继续学习资源或进入综合练习。'
    return '建议回到学习资源复习薄弱内容后再练一次。'
  })

  // === 辅助 ===
  const stripOptionPrefix = (o: string) => o.replace(/^[A-Da-d][.\s、]+/, '')
  const resolveCorrectIndex = (q: any): number => {
    const answer = q.correct_answer || ''
    if (/^[A-D]$/.test(answer)) return answer.charCodeAt(0) - 65
    const stripped = answer.replace(/^[A-Da-d][.\s、]+/, '')
    return q.options?.findIndex((opt: string) => stripOptionPrefix(opt) === stripped || opt === answer) ?? 0
  }

  const resolveSelectedStage = () => {
    let stage = Number(route.query.stage) || selectedStage.value || 1
    if (nodes.value.length > 0 && !nodes.value.some((n: any) => Number(n.stage) === stage)) {
      stage = Number(nodes.value[0].stage) || 1
    }
    selectedStage.value = stage
    return stage
  }

  // === 初始化 ===
  const initQuestions = async () => {
    if (!sessionId.value) {
      loading.value = false; loadError.value = '缺少会话信息，请先完成学习者画像和 Agent 协同生成'; return
    }
    loading.value = true; loadError.value = ''
    questions.value = []
    resultSaved.value = false
    resultSaveError.value = ''

    try {
      await fetchLearningPath()

      let resolvedLevel = normalizeTestLevel(route.query.level) || 'node'
      if (resolvedLevel === 'comprehensive') {
        testLevel.value = resolvedLevel
        const result = await api.getTieredQuestions(sessionId.value, resolvedLevel)
        if (!result?.questions?.length) {
          loadError.value = (result as any)?.error || '综合练习暂不可用'
          loading.value = false
          return
        }
        applyQuestions(result)
        return
      }

      comprehensiveScenario.value = null
      const stage = resolveSelectedStage()
      const node = nodes.value.find((n: any) => Number(n.stage) === stage)
      if (!node) {
        loadError.value = '暂未找到学习节点，请先完成 Agent 协同生成'
        loading.value = false
        return
      }

      testLevel.value = resolvedLevel

      const result = await api.getTieredQuestions(sessionId.value, resolvedLevel, stage)
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
    comprehensiveScenario.value = testLevel.value === 'comprehensive' ? (result.scenario || null) : null
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
      api.getPracticeState(
        sessionId.value,
        testLevel.value || undefined,
        testLevel.value === 'comprehensive' ? null : selectedStage.value,
      ).then(saved => {
        if (saved?.questions?.length) {
          let matched = 0
          questions.value = questions.value.map((q: any) => {
            const match = saved.questions.find((s: any) => s.question === q.question)
            if (match) matched += 1
            return match ? { ...q, selectedIndex: match.selectedIndex ?? -1, answered: match.answered ?? false, finalCorrect: match.finalCorrect ?? null, practicalAnswer: match.practicalAnswer || '', practicalGraded: match.practicalGraded ?? false, practicalResult: match.practicalResult || null } : q
          })
          if (matched > 0 && typeof saved.current_index === 'number') currentIndex.value = saved.current_index
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
        question: questionWithScenario.value,
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
        question: questionWithScenario.value, user_answer: practicalAnswer.value,
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
  const nextQuestion = async () => {
    if (currentIndex.value < questions.value.length - 1) { currentIndex.value++; resetState(); saveProgress() }
    else {
      saveProgress()
      await submitPracticeResult()
      testCompleted.value = true
    }
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
      level: testLevel.value || null,
      stage: testLevel.value === 'comprehensive' ? null : selectedStage.value,
      questions: questions.value.map((q: any) => ({ question: q.question, selectedIndex: q.selectedIndex, answered: q.answered, finalCorrect: q.finalCorrect, practicalAnswer: q.practicalAnswer, practicalGraded: q.practicalGraded, practicalResult: q.practicalResult })),
    }).catch(() => {})
  }

  const submitPracticeResult = async () => {
    if (!sessionId.value || !testLevel.value || resultSaved.value || resultSaving.value) return
    resultSaving.value = true
    resultSaveError.value = ''
    try {
      await api.savePracticeResult(sessionId.value, {
        level: testLevel.value,
        stage: testLevel.value === 'comprehensive' ? null : selectedStage.value,
        score: accuracy.value,
        correct_count: correctCount.value,
        wrong_count: wrongCount.value,
        question_count: questions.value.length,
        questions: questions.value.map((q: any) => ({
          topic: q.topic || '',
          question: q.question,
          question_type: q.question_type,
          is_correct: q.finalCorrect === true,
          user_answer: q.question_type === 'practical'
            ? q.practicalAnswer
            : q.selectedIndex >= 0 ? String.fromCharCode(65 + q.selectedIndex) : '',
          correct_answer: q.correctAnswer,
        })),
      })
      resultSaved.value = true

      // 节点练习完成后自动标记当前节点为已完成，推进到下一节点
      if (testLevel.value === 'node') {
        try {
          await api.completeCurrentNode(sessionId.value)
        } catch {
          // 节点推进失败不阻塞结果展示
        }
      }
    } catch (err) {
      console.warn('保存练习结果失败:', err)
      resultSaveError.value = '练习结果保存失败，报告可能暂时无法显示本次成绩'
    } finally {
      resultSaving.value = false
    }
  }

  // === 结果页操作 ===
  const goResources = () => router.push({ path: '/resources', query: { stage: String(selectedStage.value || 1) } })
  const goReport = () => router.push('/report')

  const hasNextStage = computed(() => {
    const idx = nodes.value.findIndex((n: any) => Number(n.stage) === selectedStage.value)
    return idx >= 0 && idx < nodes.value.length - 1
  })

  const goNextStage = () => {
    const idx = nodes.value.findIndex((n: any) => Number(n.stage) === selectedStage.value)
    if (idx >= 0 && idx < nodes.value.length - 1) {
      switchStage(Number(nodes.value[idx + 1].stage))
    }
  }

  const goComprehensive = () => switchLevel('comprehensive')

  const switchLevel = (level: TestLevel) => {
    if (level === testLevel.value) return
    const query = level === 'comprehensive'
      ? { level }
      : { stage: String(selectedStage.value || 1), level }
    router.push({ path: '/practice', query })
  }

  const switchStage = (stage: number) => {
    if (!stage || (stage === selectedStage.value && testLevel.value !== 'comprehensive')) return
    router.push({
      path: '/practice',
      query: { stage: String(stage), level: testLevel.value && testLevel.value !== 'comprehensive' ? testLevel.value : 'node' },
    })
  }

  const retryTest = () => {
    questions.value.forEach(q => { q.selectedIndex = -1; q.answered = false; q.finalCorrect = null; q.practicalAnswer = ''; q.practicalGraded = false; q.practicalResult = null })
    currentIndex.value = 0; testCompleted.value = false; resultSaved.value = false; resetState(); saveProgress()
  }

  // === 初始化 ===
  onMounted(() => {
    if (isLoggedIn.value && sessionId.value) initQuestions()
    else if (!isLoggedIn.value) { loading.value = false; loadError.value = '请先登录' }
    else { loading.value = false; loadError.value = '请先完成学情诊断' }
  })

  // F5 刷新时布局会异步恢复登录态和学习会话；恢复完成后自动加载，无需再点“重新加载”。
  watch([authLoading, isLoggedIn, sessionId], ([isAuthLoading, loggedIn, sid]) => {
    if (!isAuthLoading && loggedIn && sid && !loading.value && questions.value.length === 0) {
      initQuestions()
    }
  })

  watch(() => [route.query.level, route.query.stage], ([newLevel, newStage], [oldLevel, oldStage]) => {
    if (newLevel !== oldLevel || newStage !== oldStage) {
      testCompleted.value = false
      loading.value = true
      loadError.value = ''
      questions.value = []
      currentIndex.value = 0
      initQuestions()
    }
  })

  return {
    // 等级与描述
    testLevel,
    testLabel,
    testDescription,
    levelBadgeClass,
    PASS_THRESHOLD,
    // 加载状态
    loading,
    loadError,
    initQuestions,
    // 节点选择
    nodes,
    selectedStage,
    switchStage,
    switchLevel,
    // 答题状态
    questions,
    currentIndex,
    currentQuestion,
    answered,
    showFeedback,
    isCorrect,
    optionClass,
    selectOption,
    stripOptionPrefix,
    // 苏格拉底追问
    socraticHistory,
    socraticLoading,
    revealAnswer,
    // 简答题
    practicalAnswer,
    practicalGrading,
    practicalGraded,
    practicalResult,
    submitPractical,
    // 场景
    comprehensiveScenario,
    scenarioMarkdown,
    // 统计与结果
    correctCount,
    wrongCount,
    accuracy,
    passed,
    resultEmoji,
    resultTitle,
    resultMessage,
    resultSaveError,
    testCompleted,
    hasNextStage,
    // 翻页与操作
    prevQuestion,
    nextQuestion,
    goResources,
    goReport,
    goNextStage,
    goComprehensive,
    retryTest,
  }
}
