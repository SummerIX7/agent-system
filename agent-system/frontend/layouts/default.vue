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
const { user, isLoggedIn, restoreToken, logout } = useAuth()
const { setSession, setProfile } = useSession()
const api = useApi()

const mobileMenuOpen = ref(false)

const navItems = [
  { path: '/', label: '首页' },
  { path: '/profile', label: '学习者画像' },
  { path: '/dashboard', label: '学情诊断' },
  { path: '/workflow', label: 'Agent 协同' },
  { path: '/report', label: '分析报告' },
  { path: '/resources', label: '资源展示' },
  { path: '/history', label: '历史记录' },
]

// 用户名首字母（用于头像显示）
const userInitial = computed(() => {
  return user.value?.username?.charAt(0)?.toUpperCase() || 'U'
})

// 页面加载时恢复 token 和 session
onMounted(async () => {
  await restoreToken()

  // 登录态恢复后，尝试恢复 session 上下文（解决 F5 刷新后 sessionId 丢失）
  if (isLoggedIn.value) {
    try {
      const profile = await api.getMyProfile()
      if (profile) {
        setSession(profile.session_id || `user-${profile.id}`, String(profile.id))
        setProfile(profile)
      }
    } catch {
      // 404 = 用户尚未创建画像，正常情况
    }
  }
})

const handleLogout = () => {
  logout()
  mobileMenuOpen.value = false
  router.push('/login')
}
</script>
