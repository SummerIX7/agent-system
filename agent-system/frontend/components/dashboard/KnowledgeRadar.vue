<template>
  <div class="w-full" style="max-width: 380px; height: 360px; margin: 0 auto;">
    <VChart v-if="isValidData" :option="chartOption" autoresize />
    <p v-else class="text-text-3 text-center py-12">暂无有效数据</p>
  </div>
</template>

<script setup lang="ts">
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { RadarChart } from 'echarts/charts'
import { CanvasRenderer } from 'echarts/renderers'

use([RadarChart, CanvasRenderer])

interface KnowledgePoint {
  name: string
  score: number
  level: string
}

const props = defineProps<{
  knowledgePoints: KnowledgePoint[]
}>()

const isValidData = computed(() => {
  return Array.isArray(props.knowledgePoints) &&
    props.knowledgePoints.length > 0 &&
    props.knowledgePoints.every((kp) => kp && kp.name && typeof kp.score === 'number')
})

// ✅ 使用origin的精美配置 + agent-system的动态数据
const chartOption = computed(() => ({
  radar: {
    indicator: props.knowledgePoints.map((kp) => ({
      name: kp.name,
      max: 100,
    })),
    shape: 'polygon',
    splitNumber: 4,  // origin: 4层分割，更简洁
    axisName: {
      color: '#4B5563',
      fontSize: 11,
      fontFamily: '-apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif',
    },
    splitArea: { show: false },  // origin: 隐藏分割区域背景
    splitLine: { lineStyle: { color: '#ECECEF' } },  // origin: 浅灰色网格线
    axisLine: { lineStyle: { color: '#ECECEF' } },   // origin: 浅灰色轴线
  },
  series: [{
    type: 'radar',
    data: [{
      value: props.knowledgePoints.map((kp) => kp.score),  // ✅ 动态数据
      areaStyle: { color: 'rgba(79, 70, 229, 0.08)' },    // origin: 淡靛蓝半透明
      lineStyle: { color: '#4F46E5', width: 1.5 },         // origin: 靛蓝色线条
      itemStyle: { color: '#4F46E5', borderWidth: 0 },     // origin: 靛蓝色数据点
      symbol: 'circle',
      symbolSize: 6,                                        // origin: 显示数据点
    }],
  }],
}))
</script>
