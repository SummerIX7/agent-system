# 领域知识个性化生成与多智能体协同决策系统

## 项目简介

本项目面向垂直领域（CNC 数控加工、Python 数据分析）的个性化学习需求，采用 **5 Agent 协同架构**，通过 LangGraph 有向图编排、双视角审核纠偏、RAG 知识溯源、苏格拉底式追问等策略，为不同水平的学习者自动生成定制化学习资源，并以学习路径节点为驱动形成「诊断 → 学习 → 考核 → 推进」的完整闭环。

### 核心指标

| 指标 | 目标 | 验证方法 |
|------|------|----------|
| 知识谬误率 | < 5% | 独立事实核查 — RAG 知识库逐条比对（一次性计算，持久化快照） |
| 难度匹配准确率 | >= 85% | 学情诊断 Agent + 4 级难度自适应 |
| 知识点覆盖率 | >= 90% | RAG 检索 + 关键词模糊匹配 |

### 技术架构

```
+-----------------------------------------------------------+
|                    前端展示层 (Nuxt 3)                       |
| 首页 | 学情画像 | Agent协同 | 分析报告 | 资源展示 | 历史记录    |
+-----------------------------------------------------------+
|                  API 网关层 (FastAPI)                        |
+-----------------------------------------------------------+
|             多 Agent 协同编排层 (LangGraph)                    |
| 学情诊断 -> 路径规划 -> 知识生成 -> 审核纠偏 -> 决策调度           |
+-----------------------------------------------------------+
|                    基础设施层                                |
| LLM (DeepSeek) | ChromaDB | MySQL 8.0 | Redis 7.0           |
+-----------------------------------------------------------+
```

### Agent 角色定义

| Agent | 职责 | 核心能力 |
|-------|------|----------|
| 学情诊断 Agent | 构建学习者画像，定位知识盲区 | 画像建模、能力评估、盲区检测 |
| 路径规划 Agent | 生成/调整分阶段学习路径 | 路径规划、动态调整 |
| 知识生成 Agent | 依托 RAG 知识库生成个性化资源（讲义/指导/案例） | 检索增强、知识溯源、多形态生成 |
| 审核纠偏 Agent | 双视角审查+自动修正（合并原预审+辩论功能） | 学术审查+工业实践双视角、严重度评分、自动修正验证 |
| 试题生成 Agent | 按难度生成分阶试题（基础+提升） | 选择题/判断题/实操题 |
| 决策调度 Agent | 流程编排、审核不通过时触发重生成 | 流程编排、难度自适应、节点推进 |

### 学习流程

```
Agent 协同（首次）:
  -> 学情分析 -> 路径规划（生成 N 个节点）
  -> 生成节点 1 资源（讲义+指导+案例）+ 审核
  -> 生成节点 1 试题（基础+提升）
  -> 完成后进入分析报告

分析报告 -> 查看节点 1 资源 -> 基础考核 -> 提升考核 -> 更新学习路径
  -> 推进到节点 2 -> 生成节点 2 资源 -> 生成节点 2 试题
  -> ... -> 所有节点完成
```

---

## 环境要求

### 最低配置

| 软件 | 版本要求 | 说明 |
|------|----------|------|
| Python | 3.11+ | 后端运行环境 |
| Node.js | 18+ | 前端构建环境 |
| pnpm | 8+ | 前端包管理器（推荐） |
| MySQL | 8.0+ | 关系数据库 |
| Redis | 7.0+ | 缓存与会话管理（不可用时自动降级为内存存储） |
| Git | 2.0+ | 版本管理 |

### API Key 要求

| 服务 | 用途 | 获取地址 |
|------|------|----------|
| DeepSeek API | 大语言模型 | https://platform.deepseek.com |
| 阿里云 DashScope | 文本嵌入模型 | https://dashscope.aliyun.com |

---

## 快速开始

### 一、克隆项目

```bash
git clone <repository-url>
cd Agent/agent-system
```

### 二、后端部署

#### 2.1 创建 Python 虚拟环境

```bash
cd backend

# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

#### 2.2 安装依赖

```bash
pip install -r requirements.txt
```

#### 2.3 配置环境变量

```bash
# 复制环境变量模板
copy .env.example .env    # Windows
cp .env.example .env      # macOS / Linux
```

编辑 `.env` 文件，填入必要的配置：

```bash
# ---- 必须配置 ----

