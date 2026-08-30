<template>
  <div class="page page--wide">
    <div class="page-head">
      <p class="page-head__eyebrow">历史记录</p>
      <h1 class="page-head__title">学习历程与画像演变</h1>
      <p class="page-head__desc">查看您的学习历史和画像变化轨迹。</p>
    </div>

    <div class="card">
      <div v-if="loading" class="text-center py-8">
        <div class="animate-spin" style="width: 24px; height: 24px; margin: 0 auto; border: 3px solid var(--line); border-top-color: var(--accent); border-radius: 50%;"></div>
        <p class="mt-4 text-text-2">加载中...</p>
      </div>

      <div v-else-if="historyRecords.length === 0" class="text-center py-8 text-text-3">
        暂无学习记录<br/>
        <NuxtLink to="/resources" class="btn btn--ghost btn--sm" style="margin-top: 12px">去学习产生记录 →</NuxtLink>
      </div>

      <div v-else class="history-list">
        <div
          v-for="(record, index) in historyRecords"
          :key="index"
          class="history-item"
        >
          <div class="history-dot">
            <div class="history-dot__circle"></div>
            <div v-if="index < historyRecords.length - 1" class="history-dot__line"></div>
          </div>
          <div class="history-content">
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <p style="font-weight: 600;">{{ record.title }}</p>
              <span class="text-text-3 text-xs">{{ formatDate(record.date) }}</span>
            </div>
            <p class="text-text-2 text-sm mt-1">{{ record.description }}</p>
            <div style="display: flex; gap: 8px; margin-top: 8px;">
              <span v-for="tag in record.tags" :key="tag" class="badge badge--mute">
                {{ tag }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 分页导航 -->
      <div v-if="totalPages > 1" class="pagination-bar">
        <span class="pagination-info">{{ totalRecords }} 条记录，第 {{ currentPage }}/{{ totalPages }} 页</span>
        <div class="pagination-btns">
          <button class="btn btn--ghost btn--sm" :disabled="currentPage <= 1" @click="goPage(currentPage - 1)">上一页</button>
          <button
            v-for="p in displayPages"
            :key="p"
            class="btn btn--sm"
            :class="p === currentPage ? 'btn--primary' : 'btn--ghost'"
            @click="goPage(p)"
          >
            {{ p }}
          </button>
          <button class="btn btn--ghost btn--sm" :disabled="currentPage >= totalPages" @click="goPage(currentPage + 1)">下一页</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const api = useApi()
const { learnerId } = useSession()

const loading = ref(true)
const historyRecords = ref<any[]>([])
const currentPage = ref(1)
const totalPages = ref(1)
const totalRecords = ref(0)
const PAGE_SIZE = 20

const fetchHistory = async (page: number = 1) => {
  if (!learnerId.value) return
  loading.value = true
  try {
    const data = await api.getHistory(learnerId.value, page, PAGE_SIZE)
    historyRecords.value = data.items
    currentPage.value = data.page
    totalPages.value = data.total_pages
    totalRecords.value = data.total
  } catch (err) {
    console.warn('获取历史失败:', err)
  } finally {
    loading.value = false
  }
}

const goPage = (page: number) => {
  if (page < 1 || page > totalPages.value || page === currentPage.value) return
  fetchHistory(page)
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const formatDate = (value: string) => {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const displayPages = computed(() => {
  const pages: number[] = []
  const start = Math.max(1, currentPage.value - 2)
  const end = Math.min(totalPages.value, currentPage.value + 2)
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
})

onMounted(() => fetchHistory(1))
</script>

<style scoped>
.history-list {
  display: flex;
  flex-direction: column;
}
.history-item {
  display: flex;
  gap: 18px;
  padding: 18px 0;
}
.history-item:first-child {
  padding-top: 0;
}
.history-item:last-child {
  padding-bottom: 0;
}
.history-dot {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
}
.history-dot__circle {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--accent);
  flex-shrink: 0;
}
.history-dot__line {
  width: 2px;
  flex: 1;
  background: var(--line);
  margin-top: 4px;
}
.history-content {
  flex: 1;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--line);
}
.history-item:last-child .history-content {
  border-bottom: none;
  padding-bottom: 0;
}
.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 24px;
  margin-top: 24px;
  border-top: 1px solid var(--line);
}
.pagination-info {
  font-size: 13px;
  color: var(--text-3);
}
.pagination-btns {
  display: flex;
  align-items: center;
  gap: 6px;
}
.animate-spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
