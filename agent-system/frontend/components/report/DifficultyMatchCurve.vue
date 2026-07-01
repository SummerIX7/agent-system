<template>
  <div class="w-full" style="max-width: 480px; height: 280px; margin: 0 auto;">
    <VChart v-if="isValidData" :option="chartOption" autoresize />
    <p v-else class="text-text-3 text-center py-12">暂无有效数据</p>
  </div>
</template>

<script setup lang="ts">
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, MarkLineComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { graphic } from 'echarts'

use([LineChart, GridComponent, MarkLineComponent, CanvasRenderer])

interface MatchData {
  learnerLevel: number | string
  resources: {
    name: string
    difficulty: number
    match: number
  }[]
}

const props = defineProps<{
  data: MatchData
}>()

const isValidData = computed(() => {
  return props.data &&
    Array.isArray(props.data.resources) &&
    props.data.resources.length > 0
})

//  使用origin的精美配置 + agent-system的动态数据
const chartOption = computed(() => ({
  grid: { top: 30, right: 40, bottom: 40, left: 50 },
  tooltip: {
    trigger: 'axis',
    formatter: (params: any) => {
      const idx = params[0]?.dataIndex
      if (idx === undefined) return ''
      const r = props.data.resources[idx]
      return `${r.name}<br/>难度: ${r.difficulty.toFixed(1)}<br/>匹配度: ${(r.match * 100).toFixed(0)}%`
    },
  },
  xAxis: {
    type: 'category',
    data: props.data.resources.map((r) => r.name),  //  动态数据
    axisLine: { lineStyle: { color: '#E5E7EB' } },
    axisTick: { show: false },
    axisLabel: { color: '#9CA3AF', fontSize: 10 },
  },
  yAxis: {
    type: 'value',
    min: 1,
    max: 5,
    interval: 1,
    axisLabel: {
      formatter: (v: number) => `L${v}`,  // origin: L1/L2/L3格式
      color: '#9CA3AF',
      fontSize: 10,
      fontFamily: 'SF Mono, JetBrains Mono, Consolas, monospace',
    },
    splitLine: { lineStyle: { color: '#F3F4F6' } },
    axisLine: { show: false },
    axisTick: { show: false },
  },
  series: [
    {
      type: 'line',  // origin: 纯折线图（非柱状图）
      data: props.data.resources.map((r) => r.difficulty),  //  动态数据
      smooth: false,
      symbol: 'circle',
      symbolSize: 7,
      lineStyle: { color: '#4F46E5', width: 2 },           // origin: 靛蓝色线条
      itemStyle: { color: '#4F46E5', borderWidth: 0 },     // origin: 靛蓝色数据点
      areaStyle: {                                          // origin: 渐变背景
        color: new graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(79, 70, 229, 0.12)' },
          { offset: 1, color: 'rgba(79, 70, 229, 0.02)' },
        ]),
      },
      markLine: {
        silent: true,
        symbol: 'none',
        lineStyle: { color: '#9CA3AF', width: 1.4, type: 'dashed' },  // origin: 灰色虚线
        label: {
          show: true,
          position: 'insideEndTop',
          formatter: '学习者水平',
          color: '#9CA3AF',
          fontSize: 10,
        },
        data: [{ yAxis: props.data.learnerLevel }],  //  动态数据
      },
    },
  ],
}))
</script>
