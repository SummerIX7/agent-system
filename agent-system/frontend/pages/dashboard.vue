<template>
  <div class="page page--wide">
    <div class="page-head">
      <p class="page-head__eyebrow">Step 2</p>
      <h1 class="page-head__title">学情诊断仪表盘</h1>
      <p class="page-head__desc">基于您提交的学习者画像，系统将为您生成个性化学习路径。</p>
    </div>

    <!-- 统计指标 -->
    <div class="stats-row">
      <div class="stat-cell">
        <div style="font-size: 12px; color: var(--text-3)">总体掌握度</div>
        <div style="font-size: 28px; font-weight: 600; letter-spacing: -.03em; margin-top: 8px">
          {{ overallMastery }}<span style="font-size: 16px; color: var(--text-3)">分</span>
        </div>
        <div style="font-size: 12px; color: var(--text-3); margin-top: 4px">{{ masteryLevel }}</div>
      </div>
      <div class="stat-cell">
        <div style="font-size: 12px; color: var(--text-3)">已覆盖知识点</div>
        <div style="font-size: 28px; font-weight: 600; letter-spacing: -.03em; margin-top: 8px">{{ knowledgePoints.length }}</div>
        <div style="font-size: 12px; color: var(--text-3); margin-top: 4px">已评估学习领域</div>
      </div>
      <div class="stat-cell">
        <div style="font-size: 12px; color: var(--text-3)">知识盲区</div>
        <div style="font-size: 28px; font-weight: 600; letter-spacing: -.03em; margin-top: 8px; color: var(--err)">{{ blindSpots.length }}</div>
        <div style="font-size: 12px; color: var(--text-3); margin-top: 4px">需重点学习</div>
      </div>
      <div class="stat-cell">
        <div style="font-size: 12px; color: var(--text-3)">推荐难度等级</div>
        <div style="font-size: 28px; font-weight: 600; letter-spacing: -.03em; margin-top: 8px">{{ recommendedLevel }}</div>
        <div style="font-size: 12px; color: var(--text-3); margin-top: 4px">{{ levelDesc }}</div>
      </div>
    </div>

    <!-- 雷达图 + 知识盲区 -->
    <div class="dashboard-grid">
      <div class="card">
        <div class="card__head">
          <h2 class="card__title">知识掌握雷达图</h2>
          <span class="badge badge--mute">{{ knowledgePoints.length }} 维度</span>
        </div>
        <div style="display: flex; align-items: center; justify-content: center; padding: 8px 0 4px">
          <DashboardKnowledgeRadar
            v-if="knowledgePoints.length > 0"
            :key="radarKey"
            :knowledge-points="knowledgePoints"
          />
          <p v-else class="text-text-3 text-center py-12">暂无诊断数据</p>
        </div>
      </div>

      <div class="card">
        <div class="card__head">
          <h2 class="card__title">知识盲区定位</h2>
          <span class="badge badge--err">{{ blindSpots.length }} 项待提升</span>
        </div>
        <div v-for="spot in blindSpots" :key="spot.name" class="blind-item">
          <div style="flex: 1">
            <div style="font-size: 14px; font-weight: 500">{{ spot.name }}</div>
            <div class="bar" style="margin-top: 8px">
              <div
                class="bar__fill"
                :style="{ width: (spot.severity * 100) + '%', background: spot.severity > 0.7 ? 'var(--err)' : 'var(--warn)' }"
              ></div>
            </div>
          </div>
          <div style="font-size: 13px; font-weight: 600; font-family: var(--mono); width: 44px; text-align: right" :style="{ color: spot.severity > 0.7 ? 'var(--err)' : 'var(--warn)' }">
            {{ (spot.severity * 100).toFixed(0) }}%
          </div>
        </div>
        <p v-if="blindSpots.length === 0" class="text-text-3 text-center py-4">暂无检测到的知识盲区</p>
        <div v-if="blindSpots.length > 0" style="margin-top: 20px; padding: 14px; background: var(--accent-soft); border-radius: var(--radius-sm); font-size: 12.5px; color: var(--text-2); line-height: 1.7">
          <strong style="color: var(--accent)">诊断建议</strong>：盲区集中在相关知识领域，建议优先学习基础内容，再向进阶过渡。
        </div>
      </div>
    </div>

    <!-- 能力维度分析 -->
    <div class="card" style="margin-top: 24px">
      <div class="card__head">
        <h2 class="card__title">能力维度分析</h2>
        <span class="card__sub">点击维度可查看对应学习资源</span>
      </div>
      <div v-for="kp in knowledgePoints" :key="kp.name" class="ability-row">
        <div style="font-size: 13px; font-weight: 500; width: 110px">{{ kp.name }}</div>
        <div style="flex: 1">
          <div class="bar">
            <div class="bar__fill" :class="getBarClass(kp.score)" :style="{ width: kp.score + '%' }"></div>
          </div>
        </div>
        <div style="font-size: 14px; font-weight: 600; font-family: var(--mono); width: 36px; text-align: right">{{ kp.score.toFixed(0) }}</div>
        <div style="width: 56px; text-align: right">
          <span class="badge" :class="getBadgeClass(kp.score)">{{ kp.level }}</span>
        </div>
      </div>
      <p v-if="knowledgePoints.length === 0" class="text-text-3 text-center py-8">暂无能力维度数据</p>
    </div>

    <div style="display: flex; gap: 12px; justify-content: center; margin-top: 32px">
      <NuxtLink to="/workflow" class="btn btn--primary btn--lg">查看 Agent 协同过程 →</NuxtLink>
      <NuxtLink to="/report" class="btn btn--ghost btn--lg">查看学习报告</NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