# LLM API Key（DeepSeek）
LLM_API_KEY=sk-your-deepseek-api-key

# 嵌入模型 API Key（阿里云 DashScope）
EMBEDDING_API_KEY=sk-your-dashscope-api-key

# ---- 可选配置 ----

# MySQL 数据库（不配置则使用默认 localhost）
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your-password
MYSQL_DATABASE=agent_system

# Redis（不配置则自动降级为内存存储）
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=          # 本地开发通常不需要密码
```

#### 2.4 构建知识库索引

在首次启动或更新知识库文档后，需要重新构建向量索引：

```bash
cd backend
python build_index.py
```

执行成功后会在 `backend/chroma_db/` 下生成向量索引文件。

#### 2.5 创建数据库表

如果使用 MySQL，确保数据库已创建：

```sql
CREATE DATABASE IF NOT EXISTS agent_system DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

应用启动时会自动通过 SQLAlchemy `Base.metadata.create_all` 创建表结构。也可以手动执行 Alembic 迁移：

```bash
cd backend
alembic upgrade head
```

#### 2.6 启动后端服务

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

启动成功后访问：
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

### 三、前端部署

#### 3.1 安装依赖

```bash
cd frontend

# 使用 pnpm（推荐）
pnpm install

# 或使用 npm
npm install
```

#### 3.2 配置 API 地址

编辑 `frontend/nuxt.config.ts`，确保 API 地址指向后端：

```typescript
runtimeConfig: {
  public: {
    apiBase: 'http://localhost:8000',   // 后端 API 地址
    wsBase: 'ws://localhost:8000',       // WebSocket 地址
  },
},
```

#### 3.3 启动前端开发服务器

```bash
pnpm dev        # http://localhost:3000
# 或
npm run dev
```

#### 3.4 生产构建

```bash
pnpm build
# 构建产物在 .output/ 目录
```

### 四、验证安装

1. 打开浏览器访问 http://localhost:3000
2. 点击「注册」创建账号
3. 点击「学习者画像」填写学历、专业等信息并提交
4. 点击「Agent 协同」触发资源生成，等待工作流完成
5. 点击「查看学习报告」进入分析报告，查看学习路径
6. 依次体验：资源学习 -> 基础考核 -> 提升考核 -> 推进节点 -> 下一节点学习

---

## 项目结构

