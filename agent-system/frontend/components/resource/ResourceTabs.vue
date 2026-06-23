<template>
  <div>
    <UTabs :items="tabs" v-model="activeTab">
      <template #default="{ item, index }">
        <div class="prose max-w-none p-4" v-html="contents[index]" />
      </template>
    </UTabs>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  lecture: string
  guide: string
  test: string
}>()

const activeTab = ref(0)

const tabs = [
  { key: 'lecture', label: '定制讲义' },
  { key: 'guide', label: '实操指南' },
  { key: 'test', label: '分阶测试' },
]

const contents = computed(() => [props.lecture, props.guide, props.test])
</script>
