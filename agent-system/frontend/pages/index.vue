<template>
  <div>
    <!-- Hero区域 -->
    <section class="page" style="padding-top: 80px; padding-bottom: 60px;">
      <div class="page-head" style="text-align: center; max-width: 640px; margin: 0 auto;">
        <p class="page-head__eyebrow" style="margin-bottom: 16px;">领域知识个性化生成</p>
        <h1 class="page-head__title" style="font-size: 40px; letter-spacing: -.035em;">
          让每个学习者，<br>得到为自己而生的学习资源。
        </h1>
        <p class="page-head__desc" style="margin: 20px auto 0; max-width: 560px; line-height: 1.7;">
          基于学习者画像精准诊断知识盲区，通过多智能体双视角审核纠偏机制生成可溯源的个性化讲义、实验与案例，并根据答题反馈动态调整学习路径。
        </p>
        <div style="margin-top: 32px; display: flex; gap: 12px; justify-content: center;">
          <NuxtLink to="/profile" class="btn btn--primary btn--lg">开始学习诊断 →</NuxtLink>
          <NuxtLink to="/workflow" class="btn btn--ghost btn--lg">查看 Agent 协同</NuxtLink>
        </div>
      </div>
    </section>

    <!-- Agent介绍 -->
    <section class="page" style="padding-top: 0;">
      <div style="max-width: 560px; margin-bottom: 40px;">
        <h2 class="page-head__title" style="font-size: 22px;">六个 Agent，各司其职</h2>
        <p class="page-head__desc" style="margin-top: 10px;">
          每个 Agent 负责教学链路中的一个关键环节，通过双视角审核与自动修正降低知识谬误率，确保生成内容准确、可溯源、难度适配。
        </p>
      </div>
      <div class="agent-grid">
        <div v-for="agent in agents" :key="agent.num" class="agent-cell">
          <div style="font-size: 12px; color: var(--text-3); font-family: var(--mono); margin-bottom: 12px">{{ agent.num }}</div>
          <div style="font-size: 15px; font-weight: 600">{{ agent.name }}</div>
          <div style="font-size: 13px; color: var(--text-2); margin-top: 8px; line-height: 1.6">{{ agent.desc }}</div>
        </div>
      </div>
    </section>

    <!-- 学习闭环 -->
    <section class="page" style="padding-top: 0;">
      <div style="margin-bottom: 36px;">
        <h2 class="page-head__title" style="font-size: 22px;">完整学习闭环</h2>
        <p class="page-head__desc" style="margin-top: 8px;">从画像输入到反馈调整，四个环节构成自适应学习闭环。</p>
      </div>
      <div class="steps-grid">
        <div v-for="step in steps" :key="step.no">
          <div style="font-family: var(--mono); font-size: 12px; color: var(--accent); margin-bottom: 10px">步骤 {{ step.no }}</div>
          <div style="font-size: 14px; font-weight: 600">{{ step.title }}</div>
          <div style="font-size: 13px; color: var(--text-2); margin-top: 6px; line-height: 1.6">{{ step.desc }}</div>
        </div>
      </div>
    </section>

    <!-- Agent流程图 -->
    <section class="page page--wide" style="padding-top: 0; padding-bottom: 80px;">
      <div style="margin-bottom: 36px;">
        <h2 class="page-head__title" style="font-size: 22px;">Agent 协同流程</h2>
        <p class="page-head__desc" style="margin-top: 8px;">6个AI Agent协同工作，从学情分析到试题生成的完整流程。</p>
      </div>
      <AgentViewAgentFlowDiagram />
    </section>
  </div>
</template>

<script setup lang="ts">
const agents = [
  { num: '01', name: '学情分析 Agent', desc: '解析学习者画像，定位知识盲区，匹配四个难度等级。' },
  { num: '02', name: '路径规划 Agent', desc: '基于盲区生成个性化学习路径与资源推荐序列。' },
  { num: '03', name: '知识生成 Agent', desc: '结合 RAG 知识库生成讲义、实验指导与项目案例，标注来源。' },
  { num: '04', name: '审核纠偏 Agent', desc: '双视角审查内容准确性，发现问题后自动修正，确保内容质量。' },
  { num: '05', name: '试题生成 Agent', desc: '按难度生成分阶试题，并根据答题反馈动态调整路径。' },
  { num: '06', name: '决策调度 Agent', desc: '工作流中枢，根据审核结果决策通过、重试或降级完成。' },
]

const steps = [
  { no: '01', title: '画像输入', desc: '填写学历、专业与技能自评，系统构建学习者画像。' },
  { no: '02', title: '诊断与生成', desc: '多 Agent 协同诊断盲区，生成个性化资源并审核纠偏。' },
  { no: '03', title: '学习与答题', desc: '学习讲义与案例，完成分阶试题，获得苏格拉底式追问。' },
  { no: '04', title: '反馈调整', desc: '根据答题结果实时调整学习路径与难度匹配。' },
]
</script>

<style scoped>
.agent-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1px;
  background: var(--line);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  overflow: hidden;
}
.agent-cell {
  background: var(--bg);
  padding: 26px 24px;
  transition: background .15s;
}
.agent-cell:hover {
  background: var(--bg-soft);
}
.steps-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
}
@media (max-width: 760px) {
  .agent-grid { grid-template-columns: 1fr; }
  .steps-grid { grid-template-columns: 1fr 1fr; }
}
</style>
