import json
from sqlalchemy import event, Text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)


# 注册事件监听器：自动将 dict/list 转为 JSON 字符串
@event.listens_for(engine.sync_engine, "before_cursor_execute")
def _serialize_dicts(conn, cursor, statement, parameters, context, executemany):
    """在 SQL 执行前，自动将参数中的 dict/list 序列化为 JSON 字符串"""
    if parameters and isinstance(parameters, (tuple, list)):
        new_params = []
        for param in parameters:
            if isinstance(param, (dict, list)):
                new_params.append(json.dumps(param, ensure_ascii=False))
            else:
                new_params.append(param)
        return statement, tuple(new_params)
    return statement, parameters


async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    """FastAPI 依赖注入：获取数据库会话"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
