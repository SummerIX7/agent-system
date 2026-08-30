import { createRouter, createWebHistory } from 'vue-router'

/**
 * 路由表（对应原 Nuxt pages/ 目录，1:1 移植）
 *
 * meta.bare      —— 登录/注册页不渲染导航壳（对应原 definePageMeta({ layout: false })）
 * meta.keepalive —— workflow 页面保留组件状态（对应原 definePageMeta({ keepalive: true })）
 */
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: () => import('@/views/HomeView.vue') },
    { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { bare: true } },
    { path: '/register', name: 'register', component: () => import('@/views/RegisterView.vue'), meta: { bare: true } },
    { path: '/profile', name: 'profile', component: () => import('@/views/ProfileView.vue') },
    { path: '/dashboard', name: 'dashboard', component: () => import('@/views/DashboardView.vue') },
    { path: '/workflow', name: 'workflow', component: () => import('@/views/WorkflowView.vue'), meta: { keepalive: true } },
    { path: '/resources', name: 'resources', component: () => import('@/views/ResourcesView.vue') },
    { path: '/practice', name: 'practice', component: () => import('@/views/PracticeView.vue') },
    { path: '/report', name: 'report', component: () => import('@/views/ReportView.vue') },
    { path: '/knowledge-graph', name: 'knowledge-graph', component: () => import('@/views/KnowledgeGraphView.vue') },
    { path: '/trace', name: 'trace', component: () => import('@/views/TraceView.vue') },
    { path: '/history', name: 'history', component: () => import('@/views/HistoryView.vue') },
    // 兜底：未匹配路由回到首页（Nuxt 默认 404 行为的等价简化）
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

export default router
