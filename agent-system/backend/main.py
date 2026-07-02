import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, domains, feedback, generation, learning_path, profile, questions, visualization, ws
from app.core.config import get_settings
from app.core.store import check_redis_health
from app.models.database import engine, Base
# 导入所有模型，确保被 Base 注册
from app.models.user import User
from app.models.learner import Learner
from app.models.resource import Resource
from app.models.agent_state import AgentLog, FeedbackRecord

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # ── 启动时 ──
    # 1. 清除配置缓存，确保加载最新 .env 和 config.py
    get_settings.cache_clear()

    # 1½. 清除嵌入模型缓存（Mock 模式切换时确保重新判断）
    import app.knowledge.embedder as embedder_mod
    embedder_mod.get_embeddings.cache_clear()

    # 2. 重置知识库检索器单例，避免使用旧索引
    import app.knowledge.retriever as retriever_mod
    retriever_mod._retriever = None

    # 3. 检查 Redis 连接状态
    health = check_redis_health()
    if health["status"] == "degraded":
        logger.warning(
            "️ Redis 不可用，已降级为内存存储。"
            "多用户部署时请确保 Redis 已启动且配置正确。"
        )
        print("[启动] ️ Redis 不可用，已降级为内存存储")
    else:
        logger.info(f" Redis 连接正常: {health}")
        print(f"[启动]  Redis 连接正常: {health}")

    # 3½. 打印 Mock 模式状态
    settings = get_settings()
    if settings.MOCK_MODE:
        print("[启动] 🟡 MOCK 模式已启用 — 所有 LLM / 嵌入 / 知识库调用使用本地模拟数据")
    else:
        print("[启动] 🟢 真实 API 模式 — LLM: {}({}), 嵌入: {}".format(
            settings.LLM_PROVIDER, settings.LLM_MODEL, settings.EMBEDDING_MODEL))
    print("[启动] 配置已刷新")

    # 4. 创建数据库表（如果不存在）
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[启动] 数据库表已就绪")

    yield

    # ── 关闭时 ──
    await engine.dispose()


settings = get_settings()

app = FastAPI(
    title="领域知识个性化生成与多智能体协同决策系统",
    description="通过多个 AI Agent 协同工作，实现个性化学习资源生成",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载路由
app.include_router(auth.router)
app.include_router(domains.router)
app.include_router(profile.router)
app.include_router(generation.router)
app.include_router(feedback.router)
app.include_router(learning_path.router)
app.include_router(visualization.router)
app.include_router(questions.router)
app.include_router(ws.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理，防止未捕获异常返回 500 HTML"""
    return JSONResponse(
        status_code=500,
        content={"detail": f"服务器内部错误: {type(exc).__name__}: {str(exc)}"},
    )


@app.get("/")
async def root():
    return {"message": "多智能体协同决策系统 API", "version": "1.0.0"}


@app.get("/health")
async def health():
    """健康检查端点，包含 Redis 和 Mock 模式状态"""
    settings = get_settings()
    return {
        "status": "ok",
        "mock_mode": settings.MOCK_MODE,
        "llm_provider": "mock" if settings.MOCK_MODE else settings.LLM_PROVIDER,
        "llm_model": "mock" if settings.MOCK_MODE else settings.LLM_MODEL,
        "redis": check_redis_health(),
    }

@app.get("/mock-status")
async def mock_status():
    """查询当前 Mock 模式状态"""
    settings = get_settings()
    return {
        "mock_mode": settings.MOCK_MODE,
        "description": (
            "🟡 Mock 模式：所有 LLM/嵌入/知识库调用返回本地模拟数据，不访问外部 API。"
            if settings.MOCK_MODE else
            "🟢 真实 API 模式：LLM 调用 {}, 嵌入调用 {}。".format(
                settings.LLM_PROVIDER, settings.EMBEDDING_MODEL)
        ),
        "how_to_switch": (
            "将 .env 中 MOCK_MODE 改为 true，然后重启服务即可切换到 Mock 模式。"
            if not settings.MOCK_MODE else
            "将 .env 中 MOCK_MODE 改为 false，然后重启服务即可切换到真实 API 模式。"
        ),
    }
