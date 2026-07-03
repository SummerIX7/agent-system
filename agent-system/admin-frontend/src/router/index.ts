import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { title: '管理员登录', requiresAuth: false },
  },
  {
    path: '/',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/DashboardView.vue'),
        meta: { title: '数据看板' },
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/UsersView.vue'),
        meta: { title: '学员管理' },
      },
      {
        path: 'users/:id',
        name: 'UserDetail',
        component: () => import('@/views/UserDetailView.vue'),
        meta: { title: '学员详情' },
      },
      {
        path: 'approval',
        name: 'Approval',
        component: () => import('@/views/ApprovalView.vue'),
        meta: { title: '审批管理' },
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/SettingsView.vue'),
        meta: { title: '系统设置' },
      },
      {
        path: 'knowledge-progress',
        name: 'KnowledgeProgress',
        component: () => import('@/views/KnowledgeProgressView.vue'),
        meta: { title: '学员知识图谱进度' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫
router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()

  // 设置页面标题
  document.title = (to.meta.title as string) || 'CNC 培训管理后台'

  // 不需要认证的页面直接放行
  if (!to.meta.requiresAuth) {
    return next()
  }

  // 无 token → 跳转登录
  if (!authStore.token) {
    return next({ name: 'Login', query: { redirect: to.fullPath } })
  }

  // 有 token 但未获取用户信息 → 去后端验证
  if (!authStore.user) {
    try {
      const { authApi } = await import('@/api/auth')
      const user = await authApi.getMe()
      if (user.role !== 'admin') {
        authStore.logout()
        return next({ name: 'Login' })
      }
      authStore.setUser(user)
    } catch {
      authStore.logout()
      return next({ name: 'Login' })
    }
  }

  // 需要管理员权限但角色不符
  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    return next({ name: 'Login' })
  }

  next()
})

export default router
