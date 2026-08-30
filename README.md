# 领域知识个性化生成与多智能体协同决策系统

## 项目简介

面向垂直领域（CNC 数控加工、Python 数据分析）的个性化学习平台，采用 **6 Agent 协同架构**，通过 LangGraph 有向图编排、双视角审核纠偏、RAG 知识溯源、苏格拉底式追问等策略，为不同水平的学习者自动生成定制化学习资源，形成「诊断 → 学习 → 考核 → 推进」的完整学习闭环。配套 B 端管理后台，支持学员管理、机台使用审批、知识库管理。

### 核心指标

| 指标 | 目标 | 验证方法 |
|------|------|----------|
| 知识谬误率 | < 5% | RAG 知识库逐条比对，持久化快照 |
| 难度匹配准确率 | >= 85% | 学情诊断 + 4 级难度自适应 |
| 知识点覆盖率 | >= 90% | RAG 检索 + 关键词模糊匹配 |

### 系统架构

```
┌─────────────────────────────────────────────────────┐
│                    C 端学习平台 (Nuxt 3)               │
│  首页 │ 学情画像 │ Agent协同 │ 学习报告 │ 答题考核      │
├─────────────────────────────────────────────────────┤
│                  B 端管理后台 (Vue 3 + Naive UI)        │
│  数据看板 │ 学员管理 │ 审批管理 │ 系统设置               │
├─────────────────────────────────────────────────────┤
│                  API 网关层 (FastAPI)                  │
│  认证 │ 画像 │ 生成 │ 反馈 │ 学习路径 │ 试题 │ 管理接口  │
├─────────────────────────────────────────────────────┤
│              多 Agent 协同编排层 (LangGraph)             │
│  学情诊断 → 路径规划 → 知识生成 → 审核纠偏 → 试题生成     │
│                       ↕ 决策调度 ↕                     │
├─────────────────────────────────────────────────────┤
│                     基础设施层                         │
│   LLM (OpenAI 兼容)  │  ChromaDB  │  MySQL 8.0  │  Redis │
└─────────────────────────────────────────────────────┘
```

---

## 环境要求

| 软件 | 版本 | 说明 |
|------|------|----------|
| uv | 0.12+ | Python 环境与依赖管理（自动提供 Python 3.11+，替代 conda/pip） |
| Node.js | 18+ | 前端构建环境 |
| pnpm | 8+ | 包管理器 |
| MySQL | 8.0+ | 关系数据库 |
| Redis | 7.0+ | 缓存与会话（不可用时自动降级） |

### API Key

| 服务 | 用途 | 获取地址 |
|------|------|----------|
| LLM（OpenAI 兼容） | 大语言模型 | 见下方「切换 LLM 平台」章节 |
| 嵌入模型（OpenAI 兼容） | 文本嵌入 | 默认使用阿里云 DashScope |

默认配置使用 DeepSeek（LLM）和阿里云 DashScope（嵌入），可在 `.env` 中替换为任意 OpenAI 兼容平台（Kimi、GLM、MiniMax 等）。

---

## 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd Agent
```

### 2. 后端部署

```bash
cd backend

# 安装依赖（自动创建 .venv，版本由 uv.lock 锁定）
uv sync

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY 和 EMBEDDING_API_KEY
# 可选：修改 LLM_BASE_URL 和 LLM_MODEL 切换其他模型平台

# 一键初始化（创建管理员 + 构建知识库索引）
uv run python setup.py

# 启动服务
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000/docs 查看 API 文档。

### 3. C 端（学员端）部署

```bash
cd frontend
pnpm install
pnpm dev          # http://localhost:3000
```

### 4. B 端（管理后台）部署

```bash
cd admin-frontend
pnpm install
pnpm dev          # http://localhost:5173
```

管理员初始账号：`admin` / `admin123`

---

## 项目结构

