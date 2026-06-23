<template>
  <div class="container mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold mb-6">历史记录</h1>

    <UCard>
      <template #header>
        <h2 class="text-lg font-semibold">学习历程与画像演变</h2>
      </template>

      <div v-if="loading" class="text-center py-8">
        <UIcon name="i-heroicons-arrow-path" class="w-6 h-6 animate-spin text-primary mx-auto" />
        <p class="mt-2 text-gray-500">加载中...</p>
      </div>

      <div v-else-if="historyRecords.length === 0" class="text-center py-8 text-gray-500">
        暂无学习记录
      </div>

      <div v-else class="space-y-6">
        <div
          v-for="(record, index) in historyRecords"
          :key="index"
          class="flex gap-4 p-4 rounded-lg border hover:bg-gray-50 transition-colors"
        >
          <div class="flex flex-col items-center">
            <div class="w-3 h-3 rounded-full bg-primary mt-1" />
            <div v-if="index < historyRecords.length - 1" class="w-0.5 h-full bg-gray-200 mt-1" />
          </div>
          <div class="flex-1">
            <div class="flex items-center justify-between">
              <p class="font-semibold">{{ record.title }}</p>
              <span class="text-sm text-gray-400">{{ record.date }}</span>
            </div>
            <p class="text-sm text-gray-500 mt-1">{{ record.description }}</p>
            <div class="flex gap-2 mt-2">
              <UBadge v-for="tag in record.tags" :key="tag" variant="subtle" size="sm">
                {{ tag }}
              </UBadge>
            </div>
          </div>
        </div>
      </div>
    </UCard>
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
