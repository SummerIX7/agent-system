from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import feedback, generation, profile, visualization, ws
from app.core.config import get_settings
from app.models.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时：可以在这里初始化数据库连接池等
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
app.include_router(profile.router)
app.include_router(generation.router)
app.include_router(feedback.router)
app.include_router(visualization.router)
app.include_router(ws.router)


@app.get("/")
async def root():
    return {"message": "多智能体协同决策系统 API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}
