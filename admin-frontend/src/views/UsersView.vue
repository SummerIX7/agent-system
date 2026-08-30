<script setup lang="ts">
import { usersApi } from '@/api/users'
import type { LearnerItem } from '@/types/admin'
import { formatDate, APPROVAL_STATUS_MAP, LEVEL_MAP } from '@/utils/format'
import { formatPercent } from '@/utils/format'
import type { DataTableColumns, DataTableSortState } from 'naive-ui'
import { useRouter } from 'vue-router'
import { SearchOutline } from '@vicons/ionicons5'

const router = useRouter()
const message = useMessage()

const loading = ref(false)
const data = ref<LearnerItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const approvalStatus = ref<string | null>(null)
const level = ref<string | null>(null)

const columns: DataTableColumns<LearnerItem> = [
  { title: '用户名', key: 'username', width: 120, ellipsis: { tooltip: true } },
  { title: '学历', key: 'education_background', width: 90 },
  { title: '专业', key: 'major', width: 120, ellipsis: { tooltip: true } },
  {
    title: '学习进度',
    key: 'learning_progress',
    width: 140,
    sorter: true,
    render(row) {
      return h('div', { style: 'display: flex; align-items: center; gap: 8px' }, [
        h('div', {
          style: `flex:1; height:4px; border-radius:99px; background:#F5F5F5; overflow:hidden`,
        }, [
          h('div', {
            style: `height:100%; width:${row.learning_progress * 100}%; background:#4F46E5; border-radius:99px`,
          }),
        ]),
        h('span', { style: 'font-size:13px; color:#4B5563' }, formatPercent(row.learning_progress)),
      ])
    },
  },
  {
    title: '等级',
    key: 'overall_level',
    width: 90,
    sorter: true,
    render(row) {
      if (!row.profile_created) {
        return h('span', { style: 'font-size:12px; color:#9CA3AF' }, '未建档')
      }
      return h('span', { style: 'font-size:13px; color:#4B5563' }, LEVEL_MAP[row.overall_level] || row.overall_level || '-')
    },
  },
  {
    title: '审批状态',
    key: 'machine_approval_status',
    width: 100,
    render(row) {
      const status = APPROVAL_STATUS_MAP[row.machine_approval_status] || APPROVAL_STATUS_MAP.none
      return h('span', {
        style: `font-size:12px; padding:2px 8px; border-radius:20px; font-weight:500;
          ${status.type === 'warning' ? 'background:#FFFBEB;color:#D97706' : ''}
          ${status.type === 'success' ? 'background:#ECFDF5;color:#059669' : ''}
          ${status.type === 'error' ? 'background:#FEF2F2;color:#DC2626' : ''}
          ${status.type === 'default' ? 'background:#F5F5F5;color:#9CA3AF' : ''}
        `,
      }, status.label)
    },
  },
  {
    title: '更新时间',
    key: 'updated_at',
    width: 160,
    sorter: true,
    render(row) {
      return row.updated_at ? formatDate(row.updated_at) : '-'
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 100,
    fixed: 'right',
    render(row) {
      if (!row.profile_created || !row.id) {
        return h('span', { style: 'color:#9CA3AF; font-size:13px' }, '未建档')
      }
      return h('a', {
        style: 'color:#4F46E5; cursor:pointer; font-size:13px',
        onClick: () => router.push({ name: 'UserDetail', params: { id: row.id } }),
      }, '查看详情')
    },
  },
]

const approvalStatusOptions: any[] = [
  { label: '全部', value: null },
  { label: '未申请', value: 'none' },
  { label: '审批中', value: 'pending' },
  { label: '已批准', value: 'approved' },
  { label: '未通过', value: 'rejected' },
]

const levelOptions: any[] = [
  { label: '全部', value: null },
  { label: '初级', value: 'beginner' },
  { label: '中级', value: 'intermediate' },
  { label: '高级', value: 'advanced' },
  { label: '专家', value: 'expert' },
]

async function loadData() {
  loading.value = true
  try {
    const result = await usersApi.getList({
      page: page.value,
      page_size: pageSize.value,
      keyword: keyword.value || undefined,
      approval_status: approvalStatus.value || undefined,
      level: level.value || undefined,
    })
    data.value = result.items
    total.value = result.total
  } catch (err: any) {
    message.error(err.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadData()
}

function handlePageChange(p: number) {
  page.value = p
  loadData()
}

function handleSorterChange(_sortState: DataTableSortState | null) {
  loadData()
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <div>
    <div class="page-head">
      <h1 class="page-head-title">学员管理</h1>
      <p class="page-head-desc">管理所有学员，查看学习进度与审批状态</p>
    </div>

    <!-- 搜索与筛选 -->
    <NCard :bordered="true" size="small" style="margin-bottom: 16px">
      <NSpace align="center" :wrap="true">
        <NInput
          v-model:value="keyword"
          placeholder="搜索用户名/邮箱"
          clearable
          style="width: 220px"
          @keyup.enter="handleSearch"
        >
          <template #prefix>
            <NIcon><SearchOutline /></NIcon>
          </template>
        </NInput>
        <NSelect
          v-model:value="approvalStatus"
          :options="approvalStatusOptions"
          placeholder="审批状态"
          style="width: 120px"
          clearable
          @update:value="handleSearch"
        />
        <NSelect
          v-model:value="level"
          :options="levelOptions"
          placeholder="等级"
          style="width: 110px"
          clearable
          @update:value="handleSearch"
        />
        <NButton type="primary" @click="handleSearch">
          <template #icon><NIcon><SearchOutline /></NIcon></template>
          搜索
        </NButton>
      </NSpace>
    </NCard>

    <!-- 表格 -->
    <NCard :bordered="true" size="small">
      <div style="overflow: auto">
      <NDataTable
        :columns="columns"
        :data="data"
        :loading="loading"
        :bordered="false"
        :single-line="false"
        size="small"
        :pagination="{
          page: page,
          pageSize: pageSize,
          itemCount: total,
          onChange: handlePageChange,
          showSizePicker: false,
          prefix: () => `共 ${total} 条`,
        }"
        @update:sorter="handleSorterChange"
      />
      </div>
    </NCard>
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
