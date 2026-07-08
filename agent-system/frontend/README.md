# C 端学习平台

面向学员的个性化学习前端，基于 Nuxt 3 构建，覆盖「画像填写 → 学情诊断 → Agent 协同 → 资源学习 → 答题练习 → 学习报告」完整闭环。

## 技术栈

- **框架**: Nuxt 3 (Vue 3 + TypeScript)
- **构建**: Vite
- **样式**: 自定义设计系统 (CSS Variables)
- **图表**: 雷达图 / 匹配曲线 (纯 SVG)
- **WebSocket**: Agent 状态实时推送

## 快速开始

```bash
# 安装依赖
pnpm install

# 开发模式
pnpm dev          # http://localhost:3000

# 生产构建
pnpm build
```

`nuxt.config.ts` 中配置后端地址：

```typescript
runtimeConfig: {
  public: {
    apiBase: 'http://localhost:8000',
    wsBase: 'ws://localhost:8000',
  },
},
```

## 项目结构

```
frontend/
├── pages/                    # 页面路由 (Nuxt 文件路由)
│   ├── index.vue             # 首页 — 功能展示
│   ├── login.vue             # 登录
│   ├── register.vue          # 注册
│   ├── profile.vue           # 学习者画像填写 (Step 1)
│   ├── dashboard.vue         # 学情诊断仪表盘 (Step 2) — 雷达图 + 盲区定位
│   ├── workflow.vue          # Agent 协同 (Step 3) — 实时状态监控
│   ├── resources.vue         # 学习资源 (Step 4) — 讲义/实验指导/项目案例
│   ├── practice.vue          # 答题练习 (Step 5) — 分阶练习 + 苏格拉底追问
│   ├── report.vue            # 学习报告 (Step 6) — 学习路径 + 核心指标
│   ├── knowledge-graph.vue   # 知识图谱 — 掌握度驱动的知识点点亮（SSR 已禁用）
│   ├── history.vue           # 学习历程
│   └── trace.vue             # 工作流追踪 (调试)
├── components/
│   ├── MarkdownRenderer.vue  # Markdown 渲染器
│   ├── agent-view/           # Agent 可视化组件
│   │   ├── AgentFlowDiagram.vue   # 协同流程图 (首页)
│   │   └── AgentFlowChart.vue     # 状态图表
│   ├── dashboard/            # 仪表盘组件
│   │   └── KnowledgeRadar.vue     # 知识掌握雷达图
│   ├── report/               # 报告组件
│   │   └── DifficultyMatchCurve.vue  # 难度匹配曲线
│   └── resource/             # 资源组件
│       └── ResourceTabs.vue       # 资源标签页
├── composables/              # 组合式函数 (自动导入)
│   ├── useApi.ts             # API 请求封装
│   ├── useAuth.ts            # 认证状态管理
│   ├── useSession.ts         # 会话管理
│   ├── useLearningPath.ts    # 学习路径状态
│   └── useAgentWebSocket.ts  # WebSocket 连接
├── utils/                    # 工具函数 (自动导入)
│   └── labels.ts             # 中文标签映射
├── types/
│   └── api.ts                # TypeScript 类型定义
├── layouts/
│   └── default.vue           # 默认布局 (导航栏 + 页脚)
├── assets/
│   └── css/
│       └── main.css          # 设计系统 (CSS 变量、按钮、卡片等)
└── nuxt.config.ts
```

## 学习流程

```
首页 → 注册/登录 → 填写学习者画像 (Step 1)
    → 学情诊断仪表盘 (Step 2) — 雷达图 + 盲区
    → Agent 协同生成 (Step 3) — 6 Agent 实时状态
    → 查看生成资源 (Step 4) — 讲义/指导/案例
    → 答题练习 (Step 5) — 节点练习 / 综合练习
    → 学习报告 (Step 6) — 路径进度 + 机台申请
    → 推进到下一节点 → 回到 Step 4 ...
    → 知识图谱 (独立页面) — 可视化知识体系掌握度
```

## 页面说明

| 页面 | 路由 | 功能 |
|------|------|------|
| 首页 | `/` | Agent 介绍 + 学习闭环展示 |
| 登录/注册 | `/login`, `/register` | JWT 认证 |
| 学习者画像 | `/profile` | 学历/专业/技能自评/学习目标 |
| 学情诊断 | `/dashboard` | 知识雷达图 + 盲区定位 + 推荐难度 |
| Agent 协同 | `/workflow` | 6 Agent 实时状态 + 资源生成进度 |
| 学习资源 | `/resources?stage=N` | 讲义/实验指导/项目案例 + 参考来源 |
| 答题练习 | `/practice?level=node\|comprehensive` | 节点练习 + 综合练习 + 苏格拉底追问 + 简答批改 |
| 学习报告 | `/report` | 学习路径进度 + 核心指标 + 机台申请 |
| 知识图谱 | `/knowledge-graph` | 树状知识体系 + 掌握度点亮（深绿/浅绿/黄/灰） |
| 学习历程 | `/history` | 画像演变历史 |
| 工作流追踪 | `/trace` | Agent LLM 调用明细 (调试) |
