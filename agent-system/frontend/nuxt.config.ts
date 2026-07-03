// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-01-01',
  devtools: { enabled: true },

  devServer: {
    port: 3000,
  },

  modules: [
    '@nuxt/ui',
    '@nuxtjs/tailwindcss',
  ],

  css: ['~/assets/css/main.css'],

  runtimeConfig: {
    public: {
      apiBase: 'http://localhost:8000',
      wsBase: 'ws://localhost:8000',
    },
  },

  app: {
    head: {
      title: '领域知识个性化生成与多智能体协同决策系统',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      ],
      link: [
        { rel: 'icon', type: 'image/svg+xml', href: '/logo.svg' },
      ],
    },
  },

  // 强制 knowledge-graph 页面禁用 SSR（vue-echarts 依赖浏览器 DOM API）
  routeRules: {
    '/knowledge-graph': { ssr: false },
  },
})
