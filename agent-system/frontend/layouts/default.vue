<template>
  <div class="min-h-screen flex flex-col" style="font-family: var(--font)">
    <!-- 毛玻璃导航栏 -->
    <header class="topnav">
      <NuxtLink to="/" class="topnav__brand">
        <span class="dot" style="background: var(--accent); width: 7px; height: 7px; border-radius: 50%"></span>
        领域知识个性化生成系统
      </NuxtLink>

      <!-- 桌面端导航 -->
      <nav class="topnav__items hidden md:flex">
        <NuxtLink
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="topnav__link"
          active-class="active"
        >
          {{ item.label }}
        </NuxtLink>
      </nav>

      <div class="topnav__right">
        <!-- 认证状态：登录/注册 或 用户头像+退出 -->
        <template v-if="isLoggedIn">
          <div class="topnav__user">
            <span class="topnav__avatar">{{ userInitial }}</span>
            <span>{{ user?.username }}</span>
          </div>
          <button class="btn btn--ghost btn--sm" @click="handleLogout">退出</button>
        </template>
        <template v-else>
          <NuxtLink to="/login" class="btn btn--ghost btn--sm">登录</NuxtLink>
          <NuxtLink to="/register" class="btn btn--primary btn--sm">注册</NuxtLink>
        </template>

        <!-- 移动端菜单按钮 -->
        <button
          class="md:hidden btn btn--ghost btn--sm"
          @click="mobileMenuOpen = !mobileMenuOpen"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="3" y1="6" x2="21" y2="6"></line>
            <line x1="3" y1="12" x2="21" y2="12"></line>
            <line x1="3" y1="18" x2="21" y2="18"></line>
          </svg>
        </button>
      </div>
    </header>

    <!-- 移动端导航菜单 -->
    <div v-if="mobileMenuOpen" class="md:hidden border-b border-line bg-white">
      <nav class="px-4 py-3 space-y-1">
        <NuxtLink
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="block py-2 px-3 text-sm rounded-md hover:bg-bg-muted transition-colors"
          active-class="text-accent bg-accent-soft"
          @click="mobileMenuOpen = false"
        >
          {{ item.label }}
        </NuxtLink>
        <div class="pt-2 mt-2 border-t border-line">
          <template v-if="isLoggedIn">
            <p class="px-3 py-2 text-sm text-text-2">{{ user?.username }}</p>
            <button class="w-full text-left px-3 py-2 text-sm text-err hover:bg-err-soft rounded-md" @click="handleLogout">
              退出登录
            </button>
          </template>
          <template v-else>
            <NuxtLink to="/login" class="block px-3 py-2 text-sm hover:bg-bg-muted rounded-md" @click="mobileMenuOpen = false">
              登录
            </NuxtLink>
            <NuxtLink to="/register" class="block px-3 py-2 text-sm text-accent hover:bg-accent-soft rounded-md" @click="mobileMenuOpen = false">
              注册
            </NuxtLink>
          </template>
        </div>
      </nav>
    </div>

    <!-- 步骤进度指示器 -->
    <div class="step-bar">
      <div class="step-bar__inner">
        <NuxtLink
          v-for="(step, idx) in steps"
          :key="step.path"
          :to="step.path"
          class="step-bar__item"
          :class="{ active: isCurrentStep(step.path), done: isStepDone(step.path) }"
        >
          <span class="step-bar__num">{{ isStepDone(step.path) ? '✓' : idx + 1 }}</span>
          <span class="step-bar__label">{{ step.label }}</span>
        </NuxtLink>
      </div>
    </div>

    <!-- 主内容区 -->
    <main class="flex-1">
      <slot />
    </main>

    <!-- 底部版权 -->
    <footer class="py-6 text-center text-text-3 text-xs border-t border-line">
      © 2026 领域知识个性化生成与多智能体协同决策系统
    </footer>
  </div>
</template>

<script setup lang="ts">
const router = useRouter()
const route = useRoute()
const { user, isLoggedIn, restoreToken, logout } = useAuth()
const { sessionId } = useSession()

const mobileMenuOpen = ref(false)

const navItems = [
  { path: '/', label: '首页' },
  { path: '/profile', label: '学习者画像' },
  { path: '/dashboard', label: '学情诊断' },
  { path: '/workflow', label: 'Agent 协同' },
  { path: '/resources', label: '资源展示' },
  { path: '/practice', label: '反馈交互' },
  { path: '/report', label: '分析报告' },
  { path: '/history', label: '历史记录' },
]

// 步骤进度条：只包含 6 个核心步骤
const steps = [
  { path: '/profile', label: '画像' },
  { path: '/dashboard', label: '诊断' },
  { path: '/workflow', label: '生成' },
  { path: '/resources', label: '资源' },
  { path: '/practice', label: '练习' },
  { path: '/report', label: '报告' },
]

// 步骤顺序映射（用于判断哪些步骤已完成）
const stepOrder = Object.fromEntries(steps.map((s, i) => [s.path, i]))

// 判断当前所在步骤
const currentStepIndex = computed(() => {
  const idx = stepOrder[route.path]
  return idx !== undefined ? idx : -1
})

const isCurrentStep = (path: string) => route.path === path
const isStepDone = (path: string) => {
  const stepIdx = stepOrder[path]
  if (stepIdx === undefined) return false
  // 已完成的步骤：有 session 且步骤在当前步骤之前
  return sessionId.value !== '' && stepIdx < currentStepIndex.value
}

// 用户名首字母（用于头像显示）
const userInitial = computed(() => {
  return user.value?.username?.charAt(0)?.toUpperCase() || 'U'
})

// 页面加载时恢复 token 和用户信息
onMounted(async () => {
  await restoreToken()
})

const handleLogout = () => {
  logout()
  mobileMenuOpen.value = false
  router.push('/login')
}
</script>

<style scoped>
/* ── 步骤进度条 ── */
.step-bar {
  border-bottom: 1px solid var(--line);
  background: var(--bg);
  position: sticky;
  top: 56px;
  z-index: 40;
}
.step-bar__inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  padding: 0 24px;
}
.step-bar__item {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 14px 8px;
  font-size: 13px;
  color: var(--text-3);
  text-decoration: none;
  border-bottom: 2px solid transparent;
  transition: all .15s;
  position: relative;
}
.step-bar__item:hover {
  color: var(--text-2);
  border-bottom-color: var(--line-2);
}
.step-bar__item.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
  font-weight: 600;
}
.step-bar__item.done {
  color: var(--ok);
}
.step-bar__num {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--bg-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  font-family: var(--mono);
  flex-shrink: 0;
}
.step-bar__item.active .step-bar__num {
  background: var(--accent);
  color: #fff;
}
.step-bar__item.done .step-bar__num {
  background: var(--ok-soft);
  color: var(--ok);
}
.step-bar__label {
  white-space: nowrap;
}

@media (max-width: 768px) {
  .step-bar__label {
    display: none;
  }
  .step-bar__item {
    padding: 10px 4px;
  }
}
</style>