```
agent-system/
+-- backend/
|   +-- app/
|   |   +-- agents/              # Agent 实现
|   |   |   +-- base.py          # Agent 基类（LLM 调用、知识库检索）
|   |   |   +-- diagnosis.py     # 学情诊断 Agent
|   |   |   +-- path_planner.py  # 路径规划 Agent
|   |   |   +-- generation.py    # 知识生成 Agent
|   |   |   +-- review.py        # 审核纠偏 Agent（双视角审查+修正）
|   |   |   +-- debate.py        # 辩论管理器（已合并到 review，保留作为备用）
|   |   |   +-- judge.py         # 裁判 Agent（已合并到 review，保留作为备用）
|   |   |   +-- question_generator.py  # 试题生成 Agent
|   |   |   +-- orchestrator.py  # 决策调度 Agent
|   |   +-- graph/               # LangGraph 工作流
|   |   |   +-- state.py         # 状态定义
|   |   |   +-- workflow.py      # 5 节点协同工作流图
|   |   +-- knowledge/           # 知识库模块
|   |   |   +-- loader.py        # 文档加载
|   |   |   +-- embedder.py      # 向量化
|   |   |   +-- retriever.py     # 检索器
|   |   +-- metrics/             # 指标计算
|   |   |   +-- hallucination_checker.py  # 独立谬误检测
|   |   |   +-- report_builder.py         # 报告指标快照计算
|   |   +-- api/                 # API 路由
|   |   |   +-- auth.py          # 用户认证
|   |   |   +-- profile.py       # 学习者画像
|   |   |   +-- generation.py    # 资源生成
|   |   |   +-- feedback.py      # 答题反馈（含苏格拉底追问）
|   |   |   +-- questions.py     # 分阶试题生成与缓存
|   |   |   +-- learning_path.py # 学习路径管理、节点推进、按需生成
|   |   |   +-- visualization.py # 可视化数据（读 report_cache 快照）
|   |   |   +-- ws.py            # WebSocket（Agent 状态实时推送）
|   |   +-- models/              # 数据模型
|   |   |   +-- database.py      # 数据库连接
|   |   |   +-- user.py          # 用户模型
|   |   |   +-- learner.py       # 学习者模型（含 report_cache 快照）
|   |   |   +-- resource.py      # 资源模型
|   |   |   +-- agent_state.py   # Agent 日志 + 反馈记录模型
|   |   |   +-- schemas.py       # Pydantic Schema
|   |   +-- core/                # 核心模块
|   |       +-- config.py        # 配置管理
|   |       +-- llm.py           # LLM 调用封装
|   |       +-- auth.py          # JWT 认证
|   |       +-- store.py         # Redis 存储层（含 DB 回填）
|   |       +-- domains.py       # 多领域配置
|   +-- alembic/                 # 数据库迁移
|   +-- chroma_db/               # 向量索引（自动生成）
|   +-- tests/                   # 单元测试（49 个测试用例）
|   +-- main.py                  # 应用入口
|   +-- build_index.py           # 索引构建脚本
|   +-- requirements.txt         # Python 依赖
|   +-- .env.example             # 环境变量模板
+-- frontend/
|   +-- pages/                   # 页面路由
|   |   +-- index.vue            # 首页
|   |   +-- profile.vue          # 学习者画像
|   |   +-- dashboard.vue        # 学情诊断
|   |   +-- workflow.vue         # Agent 协同
|   |   +-- report.vue           # 分析报告（学习路径主视图）
|   |   +-- resources.vue        # 资源展示
|   |   +-- practice.vue         # 分阶答题考核
|   |   +-- history.vue          # 历史记录
|   |   +-- login.vue            # 登录
|   |   +-- register.vue         # 注册
|   +-- components/              # Vue 组件
|   |   +-- MarkdownRenderer.vue # Markdown 渲染
|   |   +-- dashboard/           # 仪表盘组件（雷达图）
|   |   +-- agent-view/          # Agent 可视化（流程图）
|   |   +-- report/              # 报告组件（匹配曲线）
|   +-- composables/             # 组合式函数
|   |   +-- useApi.ts            # API 封装
|   |   +-- useAuth.ts           # 认证管理
|   |   +-- useSession.ts        # 会话管理（localStorage 持久化）
|   |   +-- useLearningPath.ts   # 学习路径状态管理
|   |   +-- useAgentWebSocket.ts # WebSocket 连接
|   +-- types/api.ts             # TypeScript 类型
|   +-- layouts/default.vue      # 默认布局
|   +-- assets/css/main.css      # 设计系统
|   +-- nuxt.config.ts           # Nuxt 配置
|   +-- package.json
+-- knowledge-base/
|   +-- cnc_domain/              # CNC 数控加工领域知识文档
|       +-- theory/              # 理论知识
|       +-- practice/            # 实践操作
|       +-- standards/           # 标准规范
+-- docs/
|   +--  系统流程改进计划.md
+-- README.md
```

---

## API 文档

启动后端后访问 http://localhost:8000/docs 查看 Swagger 交互式文档。

### 主要接口

#### 认证
| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/auth/register` | 否 | 用户注册 |
| POST | `/api/auth/login` | 否 | 用户登录 |
| GET | `/api/auth/me` | 是 | 获取当前用户信息 |

#### 学习者画像
| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/profile/` | 是 | 提交学习者画像（触发学情诊断） |
| GET | `/api/profile/me` | 是 | 获取当前用户画像 |

#### 资源生成
| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/generate` | 否 | 触发 Agent 工作流生成资源 |
| GET | `/api/resources/{session_id}` | 否 | 获取生成资源（支持 `?stage=N` 过滤） |

#### 学习路径管理
| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/api/learning-path/{session_id}` | 否 | 获取学习路径及节点状态 |
| GET | `/api/learning-path/{session_id}/current-node` | 否 | 获取当前节点信息 |
| POST | `/api/learning-path/{session_id}/advance` | 否 | 推进到下一节点 |
| POST | `/api/learning-path/{session_id}/generate-node-content` | 否 | 按需生成指定节点资源+试题 |