```
Agent/
├── backend/                     # 后端 FastAPI 服务
│   ├── app/
│   │   ├── agents/              # 6 个 AI Agent（学情诊断 / 路径规划 / 知识生成 / 审核纠偏 / 试题生成 / 决策调度）
│   │   ├── graph/               # LangGraph 工作流编排
│   │   ├── knowledge/           # RAG 知识库（ChromaDB）
│   │   ├── metrics/             # 谬误检测 + 指标计算
│   │   ├── mock/                # Mock 模式（MOCK_MODE=true 时使用）
│   │   ├── api/                 # API 路由
│   │   │   └── admin/           # B 端管理接口
│   │   ├── models/              # SQLAlchemy 数据模型
│   │   ├── core/                # 配置 / 认证 / 存储 / LLM
│   │   └── utils/               # 工具函数
│   ├── tests/                   # 单元测试
│   ├── main.py                  # 应用入口
│   ├── setup.py                 # 一键部署初始化
│   ├── pyproject.toml           # 依赖清单（uv 管理）
│   ├── uv.lock                  # 依赖锁定
│   └── .env.example
├── frontend/                    # C 端 Nuxt 3 学习平台
│   ├── pages/                   # 页面路由（含知识图谱、答题练习、学习报告等）
│   ├── components/              # Vue 组件（Agent 可视化、雷达图、报告图表等）
│   ├── composables/             # 组合式函数（API / 认证 / WebSocket / 学习路径）
│   ├── utils/                   # 工具函数
│   └── nuxt.config.ts
├── admin-frontend/              # B 端 Vue 3 管理后台
│   ├── src/
│   │   ├── views/               # 页面视图（含知识图谱进度）
│   │   ├── api/                 # API 请求封装
│   │   ├── stores/              # Pinia 状态管理
│   │   ├── router/              # 路由配置
│   │   ├── layouts/             # 布局组件
│   │   └── utils/               # 工具函数
│   └── vite.config.ts
├── knowledge-base/              # 知识库 Markdown 文档（50+ 篇 CNC 领域文档）
│   └── cnc_domain/
│       ├── theory/              # 理论知识（数控基础 / 坐标系 / 切削理论 / G 代码等）
│       ├── practice/            # 实践操作（刀具选择 / 装夹 / CAM / 测量等）
│       └── standards/           # 标准规范（GB / ISO / 安全规程 / 质量控制等）
├── data/                        # 数据文件
└── tests/                       # 顶层测试脚本
```

---

## 管理员功能（B 端）

| 模块 | 功能 |
|------|------|
| 数据看板 | 学员总数、待审批数、今日活跃、知识点分布、学习趋势 |
| 学员管理 | 列表搜索/筛选/分页、详情查看（学习路径/知识掌握/答题记录/审批历史） |
| 审批管理 | 机台使用申请审批（通过/拒绝 + 理由）、审批日志 |
| 系统设置 | 知识库文件浏览/编辑/新建/删除、向量索引重建 |

---

## 测试

```bash
cd backend

# 运行全部测试
uv run pytest tests/ -v

# 特定模块
uv run pytest tests/test_agents.py -v
uv run pytest tests/test_ablation.py -v
uv run pytest tests/test_redis_store.py -v
uv run pytest tests/test_main.py -v
```

---

## 常见问题

### Redis 连接失败
系统自动降级为内存存储，单用户不受影响。多用户部署请确保 Redis 已启动。

### 知识库索引更新
修改知识库文档后，重新执行 `python setup.py`，或在 B 端「系统设置」中点击「重建索引」。

### MySQL 连接失败
确保 `.env` 中数据库配置正确，或 MySQL 服务已启动。

### 切换 LLM 平台

系统通过 OpenAI 兼容接口调用 LLM，支持 DeepSeek、Kimi（月之暗面）、GLM（智谱）、Qwen（通义千问）、MiniMax 等任意平台。只需修改 `.env` 中以下三个变量：

```env
LLM_BASE_URL=https://api.moonshot.cn/v1   # 平台 API 地址
LLM_MODEL=moonshot-v1-8k                    # 模型名称
LLM_API_KEY=你的 API Key
```

### Mock 模式

开发调试时，可在 `.env` 中启用 Mock 模式，所有 LLM/嵌入调用返回本地模拟数据，不消耗 API 额度：

```env
MOCK_MODE=true
```

---

## 安全说明（演示默认 vs 生产部署）

本项目为参赛演示定位，安全配置以「开箱即用」为优先，以下默认值仅限本地/演示环境：

- 管理员初始账号 `admin / admin123`（README 已公开标注，便于评审登录；可通过 `ADMIN_USERNAME` / `ADMIN_PASSWORD` 环境变量在初始化时覆盖）
- JWT 密钥使用代码内默认值；启动时输出提醒日志
- `.env.docker` 中的 `change-me-in-production-please` 为占位符，非真实密钥；各 API Key 留空并默认启用 `MOCK_MODE`

若用于真实生产部署，请完成以下检查清单：

1. 设置 `ENVIRONMENT=production` 并更换强随机 `JWT_SECRET_KEY`（未更换时系统将拒绝启动）
2. 通过 `ADMIN_PASSWORD` 环境变量初始化管理员强密码
3. 配置真实 `LLM_API_KEY` / `EMBEDDING_API_KEY`，关闭 `MOCK_MODE`
4. 为 MySQL / Redis 设置强密码，收敛 `CORS_ORIGINS` 到实际域名，启用 HTTPS 反向代理
5. 建议补充（演示场景未实现）：JWT 刷新/滑动过期、密码强度策略、管理员首登强制改密、限流阈值按业务调整

---

## License

MIT
