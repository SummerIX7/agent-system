"""
Redis 存储层 — 会话级数据存储
支持多实例部署、数据持久化、频率限制、LLM 缓存
Redis 不可用时自动降级为内存存储
"""

import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Redis 连接池（全局单例） ──
_pool: Optional[redis.ConnectionPool] = None
_redis_available: bool = True

# ── 降级内存存储（Redis 不可用时使用） ──
_fallback_sessions: dict[str, dict] = {}
_fallback_ws_queues: dict[str, list] = {}

SESSION_TTL = timedelta(hours=24)
RATELIMIT_WINDOW = 60        # 频率限制窗口（秒）
RATELIMIT_MAX_REQUESTS = 30  # 每窗口最大请求数

# ── Key 命名前缀 ──
KEY_SESSION = "session"              # session:{id}        → Hash
KEY_SESSION_INDEX = "session:index"  # Set（活跃会话集合）
KEY_WS = "ws"                        # ws:{id}             → List
KEY_RATELIMIT = "ratelimit"          # ratelimit:{ip}:{api} → String
KEY_LLM_CACHE = "llm_cache"          # llm_cache:{hash}    → String


def _get_redis() -> Optional[redis.Redis]:
    """获取 Redis 连接，不可用时返回 None"""
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
    except Exception as e:
        logger.warning(f"Redis 连接失败，降级为内存存储: {e}")
        _redis_available = False
        return None


def _is_redis_ok(r: Optional[redis.Redis]) -> bool:
    """检查 Redis 连接是否可用"""
    if r is None:
        return False
    try:
        r.ping()
        return True
    except Exception:
        global _redis_available
        _redis_available = False
        return False


# ═══════════════════════════════════════════
# 序列化工具
# ═══════════════════════════════════════════

def _new_session(session_id: str) -> dict:
    """创建新会话数据"""
    return {
        "session_id": session_id,
        "learner_id": "",
        "profile": {},
        "resources": [],
        "feedback": [],
        "agent_logs": [],
        "created_at": datetime.now().isoformat(),
    }


def _serialize(data: dict) -> dict:
    """将 Python dict 序列化为 Redis Hash 兼容格式（全字符串）"""
    result = {}
    for k, v in data.items():
        if k in ("profile", "resources", "feedback", "agent_logs"):
            result[k] = json.dumps(v, ensure_ascii=False)
        elif v is not None:
            result[k] = str(v)
        else:
            result[k] = ""
    return result


def _deserialize(raw: dict) -> dict:
    """将 Redis Hash（全字符串）还原为 Python dict"""
    result = dict(raw)
    for field in ("profile", "resources", "feedback", "agent_logs"):
        if field in result and isinstance(result[field], str):
            try:
                result[field] = json.loads(result[field])
            except (json.JSONDecodeError, TypeError):
                result[field] = {} if field == "profile" else []
    return result


# ═══════════════════════════════════════════
# 会话管理（对外接口签名不变）
# ═══════════════════════════════════════════

def get_session(session_id: str) -> dict:
    """获取会话数据，不存在则创建空会话"""
    r = _get_redis()

    if not _is_redis_ok(r):
        if session_id not in _fallback_sessions:
            _fallback_sessions[session_id] = _new_session(session_id)
        return _fallback_sessions[session_id]

    key = f"{KEY_SESSION}:{session_id}"
    if not r.exists(key):
        session = _new_session(session_id)
        r.hset(key, mapping=_serialize(session))
        r.expire(key, SESSION_TTL)
        r.sadd(KEY_SESSION_INDEX, session_id)
        return session

    raw = r.hgetall(key)
    r.expire(key, SESSION_TTL)  # 续期
    return _deserialize(raw)


def update_session(session_id: str, data: dict) -> None:
    """更新会话数据（合并写入）"""
    r = _get_redis()

    if not _is_redis_ok(r):
        session = _fallback_sessions.get(session_id, {})
        session.update(data)
        _fallback_sessions[session_id] = session
        return

    get_session(session_id)  # 确保会话存在
    key = f"{KEY_SESSION}:{session_id}"
    r.hset(key, mapping=_serialize(data))
    r.expire(key, SESSION_TTL)


def _update_field(session_id: str, field: str, value: Any) -> None:
    """更新单个字段（资源/反馈/日志追加用）"""
    r = _get_redis()

    if not _is_redis_ok(r):
        session = _fallback_sessions.get(session_id, {})
        if not session:
            session = _new_session(session_id)
            _fallback_sessions[session_id] = session
        session[field] = value
        return

    key = f"{KEY_SESSION}:{session_id}"
    if not r.exists(key):
        get_session(session_id)  # 初始化
    r.hset(key, field, json.dumps(value, ensure_ascii=False))
    r.expire(key, SESSION_TTL)


