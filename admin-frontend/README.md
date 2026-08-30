# B 端管理后台

管理员使用的 Web 后台，负责学员管理、机台使用审批、知识库维护。

## 技术栈

- **框架**: Vue 3 + TypeScript + Vite
- **UI 库**: Naive UI
- **状态管理**: Pinia
- **路由**: Vue Router
- **HTTP**: Axios (拦截器注入 Token)

## 快速开始

```bash
# 安装依赖
pnpm install

# 开发模式
pnpm dev          # http://localhost:3001

# 生产构建
pnpm build        # 输出到 dist/
```

管理员初始账号：`admin` / `admin123`

## 项目结构

```
admin-frontend/
├── src/
│   ├── views/                # 页面视图
│   │   ├── LoginView.vue     # 管理员登录
│   │   ├── DashboardView.vue # 数据看板
│   │   ├── UsersView.vue     # 学员管理
│   │   ├── UserDetailView.vue# 学员详情
│   │   ├── ApprovalView.vue  # 审批管理
│   │   ├── KnowledgeProgressView.vue  # 知识图谱进度（全体学员掌握情况）
│   │   └── SettingsView.vue  # 系统设置
│   ├── api/                  # API 请求封装
│   │   ├── request.ts        # Axios 实例 + 拦截器
│   │   ├── auth.ts           # 认证接口
│   │   ├── dashboard.ts      # 数据看板接口
│   │   ├── users.ts          # 学员管理接口
│   │   ├── approval.ts       # 审批管理接口
│   │   ├── knowledge.ts      # 知识库管理接口
│   │   └── knowledgeProgress.ts  # 知识图谱进度接口
│   ├── stores/               # Pinia 状态管理
│   │   ├── auth.ts           # 认证状态
│   │   └── admin.ts          # UI 状态（侧边栏折叠等）
│   ├── router/
│   │   └── index.ts          # 路由配置 + 守卫
│   ├── layouts/
│   │   └── AdminLayout.vue   # 管理后台布局（侧边栏+顶栏）
│   ├── utils/
│   │   └── format.ts         # 格式化 + 枚举中文映射
│   └── types/
│       └── admin.ts          # TypeScript 类型定义
├── index.html
├── vite.config.ts
├── tsconfig.json
└── package.json
```

## 功能模块

| 模块 | 路由 | 功能 |
|------|------|------|
| 数据看板 | `/` | 统计卡片、知识点分布表、学习趋势、学历/等级分布 |
| 学员管理 | `/users` | 搜索/筛选/分页列表，点击查看详情 |
| 学员详情 | `/users/:id` | 基本信息、学习路径、知识掌握、答题记录、审批历史 |
| 审批管理 | `/approval` | 左右双栏：待审批列表 + 学情查看 + 通过/拒绝操作 |
| 知识图谱进度 | `/knowledge-progress` | 全体学员知识掌握概览、单个学员节点进度详情 |
| 系统设置 | `/settings` | 知识库目录树、文件查看/编辑/新建/删除、向量索引重建 |

## 路由配置

| 路由 | 组件 | 权限 |
|------|------|------|
| `/login` | LoginView | 公开 |
| `/` | DashboardView | 需登录 + admin 角色 |
| `/users` | UsersView | 需登录 + admin 角色 |
| `/users/:id` | UserDetailView | 需登录 + admin 角色 |
| `/approval` | ApprovalView | 需登录 + admin 角色 |
| `/knowledge-progress` | KnowledgeProgressView | 需登录 + admin 角色 |
| `/settings` | SettingsView | 需登录 + admin 角色 |

路由守卫 (`router/index.ts`) 会检查：
1. Token 是否存在 → 未登录跳转 `/login`
2. 角色是否为 `admin` → 非管理员提示并跳转

## 枚举中文化

`utils/format.ts` 提供以下映射：

| 映射 | 值 |
|------|-----|
| LEVEL_MAP | beginner→初级, intermediate→中级, advanced→高级, expert→专家 |
| LEARNING_STYLE_MAP | visual→视觉型, theory→理论型, practice→实践型 |
| APPROVAL_STATUS_MAP | none→未申请, pending→审批中, approved→已批准, rejected→未通过 |
