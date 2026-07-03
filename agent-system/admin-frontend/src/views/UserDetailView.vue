<script setup lang="ts">
import { usersApi } from '@/api/users'
import { formatDate, APPROVAL_STATUS_MAP, LEVEL_MAP, LEARNING_STYLE_MAP } from '@/utils/format'
import { formatPercent } from '@/utils/format'
import { useRoute, useRouter } from 'vue-router'
import { ArrowBackOutline } from '@vicons/ionicons5'

const route = useRoute()
const router = useRouter()
const message = useMessage()

const learnerId = computed(() => Number(route.params.id))
const loading = ref(false)
const detail = ref<any>({})
const learningDetail = ref<any>({})
const activeTab = ref('overview')

// 知识点等级颜色映射
function levelColor(level: string): string {
  const map: Record<string, string> = {
    beginner: '#D97706',
    intermediate: '#4F46E5',
    advanced: '#059669',
    expert: '#DC2626',
  }
  return map[level] || '#9CA3AF'
}

// 根据节点实际字段推导展示状态
function nodeDisplayStatus(node: any): string {
  if (node.advanced_test_passed || node.completed) return 'completed'
  if (node.basic_test_passed || node.has_resources) return 'in_progress'
  return 'pending'
}

// 节点状态标签
function stageStatusTag(node: any) {
  const realStatus = nodeDisplayStatus(node)
  const map: Record<string, { label: string; type: 'default' | 'info' | 'success' }> = {
    completed: { label: '已完成', type: 'success' },
    in_progress: { label: '进行中', type: 'info' },
    pending: { label: '未开始', type: 'default' },
  }
  return map[realStatus] || { label: realStatus, type: 'default' as const }
}

