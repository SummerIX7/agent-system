<template>
  <div class="w-full" style="max-width: 420px; height: 380px; margin: 0 auto;">
    <VChart v-if="isValidData" :option="chartOption" autoresize />
    <p v-else class="text-text-3 text-center py-12">暂无有效数据</p>
  </div>
</template>

<script setup lang="ts">
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { RadarChart } from 'echarts/charts'
import { CanvasRenderer } from 'echarts/renderers'
import { TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components'

use([RadarChart, CanvasRenderer, TitleComponent, TooltipComponent, LegendComponent])

interface KnowledgePoint {
  name: string
  score: number
  level: string
}

interface RadarIndicator {
  name: string
  max: number
}

const props = defineProps<{
  // 仪表盘模式：知识点数组
  knowledgePoints?: KnowledgePoint[]
  // 知识图谱模式：雷达指示器 + 值
  indicators?: RadarIndicator[]
  values?: number[]
  title?: string
}>()

const isValidData = computed(() => {
  // 模式1：knowledgePoints
  if (Array.isArray(props.knowledgePoints) && props.knowledgePoints.length > 0) {
    return props.knowledgePoints.every((kp) => kp && kp.name && typeof kp.score === 'number' && !Number.isNaN(kp.score))
  }
  // 模式2：indicators + values
  if (Array.isArray(props.indicators) && props.indicators.length > 0 && Array.isArray(props.values)) {
    return props.indicators.length === props.values.length && props.values.every((v) => !Number.isNaN(v))
  }
  return false
})

const chartOption = computed(() => {
  // 确定数据来源
  const isKP = Array.isArray(props.knowledgePoints) && props.knowledgePoints.length > 0

  let indicator: { name: string; max: number }[]
  let value: number[]

  if (isKP) {
    indicator = props.knowledgePoints!.map((kp) => ({
      name: kp.name,
      max: 100,
    }))
    value = props.knowledgePoints!.map((kp) => {
      const s = kp.score
      return (typeof s === 'number' && !Number.isNaN(s)) ? s : 0
    })
  } else {
    indicator = props.indicators!.map((ind) => ({
      name: ind.name,
      max: ind.max,
    }))
    value = props.values!
  }

  const seriesName = props.title || (isKP ? '掌握程度' : '知识覆盖')

  return {
    title: props.title ? {
      text: props.title,
      left: 'center',
      top: 8,
      textStyle: {
        fontSize: 13,
        fontWeight: 600,
        color: '#4B5563',
      },
    } : undefined,
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        // axis trigger 时 params 是数组（每个 series 一个元素），取第一个
        const p = Array.isArray(params) ? params[0] : params
        // dimensionIndex 是当前 hover 的维度索引
        const dimIdx = typeof p.dimensionIndex === 'number' ? p.dimensionIndex : 0
        // radar 的 value 是数组（每个维度一个值）
        const values = Array.isArray(p.value) ? p.value : [p.value]
        const val = typeof values[dimIdx] === 'number' && !Number.isNaN(values[dimIdx]) ? values[dimIdx] : 0
        const ind = indicator[dimIdx] || indicator[0]
        if (!ind) return `${p.name}: ${val}`
        const percentage = Math.round(val / ind.max * 100)
        return `${ind.name}<br/>覆盖度: <b>${percentage}%</b> (${val}/${ind.max})`
      },
    },
    legend: {
      bottom: 0,
      data: [seriesName],
      textStyle: {
        color: '#9CA3AF',
        fontSize: 11,
      },
    },
    radar: {
      center: ['50%', '50%'],
      radius: '62%',
      indicator,
      shape: 'polygon',
      splitNumber: 4,
      axisName: {
        color: '#4B5563',
        fontSize: 11,
        fontFamily: '-apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif',
      },
      splitArea: { show: false },
      splitLine: { lineStyle: { color: '#ECECEF' } },
      axisLine: { lineStyle: { color: '#ECECEF' } },
    },
    series: [{
      type: 'radar',
      name: seriesName,
      data: [{
        value,
        name: seriesName,
        areaStyle: { color: 'rgba(79, 70, 229, 0.08)' },
        lineStyle: { color: '#4F46E5', width: 1.5 },
        itemStyle: { color: '#4F46E5', borderWidth: 0 },
        symbol: 'circle',
        symbolSize: 6,
      }],
    }],
  }
})
</script>
