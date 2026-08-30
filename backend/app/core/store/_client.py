"""Redis \u5b58\u50a8\u5c42\u5171\u4eab\u5ba2\u6237\u7aef\u4e0e\u5c40\u90e8\u964d\u7ea7 state\u3002

\u672c\u6a21\u5757\u96c6\u4e2d\u7ba1\u7406\uff1a
- Redis \u8fde\u63a5\u6c60\u4e0e\u53ef\u7528\u6027\u5f00\u5173\uff08``_get_redis`` / ``_is_redis_ok`` / ``redis_is_available``\uff09
- Redis \u4e0d\u53ef\u7528\u65f6\u7684\u5185\u5b58\u964d\u7ea7\u5b58\u50a8\uff08``_fallback_sessions``\u3001``_fallback_ws_queues``\u3001``_fallback_ratelimits``\uff09
- \u5168\u5c40 Key \u524d\u7f00\u4e0e TTL \u5e38\u91cf

\u62c6\u5206\u540e\u7684\u5176\u4ed6\u5b50\u6a21\u5757\u5747\u4ece\u672c\u6587\u4ef6 import \u5171\u4eab\u4f9d\u8d56\uff0c\u4e0d\u91cd\u590d\u5b9a\u4e49\uff0c\n\u907f\u514d\u8fde\u63a5\u6c60\u91cd\u590d\u521d\u59cb\u5316\u4e0e state \u4e0d\u4e00\u81f4\u3002
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Optional

import redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Redis \u8fde\u63a5\u6c60\uff08\u5168\u5c40\u5355\u4f8b\uff09\u2500\u2500
_pool: Optional[redis.ConnectionPool] = None
_redis_available: bool = True

# ── \u964d\u7ea7\u5185\u5b58\u5b58\u50a8\uff08Redis \u4e0d\u53ef\u7528\u65f6\u4f7f\u7528\uff09\u2500\u2500
# \u6ce8\u610f\uff1a\u5b50\u6a21\u5757\u5747\u9700 ``from app.core.store._client import _fallback_sessions``\n# \u5e76\u76f4\u63a5\u4fee\u6539 dict \u5185\u5bb9\uff0c\u4e0d\u80fd\u91cd\u65b0\u8d4b\u503c\u3002
_fallback_sessions: dict[str, dict] = {}
_fallback_ws_queues: dict[str, list] = {}
_fallback_ratelimits: dict[str, tuple[int, float]] = {}

SESSION_TTL = timedelta(hours=24)
RATELIMIT_WINDOW = 60        # \u9891\u7387\u9650\u5236\u7a97\u53e3\uff08\u79d2\uff09
RATELIMIT_MAX_REQUESTS = 30  # \u6bcf\u7a97\u53e3\u6700\u5927\u8bf7\u6c42\u6570

# ── Key \u547d\u540d\u524d\u7f00 ──
KEY_SESSION = "session"              # session:{id}        \u2192 Hash
KEY_SESSION_INDEX = "session:index"  # Set\uff08\u6d3b\u8dc3\u4f1a\u8bdd\u96c6\u5408\uff09
KEY_WS = "ws"                        # ws:{id}             \u2192 List
KEY_WS_PUB = "ws:pub"                # ws:pub:{id}         \u2192 Pub/Sub channel
KEY_RATELIMIT = "ratelimit"          # ratelimit:{ip}:{api} \u2192 String
KEY_LLM_CACHE = "llm_cache"          # llm_cache:{hash}    \u2192 String


def _get_redis() -> Optional[redis.Redis]:
    """\u83b7\u53d6 Redis \u8fde\u63a5\uff0c\u4e0d\u53ef\u7528\u65f6\u8fd4\u56de None\u3002"""
    global _pool, _redis_available

    if not _redis_available:
        return None

    try:
        if _pool is None:
            _pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
        return redis.Redis(connection_pool=_pool)
    except Exception as e:  # noqa: BLE001
        logger.warning("Redis \u8fde\u63a5\u5931\u8d25\uff0c\u964d\u7ea7\u4e3a\u5185\u5b58\u5b58\u50a8: %s", e)
        _redis_available = False
        return None


def _is_redis_ok(r: Optional[redis.Redis]) -> bool:
    """\u68c0\u67e5 Redis \u8fde\u63a5\u662f\u5426\u53ef\u7528\uff08\u547d\u4e2d\u65f6\u4f1a\u4fdd\u6301\u5f00\u5173 True\uff09\u3002"""
    global _redis_available
    if r is None:
        return False
    try:
        r.ping()
        return True
    except Exception:  # noqa: BLE001
        _redis_available = False
        return False


def redis_is_available() -> bool:
    """\u4f9b\u5916\u90e8\u67e5\u8be2 Redis \u662f\u5426\u53ef\u7528\u3002"""
    r = _get_redis()
    return _is_redis_ok(r)


def check_redis_health() -> dict:
    """Redis \u5065\u5eb7\u68c0\u67e5\uff08\u4f9b\u65e7 /health \u7aef\u70b9\u4f7f\u7528\uff09\u3002"""
    r = _get_redis()

    if not _is_redis_ok(r):
        return {
            "status": "degraded",
            "backend": "memory",
            "reason": "Redis \u4e0d\u53ef\u7528\uff0c\u5f53\u524d\u4f7f\u7528\u5185\u5b58\u964d\u7ea7\u5b58\u50a8",
        }

    try:
        info = r.info("memory")
        return {
            "status": "healthy",
            "backend": "redis",
            "used_memory_human": info.get("used_memory_human", "N/A"),
            "connected_clients": info.get("connected_clients", 0),
        }
    except Exception as e:  # noqa: BLE001
        return {"status": "unhealthy", "error": str(e)}
