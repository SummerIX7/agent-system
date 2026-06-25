<template>
  <div class="min-h-screen flex flex-col">
    <!-- 顶部导航栏 -->
    <header class="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div class="container mx-auto px-4 h-16 flex items-center justify-between">
        <NuxtLink to="/" class="text-xl font-bold text-primary">
          多智能体协同决策系统
        </NuxtLink>

        <!-- 桌面端导航 -->
        <nav class="hidden md:flex items-center gap-6">
          <NuxtLink
            v-for="item in navItems"
            :key="item.path"
            :to="item.path"
            class="text-sm font-medium text-gray-600 hover:text-primary transition-colors"
            active-class="text-primary"
          >
            {{ item.label }}
          </NuxtLink>

          <!-- 用户状态 -->
          <div v-if="isLoggedIn" class="flex items-center gap-3 ml-4 pl-4 border-l">
            <span class="text-sm text-gray-600">{{ user?.username }}</span>
            <UButton size="xs" variant="ghost" @click="handleLogout">退出</UButton>
          </div>
          <div v-else class="flex items-center gap-2 ml-4 pl-4 border-l">
            <UButton size="xs" variant="ghost" to="/login">登录</UButton>
            <UButton size="xs" to="/register">注册</UButton>
          </div>
        </nav>

        <!-- 移动端菜单按钮 -->
        <UButton
          class="md:hidden"
          variant="ghost"
          icon="i-heroicons-bars-3"
          @click="mobileMenuOpen = !mobileMenuOpen"
        />
      </div>

      <!-- 移动端导航菜单 -->
      <div v-if="mobileMenuOpen" class="md:hidden border-t border-gray-100 bg-white">
        <nav class="container mx-auto px-4 py-3 space-y-2">
          <NuxtLink
            v-for="item in navItems"
            :key="item.path"
            :to="item.path"
            class="block py-2 text-sm font-medium text-gray-600 hover:text-primary transition-colors"
            active-class="text-primary"
            @click="mobileMenuOpen = false"
          >
            {{ item.label }}
          </NuxtLink>
          <div class="pt-2 border-t">
            <template v-if="isLoggedIn">
              <p class="text-sm text-gray-600 mb-2">{{ user?.username }}</p>
              <UButton size="sm" variant="ghost" @click="handleLogout">退出登录</UButton>
            </template>
            <template v-else>
              <UButton size="sm" variant="ghost" to="/login" @click="mobileMenuOpen = false">登录</UButton>
              <UButton size="sm" to="/register" @click="mobileMenuOpen = false">注册</UButton>
            </template>
          </div>
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
const router = useRouter()
const { user, isLoggedIn, restoreToken, logout } = useAuth()

const mobileMenuOpen = ref(false)

const navItems = [
  { path: '/profile', label: '学习者画像' },
  { path: '/dashboard', label: '学情诊断' },
  { path: '/workflow', label: 'Agent 协同' },
  { path: '/resources', label: '资源展示' },
  { path: '/practice', label: '反馈交互' },
  { path: '/report', label: '分析报告' },
  { path: '/history', label: '历史记录' },
]

// 页面加载时恢复 token 和用户信息
onMounted(async () => {
  await restoreToken()
})

const handleLogout = () => {
  logout()
  router.push('/login')
}
</script>