#### 分阶试题
| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/questions/generate/{session_id}` | 是 | 生成分阶试题（基础+提升） |
| GET | `/api/questions/set/{session_id}/{level}` | 是 | 获取指定等级试题（支持 `?stage=N`） |
| GET | `/api/questions/{session_id}` | 是 | 获取动态生成的试题（含缓存） |

#### 答题反馈
| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/feedback/` | 否 | 提交答题反馈（含苏格拉底追问） |
| POST | `/api/feedback/practical` | 否 | 提交实操题批改 |

#### 可视化与历史
| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/api/visualization/{session_id}` | 否 | 获取报告数据（读 DB 快照） |
| GET | `/api/history/{learner_id}` | 否 | 获取学习历史 |
| GET | `/api/trace/{session_id}` | 否 | 获取工作流追踪数据 |

#### 其他
| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| WS | `/ws/agent-status/{session_id}` | 否 | Agent 状态实时推送 |
| GET | `/health` | 否 | 健康检查（含 Redis 状态） |

---

## 数据库设计

### 核心表

| 表 | 用途 | 关键字段 |
|------|------|----------|
| `users` | 用户账号 | id, username, password_hash, email |
| `learners` | 学习者画像 | knowledge_points(JSON), blind_spots(JSON), learning_path(JSON), report_cache(JSON) |
| `resources` | 生成资源 | resource_type(lecture/guide/project), content, stage, review_score, review_passed |
| `feedback_records` | 答题反馈 | question, user_answer, correct_answer, is_correct, stage, test_level |
| `agent_logs` | Agent 执行日志 | agent_name, status, message, progress |

### 数据持久化

- **用户画像、学习路径、资源内容、答题记录、报告指标**全部持久化到 MySQL
- Session store（Redis/内存）仅作为热缓存加速读写，重启后自动从 DB 回填
- 用户退出再登录、重启服务、跨设备访问，数据完全一致

---

## 测试

### 运行所有测试

```bash
cd backend

# 运行全部测试
python -m pytest tests/ -v

# 运行特定测试模块
python -m pytest tests/test_agents.py -v             # Agent 核心逻辑
python -m pytest tests/test_domain_migration.py -v    # 领域迁移性
python -m pytest tests/test_ablation.py -v            # 消融实验
python -m pytest tests/test_redis_store.py -v         # Redis 存储
python -m pytest tests/test_main.py -v                # API 端点
```

### 验收脚本

```bash
cd backend

# 领域迁移性验收
python verify_domain_migration.py

# 消融实验验收
python verify_ablation.py
```

---

## Docker 部署（生产环境）

### docker-compose.yml

在项目根目录创建：

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: agent-redis
    command: redis-server --requirepass ${REDIS_PASSWORD} --appendonly yes
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: always

  backend:
    build: ./agent-system/backend
    container_name: agent-backend
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - redis
    restart: always

  frontend:
    build: ./agent-system/frontend
    container_name: agent-frontend
    ports:
      - "3000:3000"
    restart: always

volumes:
  redis_data:
```

### 启动

```bash
# 确保 .env 文件配置正确
docker-compose up -d
```

---

## 常见问题

### Q1: 启动时报 Redis 连接失败

Redis 不可用时系统会自动降级为内存存储，不影响单用户使用。如果需要多用户部署，请确保 Redis 已启动：

```bash
# 检查 Redis 状态
redis-cli ping

# 启动 Redis
redis-server          # Linux/macOS
redis-server.exe      # Windows
```

### Q2: 知识库索引需要更新

修改或新增知识库文档后，需要重新构建索引：

```bash
cd backend
python build_index.py
```

### Q3: MySQL 连接失败

如果不需要 MySQL，系统可以运行但在数据持久化方面受限。确保 `.env` 中的 MySQL 配置正确，或确保 MySQL 服务已启动：

```bash
# Windows
net start MySQL80

# Linux
sudo systemctl start mysql
```

### Q4: LLM API 调用超时

检查网络连接和 API Key 配置：

```bash
# 测试 API Key
curl https://api.deepseek.com/v1/models \
  -H "Authorization: Bearer $LLM_API_KEY"
```

---

## 比赛信息

- 赛事：挑战杯"揭榜挂帅"专项赛
- 项目编号：XH-202630
- 发榜单位：上海云之脑智能科技有限公司

---

## License

MIT
