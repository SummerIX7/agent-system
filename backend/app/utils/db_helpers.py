"""
数据库操作辅助工具：死锁重试、安全 flush 等。
"""
import asyncio
import functools
import logging

from sqlalchemy.exc import OperationalError, PendingRollbackError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# MySQL error code 1213: ER_LOCK_DEADLOCK
DEADLOCK_ERRNO = 1213
MAX_RETRIES = 3
RETRY_DELAYS = [0.5, 1.0, 2.0]


def _is_deadlock(exc: BaseException) -> bool:
    """检测异常是否为 MySQL 1213 死锁（支持多层包装解包）。

    说明：aiomysql 的 OperationalError 可能多层嵌套，
    逐层解包 orig 直到找到原始错误码。
    """
    current = exc
    while isinstance(current, OperationalError):
        orig = getattr(current, "orig", None)
        if orig is None:
            break
        errno = getattr(orig, "args", [None])
        if errno and isinstance(errno[0], int) and errno[0] == DEADLOCK_ERRNO:
            return True
        current = orig
    # 兜底：字符串匹配（某些驱动版本不暴露 errno）
    msg = str(exc)
    return "1213" in msg and "deadlock" in msg.lower()


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

    捕获 sqlalchemy.exc.OperationalError（MySQL 1213），
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
                            f"第 {attempt + 1}/{max_retries + 1} 次因 1213 死锁失败, "
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
