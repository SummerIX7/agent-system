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
        暂无学习记录
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
              <span class="text-text-3 text-xs">{{ record.date }}</span>
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
    </div>
  </div>
</template>

<script setup lang="ts">
const api = useApi()
const { learnerId } = useSession()

const loading = ref(true)
const historyRecords = ref<any[]>([])

onMounted(async () => {
  if (learnerId.value) {
    try {
      const data = await api.getHistory(learnerId.value)
      historyRecords.value = data
    } catch (err) {
      console.warn('获取历史失败:', err)
    }
  }

  // 如果没有数据，显示默认记录
  if (!historyRecords.value.length) {
    historyRecords.value = [
      {
        title: '完成学情诊断',
        date: new Date().toLocaleString(),
        description: '系统构建了初始学习者画像',
        tags: ['画像构建', '学情诊断'],
      },
    ]
  }

  loading.value = false
})
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
.animate-spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
