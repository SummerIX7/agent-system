"""
E2E 测试基础设施（MOCK 模式）

- 使用 SQLite 文件数据库代替 MySQL，无需外部数据库即可运行
- 通过 TEST_DATABASE_URL 环境变量注入，Settings.DATABASE_URL property 自动切换
- MOCK_MODE=true：所有 LLM/嵌入/知识库调用返回本地模拟数据
- conftest.py 必须在所有 app 导入之前设置环境变量
"""

from __future__ import annotations

import os

# ══════════════════════════════════════════════════════════════
# 必须在任何 app 代码导入之前设置环境变量
# ══════════════════════════════════════════════════════════════
os.environ["MOCK_MODE"] = "true"
os.environ["TEST_DATABASE_URL"] = "sqlite+aiosqlite:///./test_e2e.db"
os.environ["TEST_DATABASE_URL_SYNC"] = "sqlite:///./test_e2e.db"
os.environ["ENABLE_KNOWLEDGE_BASE"] = "false"

import pytest
from httpx import ASGITransport, AsyncClient

TEST_DB_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "test_e2e.db")


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    """测试全结束后关闭引擎连接并删除 SQLite 测试数据库文件。"""
    yield
    try:
        from app.models.database import engine
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import asyncio as _asyncio
            _asyncio.ensure_future(engine.dispose())
        else:
            loop.run_until_complete(engine.dispose())
    except Exception:
        pass
    db_path = os.path.abspath(TEST_DB_FILE)
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except PermissionError:
        pass  # Windows 文件锁定，下次运行时会覆盖


@pytest.fixture
async def app():
    """返回已配置好的 FastAPI app 实例（SQLite + Mock 模式）

    显式调用 metadata.create_all 确保表在测试前就绪，不依赖 lifespan
    （ASGITransport 在某些场景下 lifespan 触发时机不确定）。
    """
    from main import app as _app
    from app.models.database import engine, Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield _app


@pytest.fixture
async def client(app):
    """基于 ASGITransport 的异步 HTTP 客户端（无真实网络 I/O）"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers():
    """返回一个带有效 Bearer token 的 headers 字典。
    由于 MOCK 模式下 LLM 不产生真正 token，auth 流程需要真实注册/登录，
    因此这里仅提供一个辅助函数 —— 测试中自行调用 register+login 获取 token。
    """
    return {}


@pytest.fixture
async def authenticated_user(client):
    """注册 + 登录，返回 (token, user_id, username)。"""
    username = f"e2e_test_{os.urandom(4).hex()}"
    password = "test123456"

    # 注册
    resp = await client.post("/api/auth/register", json={
        "username": username,
        "password": password,
    })
    assert resp.status_code == 200, f"注册失败: {resp.text}"
    data = resp.json()
    token = data["access_token"]
    user_id = data["user_id"]

    return token, user_id, username