const api = useApi()
const { sessionId, profile } = useSession()

const knowledgePoints = ref<any[]>([])
const blindSpots = ref<any[]>([])
const radarKey = ref(0)

// 计算总体掌握度
const overallMastery = computed(() => {
  if (knowledgePoints.value.length === 0) return 0
  const sum = knowledgePoints.value.reduce((acc, kp) => acc + kp.score, 0)
  return Math.round(sum / knowledgePoints.value.length)
})

// 掌握度等级
const masteryLevel = computed(() => {
  const score = overallMastery.value
  if (score >= 80) return '优秀 · 继续保持'
  if (score >= 60) return '中级 · 建议巩固基础'
  if (score >= 40) return '初级 · 需要加强学习'
  return '入门 · 建议系统学习'
})

// 推荐难度等级
const recommendedLevel = computed(() => {
  const score = overallMastery.value
  if (score >= 80) return 'L4'
  if (score >= 60) return 'L3'
  if (score >= 40) return 'L2'
  return 'L1'
})

const levelDesc = computed(() => {
  const level = recommendedLevel.value
  if (level === 'L4') return '高级 · 挑战型任务'
  if (level === 'L3') return '进阶 · 巩固提升'
  if (level === 'L2') return '初级 → 进阶过渡'
  return '入门 · 基础学习'
})

const sanitizeKnowledgePoints = (kps: any[]): any[] => {
  if (!Array.isArray(kps)) return []
  return kps
    .filter((kp) => kp && typeof kp === 'object' && kp.name)
    .map((kp) => ({
      name: String(kp.name),
      score: typeof kp.score === 'number' ? kp.score : Number(kp.score) || 0,
      level: kp.level || 'beginner',
    }))
}

// 获取进度条样式类
const getBarClass = (score: number): string => {
  if (score >= 70) return 'ok'
  if (score >= 50) return 'warn'
  return ''
}

// 获取徽章样式类
const getBadgeClass = (score: number): string => {
  if (score >= 70) return 'badge--ok'
  if (score >= 50) return 'badge--warn'
  return 'badge--err'
}

onMounted(async () => {
  // 先从全局 profile 加载
  if (profile.value?.knowledge_points?.length) {
    knowledgePoints.value = sanitizeKnowledgePoints(profile.value.knowledge_points)
    blindSpots.value = (profile.value.blind_spots || []).map((bs: any) => {
      if (typeof bs === 'string') return { name: bs, severity: 0.7 }
      return { name: bs.name || '未知', severity: bs.severity || 0.7 }
    })
    radarKey.value++
  }

  // 再从后端获取最新数据
  if (sessionId.value) {
    try {
      const viz = await api.getVisualization(sessionId.value)
      if (viz.knowledge_points?.length) {
        knowledgePoints.value = sanitizeKnowledgePoints(viz.knowledge_points)
        radarKey.value++
      }
      if (viz.blind_spots?.length) {
        blindSpots.value = viz.blind_spots.map((bs: any) => ({
          name: bs.name || '未知',
          severity: typeof bs.severity === 'number' ? bs.severity : 0.7,
        }))
      }
    } catch (err) {
      console.warn('获取可视化数据失败，使用画像数据:', err)
    }
  }
})
</script>

<style scoped>
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1px;
  background: var(--line);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  overflow: hidden;
  margin-bottom: 24px;
}
.stat-cell {
  background: var(--bg);
  padding: 22px 24px;
}
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
}
.blind-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 0;
  border-bottom: 1px solid var(--line);
}
.blind-item:last-of-type {
  border-bottom: none;
}
.ability-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 18px 0;
  border-bottom: 1px solid var(--line);
}
.ability-row:last-child {
  border-bottom: none;
}
@media (max-width: 760px) {
  .stats-row { grid-template-columns: 1fr 1fr; }
  .dashboard-grid { grid-template-columns: 1fr; }
}
</style>
