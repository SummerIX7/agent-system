"""
数据库操作辅助工具：死锁重试、安全 flush 等。
"""
import asyncio
import functools
import logging

import asyncpg
from sqlalchemy.exc import DBAPIError, PendingRollbackError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# PostgreSQL SQLSTATE 40P01: deadlock_detected
DEADLOCK_SQLSTATE = "40P01"
MAX_RETRIES = 3
RETRY_DELAYS = [0.5, 1.0, 2.0]


def _is_deadlock(exc: BaseException) -> bool:
    """检测异常是否为 PostgreSQL 40P01 死锁（支持多层包装解包）。

    asyncpg 异常会被 SQLAlchemy 异步适配层逐层包装，
    沿 orig/__cause__ 链查找原始异常类型或 sqlstate。
    """
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, asyncpg.exceptions.DeadlockDetectedError):
            return True
        if getattr(current, "sqlstate", None) == DEADLOCK_SQLSTATE:
            return True
        current = getattr(current, "orig", None) or current.__cause__
    # 兜底：字符串匹配（某些包装层不暴露 sqlstate）
    msg = str(exc).lower()
    return "40p01" in msg or "deadlock detected" in msg


def _find_db_session(args, kwargs) -> AsyncSession | None:
    """从函数参数中查找 AsyncSession 实例，用于重试前回滚。"""
    # 优先从 kwargs 中查找名为 db 的参数
    for key in ("db", "db_session", "session"):
        if key in kwargs and isinstance(kwargs[key], AsyncSession):
            return kwargs[key]
    # 从 args 中查找
    for arg in args:
        if isinstance(arg, AsyncSession):
            return arg
    return None


def retry_on_deadlock(max_retries: int = MAX_RETRIES, delays=None):
    """
    异步函数死锁重试装饰器。

    捕获 PostgreSQL 40P01 死锁（asyncpg DeadlockDetectedError），
    死锁时自动回滚 AsyncSession 后重试，最多重试 max_retries 次。
    也会捕获 PendingRollbackError（通常是前次死锁导致），
    自动回滚后重试。

    用法:
        @retry_on_deadlock()
        async def my_db_write(db, ...):
            await db.flush()
    """
    if delays is None:
        delays = RETRY_DELAYS

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except PendingRollbackError as e:
                    # Session 已因前次死锁被回滚，需要显式 rollback 后再重试
                    db_session = _find_db_session(args, kwargs)
                    if db_session and attempt < max_retries:
                        delay = delays[min(attempt, len(delays) - 1)]
                        logger.warning(
                            f"[DB死锁重试] {func.__qualname__}: "
                            f"第 {attempt + 1}/{max_retries + 1} 次因 PendingRollbackError 失败, "
                            f"{delay}s 后 rollback 并重试..."
                        )
                        try:
                            await db_session.rollback()
                        except Exception:
                            pass
                        await asyncio.sleep(delay)
                        last_exc = e
                    else:
                        raise
                except Exception as e:
                    if _is_deadlock(e) and attempt < max_retries:
                        delay = delays[min(attempt, len(delays) - 1)]
                        logger.warning(
                            f"[DB死锁重试] {func.__qualname__}: "
                            f"第 {attempt + 1}/{max_retries + 1} 次因 40P01 死锁失败, "
                            f"{delay}s 后重试..."
                        )
                        # 死锁后回滚 session 以便重试
                        db_session = _find_db_session(args, kwargs)
                        if db_session:
                            try:
                                await db_session.rollback()
                            except Exception:
                                pass
                        await asyncio.sleep(delay)
                        last_exc = e
                    else:
                        raise
            raise last_exc

        return wrapper

    return decorator