async function loadData() {
  loading.value = true
  try {
    const [d, ld] = await Promise.all([
      usersApi.getDetail(learnerId.value),
      usersApi.getLearningDetail(learnerId.value),
    ])
    detail.value = d
    learningDetail.value = ld
  } catch (err: any) {
    message.error(err.message || '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => loadData())
</script>

<template>
  <div>
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 24px">
      <NButton text @click="router.push({ name: 'Users' })">
        <template #icon><NIcon><ArrowBackOutline /></NIcon></template>
        返回列表
      </NButton>
      <h1 style="font-size: 22px; font-weight: 600; letter-spacing: -.03em; color: #111827">
        {{ detail.username || '学员详情' }}
      </h1>
    </div>

    <NSpin :show="loading">
      <!-- 基本信息卡片 -->
      <NCard title="基本信息" :bordered="true" size="small" style="margin-bottom: 16px">
        <template #header-extra>
          <NTag :type="detail.machine_approval_status === 'approved' ? 'success' : detail.machine_approval_status === 'pending' ? 'warning' : 'default'" size="small">
            {{ APPROVAL_STATUS_MAP[detail.machine_approval_status]?.label || '未申请' }}
          </NTag>
        </template>
        <NGrid :cols="4" :x-gap="16" responsive="screen">
          <NGi :span="1">
            <div class="info-item">
              <span class="info-label">用户名</span>
              <span class="info-value">{{ detail.username }}</span>
            </div>
          </NGi>
          <NGi :span="1">
            <div class="info-item">
              <span class="info-label">邮箱</span>
              <span class="info-value">{{ detail.email || '-' }}</span>
            </div>
          </NGi>
          <NGi :span="1">
            <div class="info-item">
              <span class="info-label">学历</span>
              <span class="info-value">{{ detail.education_background || '-' }}</span>
            </div>
          </NGi>
          <NGi :span="1">
            <div class="info-item">
              <span class="info-label">专业</span>
              <span class="info-value">{{ detail.major || '-' }}</span>
            </div>
          </NGi>
          <NGi :span="1">
            <div class="info-item">
              <span class="info-label">工作年限</span>
              <span class="info-value">{{ detail.work_experience_years ?? '-' }} 年</span>
            </div>
          </NGi>
          <NGi :span="1">
            <div class="info-item">
              <span class="info-label">学习风格</span>
              <span class="info-value">{{ LEARNING_STYLE_MAP[detail.learning_style] || detail.learning_style || '-' }}</span>
            </div>
          </NGi>
          <NGi :span="1">
            <div class="info-item">
              <span class="info-label">整体水平</span>
              <NTag size="small" :bordered="false">{{ LEVEL_MAP[detail.overall_level] || detail.overall_level || '-' }}</NTag>
            </div>
          </NGi>
          <NGi :span="1">
            <div class="info-item">
              <span class="info-label">推荐难度</span>
              <span class="info-value">{{ LEVEL_MAP[detail.recommended_difficulty] || detail.recommended_difficulty || '-' }}</span>
            </div>
          </NGi>
        </NGrid>
      </NCard>

      <!-- Tab: 学习路径 / 知识掌握 / 答题记录 / 审批历史 -->
      <NTabs v-model:value="activeTab" type="line" animated>
        <NTabPane name="overview" tab="学习路径">
          <NCard :bordered="true" size="small">
            <template v-if="detail.learning_path?.length > 0">
              <div style="margin-bottom: 12px; font-size: 13px; color: #4B5563">
                学习进度：{{ formatPercent(detail.learning_progress) }}
                （{{ detail.learning_path.filter((n: any) => nodeDisplayStatus(n) === 'completed').length }} / {{ detail.learning_path.length }}）
              </div>
              <div
                v-for="(node, idx) in detail.learning_path"
                :key="idx"
                style="display: flex; align-items: center; gap: 16px; padding: 14px 16px; border: 1px solid #ECECEF; border-radius: 6px; margin-bottom: 8px"
              >
                <div style="width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; color: #fff; flex-shrink: 0"
                  :style="{ background: nodeDisplayStatus(node) === 'completed' ? '#059669' : nodeDisplayStatus(node) === 'in_progress' ? '#4F46E5' : '#D1D5DB' }"
                >
                  {{ Number(idx) + 1 }}
                </div>
                <div style="flex: 1; min-width: 0">
                  <div style="font-size: 14px; font-weight: 500; color: #111827">{{ node.title }}</div>
                  <div v-if="node.topics?.length" style="font-size: 12px; color: #9CA3AF; margin-top: 4px">
                    {{ node.topics.join(' · ') }}
                  </div>
                </div>
                <div style="text-align: right; flex-shrink: 0">
                  <NTag :type="stageStatusTag(node).type" size="small" :bordered="false">
                    {{ stageStatusTag(node).label }}
                  </NTag>
                  <div style="font-size: 12px; color: #9CA3AF; margin-top: 4px">难度 {{ LEVEL_MAP[node.difficulty] || node.difficulty }}</div>
                </div>
              </div>
            </template>
            <NEmpty v-else description="暂无学习路径数据" />
          </NCard>
        </NTabPane>

        <NTabPane name="knowledge" tab="知识掌握">
          <NCard :bordered="true" size="small">
            <template v-if="detail.knowledge_points?.length > 0">
              <div
                v-for="kp in detail.knowledge_points"
                :key="kp.name"
                style="display: flex; align-items: center; gap: 16px; padding: 12px 0; border-bottom: 1px solid #ECECEF"
              >
                <span style="width: 130px; font-size: 13px; font-weight: 500; color: #111827; flex-shrink: 0">{{ kp.name }}</span>
                <div style="flex: 1; height: 4px; border-radius: 99px; background: #F5F5F5; overflow: hidden">
                  <div
                    style="height: 100%; border-radius: 99px"
                    :style="{ width: (kp.score || 0) + '%', background: levelColor(kp.level) }"
                  />
                </div>
                <span style="width: 40px; text-align: right; font-size: 13px; font-family: monospace; color: #4B5563; flex-shrink: 0">
                  {{ kp.score?.toFixed?.(0) || kp.score || 0 }}
                </span>
                <NTag size="small" :bordered="false" :style="{ color: levelColor(kp.level) }">
                  {{ LEVEL_MAP[kp.level] || kp.level }}
                </NTag>
              </div>
            </template>
            <NEmpty v-else description="暂无知识点数据" />
          </NCard>

          <!-- 盲区 -->
          <NCard v-if="detail.blind_spots?.length > 0" title="知识盲区" :bordered="true" size="small" style="margin-top: 16px">
            <NSpace>
              <NTag v-for="bs in detail.blind_spots" :key="bs.name || bs" type="error" :bordered="false" size="small">
                {{ bs.name || bs }}
              </NTag>
            </NSpace>
          </NCard>
        </NTabPane>

        <NTabPane name="kg-progress" tab="知识图谱进度">
          <NCard :bordered="true" size="small">
            <template v-if="detail.kg_progress">
              <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 16px">
                <div style="font-size: 28px; font-weight: 600; color: #111827">
                  {{ detail.kg_progress.percentage ?? 0 }}%
                </div>
                <NProgress
                  :percentage="detail.kg_progress.percentage ?? 0"
                  :indicator-placement="'inside'"
                  :height="20"
                  :border-radius="4"
                  :rail-color="'#ECECEF'"
                  :color="(detail.kg_progress.percentage ?? 0) >= 80 ? '#10B981' : (detail.kg_progress.percentage ?? 0) >= 40 ? '#F59E0B' : '#6366F1'"
                  style="flex: 1"
                />
              </div>
              <div style="display: flex; gap: 24px; margin-bottom: 16px">
                <div>
                  <span style="font-size: 12px; color: #9CA3AF">已完成知识点</span>
                  <div style="font-size: 18px; font-weight: 600; color: #059669">{{ (detail.kg_progress.completed_nodes || []).length }}</div>
                </div>
                <div>
                  <span style="font-size: 12px; color: #9CA3AF">知识节点总数</span>
                  <div style="font-size: 18px; font-weight: 600; color: #111827">{{ detail.kg_progress.total || 0 }}</div>
                </div>
              </div>
            </template>
            <NEmpty v-else description="暂无知识图谱进度数据（学员完成答题考核后自动更新）" />
          </NCard>
        </NTabPane>

        <NTabPane name="feedback" tab="答题记录">
          <NCard :bordered="true" size="small">
            <template v-if="learningDetail.recent_feedbacks?.length > 0">
              <div
                v-for="fb in learningDetail.recent_feedbacks"
                :key="fb.id"
                style="padding: 14px 0; border-bottom: 1px solid #ECECEF"
              >
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px">
                  <NTag :type="fb.is_correct ? 'success' : 'error'" size="small" :bordered="false">
                    {{ fb.is_correct ? '正确' : '错误' }}
                  </NTag>
                  <NTag size="small" :bordered="false">{{ LEVEL_MAP[fb.test_level] || fb.test_level }}</NTag>
                  <span style="font-size: 12px; color: #9CA3AF">{{ formatDate(fb.created_at) }}</span>
                </div>
                <div style="font-size: 13px; color: #4B5563; line-height: 1.6">
                  {{ fb.question }}
                </div>
              </div>
            </template>
            <NEmpty v-else description="暂无答题记录" />
          </NCard>
        </NTabPane>

        <NTabPane name="approval" tab="审批历史">
          <NCard :bordered="true" size="small">
            <template v-if="learningDetail.approval_logs?.length > 0">
              <NTimeline>
                <NTimelineItem
                  v-for="log in learningDetail.approval_logs"
                  :key="log.id"
                  :type="log.action === 'approve' ? 'success' : log.action === 'reject' ? 'error' : 'info'"
                  :title="log.action === 'approve' ? '批准' : log.action === 'reject' ? '拒绝' : '提交申请'"
                >
                  <div style="font-size: 13px; color: #4B5563">
                    <span v-if="log.operator_name">操作人：{{ log.operator_name }}</span>
                    <span v-if="log.reason" style="margin-left: 12px">理由：{{ log.reason }}</span>
                  </div>
                  <div style="font-size: 12px; color: #9CA3AF; margin-top: 4px">{{ formatDate(log.created_at) }}</div>
                </NTimelineItem>
              </NTimeline>
            </template>
            <NEmpty v-else description="暂无审批记录" />
          </NCard>
        </NTabPane>
      </NTabs>
    </NSpin>
  </div>
</template>

<style scoped>
.info-item {
  padding: 8px 0;
}
.info-label {
  display: block;
  font-size: 12px;
  color: #9CA3AF;
  margin-bottom: 4px;
}
.info-value {
  font-size: 14px;
  color: #111827;
  font-weight: 500;
}
</style>
