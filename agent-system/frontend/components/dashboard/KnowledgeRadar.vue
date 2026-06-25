<template>
  <div class="w-full h-96">
    <VChart v-if="isValidData" :option="chartOption" autoresize />
    <p v-else class="text-gray-400 text-center py-12">暂无有效数据</p>
  </div>
</template>

<script setup lang="ts">
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { RadarChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([RadarChart, TitleComponent, TooltipComponent, LegendComponent, CanvasRenderer])

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

const chartOption = computed(() => ({
  title: {
    text: '知识掌握雷达图',
    left: 'center',
  },
  tooltip: {
    trigger: 'item',
  },
  radar: {
    indicator: props.knowledgePoints.map((kp) => ({
      name: kp.name,
      max: 100,
    })),
    shape: 'polygon',
    splitNumber: 5,
  },
  series: [
    {
      type: 'radar',
      data: [
        {
          value: props.knowledgePoints.map((kp) => kp.score),
          name: '当前掌握度',
          areaStyle: {
            color: 'rgba(59, 130, 246, 0.2)',
          },
          lineStyle: {
            color: 'rgb(59, 130, 246)',
          },
          itemStyle: {
            color: 'rgb(59, 130, 246)',
          },
        },
      ],
    },
  ],
}))
</script>
