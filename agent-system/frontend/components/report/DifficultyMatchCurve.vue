<template>
  <div class="w-full h-96">
    <VChart :option="chartOption" autoresize />
  </div>
</template>

<script setup lang="ts">
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  MarkLineComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([BarChart, LineChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent, MarkLineComponent, CanvasRenderer])

interface MatchData {
  learnerLevel: number
  resources: {
    name: string
    difficulty: number
    matchScore: number
  }[]
}

const props = defineProps<{
  data: MatchData
}>()

const chartOption = computed(() => ({
  title: {
    text: '资源难度匹配曲线',
    left: 'center',
  },
  tooltip: {
    trigger: 'axis',
  },
  legend: {
    data: ['资源难度', '匹配度'],
    bottom: 0,
  },
  xAxis: {
    type: 'category',
    data: props.data.resources.map((r) => r.name),
    axisLabel: {
      rotate: 30,
    },
  },
  yAxis: [
    {
      type: 'value',
      name: '难度',
      max: 5,
    },
    {
      type: 'value',
      name: '匹配度',
      max: 1,
      axisLabel: {
        formatter: '{value * 100}%',
      },
    },
  ],
  series: [
    {
      name: '资源难度',
      type: 'bar',
      data: props.data.resources.map((r) => r.difficulty),
      itemStyle: {
        color: 'rgb(59, 130, 246)',
      },
      markLine: {
        data: [
          {
            yAxis: props.data.learnerLevel,
            name: '学习者水平',
            lineStyle: {
              color: 'rgb(239, 68, 68)',
              type: 'dashed',
            },
            label: {
              formatter: '学习者水平: {c}',
            },
          },
        ],
      },
    },
    {
      name: '匹配度',
      type: 'line',
      yAxisIndex: 1,
      data: props.data.resources.map((r) => r.matchScore),
      itemStyle: {
        color: 'rgb(16, 185, 129)',
      },
      smooth: true,
    },
  ],
}))
</script>
