<script setup lang="ts">
import { approvalApi } from '@/api/approval'
import { usersApi } from '@/api/users'
import type { LearnerItem } from '@/types/admin'
import { formatPercent, LEVEL_MAP } from '@/utils/format'
import { CheckmarkOutline, CloseOutline, CheckmarkCircleOutline } from '@vicons/ionicons5'

const message = useMessage()

const loading = ref(false)
const pendingList = ref<LearnerItem[]>([])
const pendingTotal = ref(0)
const pendingPage = ref(1)

const selectedId = ref<number | null>(null)
const selectedDetail = ref<any>({})
const detailLoading = ref(false)

const showRejectModal = ref(false)
const rejectReason = ref('')

async function loadPendingList() {
  loading.value = true
  try {
    const result = await approvalApi.getPending(pendingPage.value, 20)
    pendingList.value = result.items
    pendingTotal.value = result.total
  } catch (err: any) {
    message.error(err.message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function selectLearner(id: number) {
  selectedId.value = id
  detailLoading.value = true
  try {
    selectedDetail.value = await usersApi.getDetail(id)
  } catch {
    // ignore
  } finally {
    detailLoading.value = false
  }
}

async function handleApprove(learnerId: number) {
  try {
    await approvalApi.approve(learnerId, '达到操作标准，批准使用')
    message.success('审批通过')
    selectedId.value = null
    selectedDetail.value = {}
    await loadPendingList()
  } catch (err: any) {
    message.error(err.message || '操作失败')
  }
}

function openRejectModal(learnerId: number) {
  selectedId.value = learnerId
  rejectReason.value = ''
  showRejectModal.value = true
}

async function handleReject() {
  if (!rejectReason.value.trim()) {
    message.warning('请填写拒绝理由')
    return
  }
  if (!selectedId.value) return

  try {
    await approvalApi.reject(selectedId.value, rejectReason.value)
    message.success('已拒绝申请')
    showRejectModal.value = false
    selectedId.value = null
    selectedDetail.value = {}
    rejectReason.value = ''
    await loadPendingList()
  } catch (err: any) {
    message.error(err.message || '操作失败')
  }
}

onMounted(() => loadPendingList())
</script>

<template>
  <div>
    <div class="page-head">
      <h1 class="page-head-title">审批管理</h1>
      <p class="page-head-desc">处理学员机台使用申请，查看学习数据辅助决策</p>
    </div>

    <NGrid :cols="2" :x-gap="24" responsive="screen">
      <!-- 左侧：待审批列表 -->
      <NGi :span="1">
        <NCard title="待审批列表" :bordered="true" size="small" style="height: calc(100vh - 200px); overflow: auto">
          <template #header-extra>
            <NTag type="warning" size="small" :bordered="false">{{ pendingTotal }} 条待处理</NTag>
          </template>

          <NSpin :show="loading">
            <div v-if="pendingList.length === 0" style="text-align: center; padding: 40px 0; color: #9CA3AF">
              暂无待审批申请
            </div>
            <div
              v-for="item in pendingList"
              :key="item.id"
              style="padding: 14px 12px; border: 1px solid #ECECEF; border-radius: 6px; margin-bottom: 8px; cursor: pointer; transition: all .15s"
              :style="{
                borderColor: selectedId === item.id ? '#4F46E5' : '#ECECEF',
                background: selectedId === item.id ? '#EEF2FF' : '#fff',
              }"
              @click="selectLearner(item.id)"
            >
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px">
                <span style="font-size: 14px; font-weight: 500; color: #111827">{{ item.username }}</span>
                <NTag type="warning" size="small" :bordered="false">待审批</NTag>
              </div>
              <div style="display: flex; align-items: center; gap: 16px; font-size: 12px; color: #9CA3AF">
                <span>{{ LEVEL_MAP[item.overall_level] || item.overall_level || '未知等级' }}</span>
                <span>进度 {{ formatPercent(item.learning_progress) }}</span>
              </div>
            </div>
          </NSpin>
        </NCard>
      </NGi>

      <!-- 右侧：详情面板 -->
      <NGi :span="1">
        <NCard :bordered="true" size="small" style="height: calc(100vh - 200px); overflow: auto">
          <template v-if="!selectedId">
            <div style="text-align: center; padding: 60px 0; color: #9CA3AF">
              <NIcon size="48" color="#D1D5DB"><CheckmarkCircleOutline /></NIcon>
              <p style="margin-top: 12px">选择左侧学员查看学习详情</p>
            </div>
          </template>

          <NSpin v-else :show="detailLoading">
            <template v-if="selectedDetail.username">
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px">
                <div>
                  <div style="font-size: 18px; font-weight: 600; color: #111827">{{ selectedDetail.username }}</div>
                  <div style="font-size: 13px; color: #9CA3AF; margin-top: 4px">
                    {{ selectedDetail.education_background }} · {{ selectedDetail.major }}
                  </div>
                </div>
                <NTag type="warning" size="small" :bordered="false">待审批</NTag>
              </div>

              <!-- 学习进度 -->
              <div style="margin-bottom: 20px">
                <div style="font-size: 13px; color: #4B5563; margin-bottom: 6px">
                  学习进度：{{ formatPercent(selectedDetail.learning_progress) }}
                </div>
                <div style="height: 4px; border-radius: 99px; background: #F5F5F5; overflow: hidden">
                  <div
                    style="height: 100%; background: #4F46E5; border-radius: 99px"
                    :style="{ width: (selectedDetail.learning_progress || 0) * 100 + '%' }"
                  />
                </div>
              </div>

              <!-- 知识点 -->
              <div v-if="selectedDetail.knowledge_points?.length > 0" style="margin-bottom: 20px">
                <div style="font-size: 13px; font-weight: 500; color: #111827; margin-bottom: 8px">知识掌握</div>
                <div v-for="kp in selectedDetail.knowledge_points.slice(0, 8)" :key="kp.name" style="display: flex; align-items: center; gap: 8px; padding: 6px 0; font-size: 13px">
                  <span style="width: 100px; color: #4B5563">{{ kp.name }}</span>
                  <span style="font-family: monospace; color: #111827; font-weight: 500; width: 36px">{{ kp.score?.toFixed?.(0) || kp.score || 0 }}</span>
                </div>
              </div>

              <!-- 盲区 -->
              <div v-if="selectedDetail.blind_spots?.length > 0" style="margin-bottom: 20px">
                <div style="font-size: 13px; font-weight: 500; color: #111827; margin-bottom: 8px">知识盲区</div>
                <NSpace>
                  <NTag v-for="bs in selectedDetail.blind_spots" :key="bs.name || bs" type="error" size="small" :bordered="false">
                    {{ bs.name || bs }}
                  </NTag>
                </NSpace>
              </div>

              <!-- 操作按钮 -->
              <NDivider />
              <div style="display: flex; gap: 12px">
                <NButton type="success" @click="handleApprove(selectedId!)" style="flex: 1">
                  <template #icon><NIcon><CheckmarkOutline /></NIcon></template>
                  批准使用
                </NButton>
                <NButton type="error" @click="openRejectModal(selectedId!)" style="flex: 1">
                  <template #icon><NIcon><CloseOutline /></NIcon></template>
                  拒绝申请
                </NButton>
              </div>
            </template>
          </NSpin>
        </NCard>
      </NGi>
    </NGrid>

    <!-- 拒绝理由弹窗 -->
    <NModal v-model:show="showRejectModal" title="拒绝申请" preset="dialog" positive-text="确认拒绝" negative-text="取消" @positive-click="handleReject">
      <NFormItem label="拒绝理由（必填）" required>
        <NInput
          v-model:value="rejectReason"
          type="textarea"
          placeholder="例如：G代码编程还需提升，建议完成进阶课程后再申请"
          :rows="3"
        />
      </NFormItem>
    </NModal>
  </div>
</template>

<style scoped>
.page-head { margin-bottom: 24px; }
.page-head-title {
  font-size: 22px; font-weight: 600; letter-spacing: -.03em;
  color: #111827; margin-bottom: 8px;
}
.page-head-desc { font-size: 14px; color: #9CA3AF; }
</style>
