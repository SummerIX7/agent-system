# 后端服务

基于 FastAPI 的多智能体协同决策系统后端，提供 REST API、WebSocket、LangGraph 工作流编排、RAG 知识库检索。

## 技术栈

- **框架**: FastAPI + Uvicorn
- **数据库**: MySQL 8.0 + SQLAlchemy (async)
- **缓存**: Redis 7.0（自动降级为内存存储）
- **向量索引**: ChromaDB
- **工作流**: LangGraph
- **LLM**: OpenAI 兼容接口（支持 DeepSeek / Kimi / GLM / Qwen / MiniMax 等任意平台）

## 快速开始

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate     # Linux / macOS
venv\Scripts\activate        # Windows

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env，至少填入:
#   LLM_API_KEY=sk-your-key
#   EMBEDDING_API_KEY=sk-your-key
# 可选：修改 LLM_BASE_URL 和 LLM_MODEL 切换其他模型平台

# 4. 一键初始化（创建管理员 + 构建知识库索引）
python setup.py

# 5. 启动
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

启动后访问:
- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

## 项目结构

```
backend/
├── app/
│   ├── agents/              # AI Agent 实现
│   │   ├── base.py          # Agent 基类
│   │   ├── diagnosis.py     # 学情诊断
│   │   ├── path_planner.py  # 路径规划
│   │   ├── generation.py    # 知识生成
│   │   ├── review.py        # 审核纠偏（双视角审查 + 修正）
│   │   ├── debate.py        # 辩论管理器（备用）
│   │   ├── judge.py         # 独立裁判 Agent（备用）
│   │   ├── question_generator.py  # 试题生成
│   │   └── orchestrator.py  # 决策调度
│   ├── graph/               # LangGraph 工作流
│   │   ├── state.py         # 状态定义
│   │   └── workflow.py      # 多节点协同编排
│   ├── knowledge/           # RAG 知识库
│   │   ├── loader.py        # 文档加载
│   │   ├── embedder.py      # 向量化
│   │   └── retriever.py     # 检索器
│   ├── metrics/             # 质量指标
│   │   ├── hallucination_checker.py  # 谬误检测
│   │   └── report_builder.py         # 报告快照
│   ├── mock/                # Mock 模式（MOCK_MODE=true 时使用，不调用外部 API）
│   │   ├── llm.py           # 模拟 LLM
│   │   ├── embeddings.py    # 模拟嵌入
│   │   ├── knowledge.py     # 模拟检索器
│   │   └── responses.py     # 预设响应数据
│   ├── api/                 # REST API 路由
│   │   ├── auth.py          # 认证
│   │   ├── profile.py       # 学习者画像
│   │   ├── generation.py    # 资源生成
│   │   ├── feedback.py      # 答题反馈
│   │   ├── questions.py     # 分阶试题
│   │   ├── learning_path.py # 学习路径与节点推进
│   │   ├── visualization.py # 可视化数据
│   │   ├── knowledge_graph.py  # 知识图谱（树状结构 + 学习进度）
│   │   ├── domains.py       # 领域配置
│   │   ├── career_tracks.py # 职业路径配置
│   │   ├── ws.py            # WebSocket
│   │   └── admin/           # B 端管理接口
│   │       ├── router.py    # 路由汇总
│   │       ├── dashboard.py # 数据看板
│   │       ├── users.py     # 学员管理
│   │       ├── approval.py  # 审批管理
│   │       └── knowledge.py # 知识库管理
│   ├── models/              # 数据模型
│   │   ├── database.py      # 数据库连接
│   │   ├── user.py          # 用户
│   │   ├── learner.py       # 学习者画像
│   │   ├── resource.py      # 学习资源
│   │   ├── agent_state.py   # Agent 日志 + 答题记录
│   │   ├── approval_log.py  # 审批日志
│   │   └── schemas.py       # Pydantic Schema
│   ├── core/                # 核心模块
│   │   ├── config.py        # 配置管理
│   │   ├── auth.py          # JWT 认证
│   │   ├── llm.py           # LLM 调用封装（OpenAI 兼容）
│   │   ├── store.py         # Redis 存储层
│   │   ├── domains.py       # 多领域配置
│   │   ├── career_tracks.py # 职业路径配置
│   │   └── question_persistence.py  # 试题持久化
│   └── utils/               # 工具函数
│       └── db_helpers.py    # 数据库辅助
├── alembic/                 # 数据库迁移脚本
├── tests/                   # 单元测试
├── main.py                  # 应用入口
├── setup.py                 # 一键部署初始化
├── requirements.txt
└── .env.example
```

## 初始化脚本

```bash
python setup.py
```
依次执行:
1. 创建管理员账号 (`admin` / `admin123`)，已存在则跳过
2. 构建 ChromaDB 知识库向量索引

## 数据库迁移

应用启动时自动建表。也可手动执行：

```bash
alembic upgrade head
```

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| LLM_API_KEY | ✅ | LLM API Key（支持任意 OpenAI 兼容平台） |
| LLM_BASE_URL | - | LLM API 地址，默认 DeepSeek |
| LLM_MODEL | - | LLM 模型名，默认 deepseek-chat |
| EMBEDDING_API_KEY | ✅ | 嵌入模型 API Key |
| EMBEDDING_BASE_URL | - | 嵌入模型 API 地址，默认 DashScope |
| EMBEDDING_MODEL | - | 嵌入模型名，默认 text-embedding-v3 |
| MYSQL_HOST | - | 默认 localhost |
| MYSQL_PORT | - | 默认 3306 |
| MYSQL_USER | - | 默认 root |
| MOCK_MODE | - | 设为 true 启用 Mock 模式，不调用外部 API |

## 测试

```bash
python -m pytest tests/ -v
```
