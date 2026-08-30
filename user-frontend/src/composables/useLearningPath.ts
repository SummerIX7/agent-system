/**
 * 学习路径状态管理（模块级单例状态）
 * 管理节点状态、当前节点、考核状态等，供 report/resources/practice 页面共享
 */
import { computed, ref } from 'vue'
import { useApi } from './useApi'
import { useSession } from './useSession'

// 模块级单例
const nodes = ref<any[]>([])
const currentStage = ref(1)
const allCompleted = ref(false)

export function useLearningPath() {
  const currentNode = computed(() => nodes.value.find(n => n.stage === currentStage.value))

  const api = useApi()
  const { sessionId } = useSession()

  // 获取完整学习路径
  const fetchLearningPath = async () => {
    if (!sessionId.value) return
    try {
      const data = await api.getLearningPath(sessionId.value)
      nodes.value = data.nodes || []
      currentStage.value = data.current_stage || 1
      allCompleted.value = data.all_completed || false
    } catch (err) {
      console.warn('获取学习路径失败:', err)
    }
  }

  // 推进到下一节点
  const advanceNode = async (basicScore: number, advancedScore: number, testFeedback: any[] = []) => {
    if (!sessionId.value) return null
    try {
      const result = await api.advanceNode(sessionId.value, {
        basic_score: basicScore,
        advanced_score: advancedScore,
        test_feedback: testFeedback,
      })
      // 更新本地状态
      if (result.new_stage) {
        currentStage.value = result.new_stage
      }
      allCompleted.value = result.all_completed || false
      // 重新获取最新路径数据
      await fetchLearningPath()
      return result
    } catch (err) {
      console.warn('节点推进失败:', err)
      return null
    }
  }

  const completeCurrentNode = async () => {
    if (!sessionId.value) return null
    try {
      const result = await api.completeCurrentNode(sessionId.value)
      if (result.new_stage) currentStage.value = result.new_stage
      allCompleted.value = result.all_completed || false
      await fetchLearningPath()
      return result
    } catch (err) {
      console.warn('完成当前节点失败:', err)
      return null
    }
  }

  // 当前节点的完成状态
  const currentNodeStatus = computed(() => {
    const node = currentNode.value
    if (!node) return { label: '就绪', color: 'var(--text-3)', action: 'start' }
    if (node.completed || node.advanced_test_passed) return { label: '已完成', color: 'var(--ok)', action: 'done' }
    if (node.has_resources) return { label: '待学习', color: 'var(--warn)', action: 'learn' }
    return { label: '待学习', color: 'var(--text-3)', action: 'learn' }
  })

  return {
    nodes,
    currentStage,
    allCompleted,
    currentNode,
    currentNodeStatus,
    fetchLearningPath,
    advanceNode,
    completeCurrentNode,
  }
}
