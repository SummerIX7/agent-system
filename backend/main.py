import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# 先初始化日志系统，避免其它模块 import 时用默认 logger
from app.core.logging_config import (
    bind_request_context,
    reset_request_context,
    setup_logging,
)

setup_logging()

from app.api import auth, career_tracks, domains, feedback, generation, health, knowledge_graph, learning_path, profile, questions, visualization, ws
from app.api.admin.router import router as admin_router
from app.core.config import DEFAULT_JWT_SECRET, get_settings
from app.core.store import check_redis_health
from app.models.database import engine, Base
# 导入所有模型，确保被 Base 注册
from app.models.user import User
from app.models.learner import Learner
from app.models.resource import Resource
from app.models.agent_state import AgentLog, FeedbackRecord
from app.models.approval_log import ApprovalLog

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
    else:
        logger.info("Redis 连接正常: %s", health)

    # 3½. 打印 Mock 模式状态
    settings = get_settings()
    if settings.MOCK_MODE:
        logger.info("🟡 MOCK 模式已启用 — 所有 LLM / 嵌入 / 知识库调用使用本地模拟数据")
    else:
        logger.info(
            "🟢 真实 API 模式 — LLM: %s(%s), 嵌入: %s",
            settings.LLM_PROVIDER, settings.LLM_MODEL, settings.EMBEDDING_MODEL,
        )
    logger.info("启动配置已刷新")

    # 3¾. 安全默认值提醒（ENVIRONMENT=production 时由 Settings 校验直接拒绝启动）
    if settings.JWT_SECRET_KEY == DEFAULT_JWT_SECRET:
        logger.warning(
            "JWT_SECRET_KEY 仍为演示默认值 — 仅限本地/演示使用。"
            "生产部署必须更换强随机密钥（ENVIRONMENT=production 将强制校验）。"
        )

    # 4. 创建数据库表（如果不存在）
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表已就绪")

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

# CORS 中间件（来源白名单见 config.CORS_ORIGINS；方法/头显式收敛）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """为每个请求分配 request_id：
    - 将 request_id 挂到 request.state，供异常处理器与业务日志引用
    - 通过 ContextVar 绑定到日志上下文，所有 logger.xxx() 自动带 rid=
    - 回写到响应头 X-Request-Id，方便前后端联合排查
    - 同时记录 HTTP 状态码到 /metrics 计数器
    """
    request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex
    request.state.request_id = request_id
    # 从 path 中尝试提取 session_id（形如 /ws/agent-status/{session_id} 或 query 参数），
    # 无匹配则保持 "-"。这里不引入正则以免误伤，交给业务代码显式 bind。
    tokens = bind_request_context(request_id)
    try:
        response = await call_next(request)
    finally:
        reset_request_context(tokens)
    response.headers["X-Request-Id"] = request_id
    try:
        from app.api.health import record_http_status
        record_http_status(int(response.status_code))
    except Exception:  # noqa: BLE001
        # metrics 不可阻断主请求
        pass
    return response

# 挂载路由
app.include_router(auth.router)
app.include_router(career_tracks.router)
app.include_router(domains.router)
app.include_router(profile.router)
app.include_router(generation.router)
app.include_router(feedback.router)
app.include_router(learning_path.router)
app.include_router(visualization.router)
app.include_router(knowledge_graph.router)
app.include_router(questions.router)
app.include_router(ws.router)
app.include_router(admin_router)
app.include_router(health.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理：
    - HTTPException 仍由 FastAPI 默认处理器处理（直接旁过）
    - 其他未捕获异常：日志记录完整堆栈 + request_id，向客户端只返回脱敏消息
    """
    # HTTPException 旁路到 FastAPI/Starlette 内置处理器
    if isinstance(exc, (FastAPIHTTPException, StarletteHTTPException)):
        raise exc

    request_id = getattr(request.state, "request_id", "-") if hasattr(request, "state") else "-"
    logger.exception(
        f"Unhandled exception [request_id={request_id}] {type(exc).__name__}: {exc}"
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误", "request_id": request_id},
        headers={"X-Request-Id": request_id},
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
