<template>
  <div class="min-h-screen flex flex-col">
    <!-- 顶部导航栏 -->
    <header class="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div class="container mx-auto px-4 h-16 flex items-center justify-between">
        <NuxtLink to="/" class="text-xl font-bold text-primary">
          多智能体协同决策系统
        </NuxtLink>
        <nav class="flex gap-6">
          <NuxtLink
            v-for="item in navItems"
            :key="item.path"
            :to="item.path"
            class="text-sm font-medium text-gray-600 hover:text-primary transition-colors"
            active-class="text-primary"
          >
            {{ item.label }}
          </NuxtLink>
        </nav>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="flex-1">
      <slot />
    </main>

    <!-- 底部 -->
    <footer class="bg-gray-50 border-t border-gray-200 py-4 text-center text-sm text-gray-500">
      领域知识个性化生成与多智能体协同决策系统 © 2026
    </footer>
  </div>
</template>

<script setup lang="ts">
const navItems = [
  { path: '/profile', label: '学习者画像' },
  { path: '/dashboard', label: '学情诊断' },
  { path: '/workflow', label: 'Agent 协同' },
  { path: '/resources', label: '资源展示' },
  { path: '/practice', label: '反馈交互' },
  { path: '/report', label: '分析报告' },
  { path: '/history', label: '历史记录' },
]
</script>