def add_resource(session_id: str, resource: dict) -> None:
    """添加生成的资源（追加到列表）"""
    session = get_session(session_id)
    resources = session.get("resources", [])
    resources.append({**resource, "created_at": datetime.now().isoformat()})
    _update_field(session_id, "resources", resources)


def add_feedback(session_id: str, feedback: dict) -> None:
    """添加反馈记录（追加到列表）"""
    session = get_session(session_id)
    feedback_list = session.get("feedback", [])
    feedback_list.append({**feedback, "created_at": datetime.now().isoformat()})
    _update_field(session_id, "feedback", feedback_list)


def add_agent_log(session_id: str, log: dict) -> None:
    """添加 Agent 日志（追加到列表）"""
    session = get_session(session_id)
    logs = session.get("agent_logs", [])
    logs.append({**log, "timestamp": datetime.now().isoformat()})
    _update_field(session_id, "agent_logs", logs)


def get_all_sessions() -> list[dict]:
    """获取所有活跃会话（替代直接遍历 _sessions dict）"""
    r = _get_redis()

    if not _is_redis_ok(r):
        return list(_fallback_sessions.values())

    session_ids = r.smembers(KEY_SESSION_INDEX)
    sessions = []
    for sid in session_ids:
        key = f"{KEY_SESSION}:{sid}"
        if r.exists(key):
            raw = r.hgetall(key)
            sessions.append(_deserialize(raw))
        else:
            r.srem(KEY_SESSION_INDEX, sid)  # 清理过期引用
    return sessions


# ═══════════════════════════════════════════
# WebSocket 消息队列
# ═══════════════════════════════════════════

def push_ws_message(session_id: str, message: dict) -> None:
    """向会话的 WebSocket 队列推送消息"""
    r = _get_redis()

    if not _is_redis_ok(r):
        if session_id not in _fallback_ws_queues:
            _fallback_ws_queues[session_id] = []
        _fallback_ws_queues[session_id].append(message)
        return

    key = f"{KEY_WS}:{session_id}"
    r.rpush(key, json.dumps(message, ensure_ascii=False))
    r.expire(key, SESSION_TTL)


def pop_ws_messages(session_id: str) -> list[dict]:
    """取出并清空会话的所有待发消息（原子操作）"""
    r = _get_redis()

    if not _is_redis_ok(r):
        msg_list = _fallback_ws_queues.pop(session_id, [])
        return msg_list

    key = f"{KEY_WS}:{session_id}"
    # Pipeline 保证 lrange + delete 原子性
    pipe = r.pipeline()
    pipe.lrange(key, 0, -1)
    pipe.delete(key)
    results = pipe.execute()
    raw_messages = results[0]  # list of JSON strings
    return [json.loads(msg) for msg in raw_messages] if raw_messages else []


# ═══════════════════════════════════════════
# 频率限制（多用户部署必备）
# ═══════════════════════════════════════════

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
        return True  # Redis 不可用时放行（降级策略）

    rkey = f"{KEY_RATELIMIT}:{key}"
    current = r.incr(rkey)
    if current == 1:
        r.expire(rkey, window_seconds)
    return current <= max_requests


# ═══════════════════════════════════════════
# LLM 响应缓存
# ═══════════════════════════════════════════

def _hash_content(content: str) -> str:
    """对内容做哈希，生成缓存键"""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def get_llm_cache(prompt: str, topic: str = "") -> Optional[str]:
    """
    获取缓存的 LLM 响应。
    用 prompt + topic 的哈希作为缓存键。
    """
    r = _get_redis()

    if not _is_redis_ok(r):
        return None

    cache_key = _hash_content(prompt + topic)
    cached = r.get(f"{KEY_LLM_CACHE}:{cache_key}")
    return cached


def set_llm_cache(prompt: str, response: str, topic: str = "", ttl: int = 3600) -> None:
    """
    缓存 LLM 响应（默认 1 小时）。
    适合缓存：知识概念解释、标准问题回答。
    不适合缓存：个性化生成、苏格拉底追问。
    """
    r = _get_redis()

    if not _is_redis_ok(r):
        return

    cache_key = _hash_content(prompt + topic)
    r.setex(f"{KEY_LLM_CACHE}:{cache_key}", ttl, response)


# ═══════════════════════════════════════════
# 健康检查
# ═══════════════════════════════════════════

def check_redis_health() -> dict:
    """Redis 连接健康检查（供 /health 端点使用）"""
    r = _get_redis()

    if not _is_redis_ok(r):
        return {
            "status": "degraded",
            "backend": "memory",
            "reason": "Redis 不可用，当前使用内存降级存储",
        }

    try:
        info = r.info("memory")
        return {
            "status": "healthy",
            "backend": "redis",
            "used_memory_human": info.get("used_memory_human", "N/A"),
            "connected_clients": info.get("connected_clients", 0),
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def redis_is_available() -> bool:
    """供外部查询 Redis 是否可用"""
    r = _get_redis()
    return _is_redis_ok(r)
