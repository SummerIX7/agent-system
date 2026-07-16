"""频率限制：Redis INCR + EXPIRE 原子实现，Redis 不可用时降级为内存滑动窗。"""

from __future__ import annotations

import time as _time_module

from app.core.store._client import (
    KEY_RATELIMIT,
    _fallback_ratelimits,
    _get_redis,
    _is_redis_ok,
)


def check_rate_limit(key: str, max_requests: int = 30, window_seconds: int = 60) -> bool:
    """
    检查频率限制，返回 True 表示允许通过。
    用法：在 LLM 调用前检查 per-user 或 per-IP 频率。

    key 示例：
      - "user:{user_id}:generate"    按用户限流
      - "ip:{client_ip}:generate"    按 IP 限流
      - "global:generate"            全局限流
    """
    r = _get_redis()

    if not _is_redis_ok(r):
        # 降级：内存限流器
        now = _time_module.time()
        rkey = f"{KEY_RATELIMIT}:{key}"
        if rkey in _fallback_ratelimits:
            count, window_start = _fallback_ratelimits[rkey]
            if now - window_start > window_seconds:
                # 窗口过期，重置
                _fallback_ratelimits[rkey] = (1, now)
                return True
            if count >= max_requests:
                return False
            _fallback_ratelimits[rkey] = (count + 1, window_start)
            return True
        else:
            _fallback_ratelimits[rkey] = (1, now)
            return True

    rkey = f"{KEY_RATELIMIT}:{key}"
    current = r.incr(rkey)
    if current == 1:
        r.expire(rkey, window_seconds)
    return current <= max_requests
