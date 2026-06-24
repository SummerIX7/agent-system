from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, feedback, generation, profile, questions, visualization, ws
from app.core.config import get_settings
from app.models.database import engine, Base
# 导入所有模型，确保被 Base 注册
from app.models.user import User
from app.models.learner import Learner
from app.models.resource import Resource
from app.models.agent_state import AgentLog, FeedbackRecord


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时：创建数据库表（如果不存在）
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[启动] 数据库表已就绪")
    yield
    # 关闭时：清理资源
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
app.include_router(profile.router)
app.include_router(generation.router)
app.include_router(feedback.router)
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
    return {"status": "ok"}
