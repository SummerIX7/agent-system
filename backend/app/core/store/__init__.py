"""``app.core.store`` 包入口 —— 保留旧的扁平 import 路径。

历史用法（继续保持有效）：
    from app.core.store import get_session, push_ws_message, check_rate_limit, ...

拆分后子模块：
    - _client       Redis 连接池 + 降级 state + Key 常量 + 健康检查
    - _serializer   会话数据序列化/反序列化
    - session       会话 CRUD、resources/feedback/agent_log、试题/考核缓存
    - ws            WebSocket 消息队列（rpush + publish 双轨道）
    - ratelimit     频率限制
    - llm_cache     LLM 响应缓存
    - trace         工作流追踪
    - context       Learner 上下文回填与 agent 日志持久化
"""

from __future__ import annotations

# ── 共享 state & 常量 ──
from app.core.store._client import (
    KEY_LLM_CACHE,
    KEY_RATELIMIT,
    KEY_SESSION,
    KEY_SESSION_INDEX,
    KEY_WS,
    KEY_WS_PUB,
    RATELIMIT_MAX_REQUESTS,
    RATELIMIT_WINDOW,
    SESSION_TTL,
    _fallback_ratelimits,
    _fallback_sessions,
    _fallback_ws_queues,
    _get_redis,
    _is_redis_ok,
    check_redis_health,
    redis_is_available,
)

# ── 会话 CRUD 与业务字段 ──
from app.core.store.session import (
    _update_field,
    add_agent_log,
    add_feedback,
    add_resource,
    append_practice_result,
    clear_cached_questions,
    clear_test_results,
    get_all_sessions,
    get_cached_questions,
    get_comprehensive_questions,
    get_practice_results,
    get_practice_state,
    get_session,
    get_test_result,
    get_tier_questions,
    get_tier_questions_for_stage,
    get_tiered_questions,
    get_tiered_questions_for_stage,
    save_cached_questions,
    save_comprehensive_questions,
    save_practice_state,
    save_test_result,
    save_tiered_questions,
    save_tiered_questions_for_stage,
    update_session,
)

# ── WebSocket 消息队列 ──
from app.core.store.ws import pop_ws_messages, push_ws_message

# ── 频率限制 ──
from app.core.store.ratelimit import check_rate_limit

# ── LLM 缓存 ──
from app.core.store.llm_cache import _hash_content, get_llm_cache, set_llm_cache

# ── 工作流追踪 ──
from app.core.store.trace import add_trace_entry, get_trace_entries

# ── Learner 上下文回填 ──
from app.core.store.context import (
    _persist_in_session_resources,
    flush_agent_logs_to_db,
    resolve_learner_context,
)

__all__ = [
    # 常量
    "KEY_LLM_CACHE", "KEY_RATELIMIT", "KEY_SESSION", "KEY_SESSION_INDEX",
    "KEY_WS", "KEY_WS_PUB", "SESSION_TTL", "RATELIMIT_MAX_REQUESTS", "RATELIMIT_WINDOW",
    # Redis 客户端
    "redis_is_available", "check_redis_health",
    # 会话
    "get_session", "update_session", "add_agent_log", "add_feedback", "add_resource",
    "save_practice_state", "get_practice_state",
    "save_cached_questions", "get_cached_questions", "clear_cached_questions",
    "save_tiered_questions", "get_tiered_questions", "get_tier_questions",
    "save_tiered_questions_for_stage", "get_tiered_questions_for_stage",
    "get_tier_questions_for_stage",
    "save_comprehensive_questions", "get_comprehensive_questions",
    "save_test_result", "get_test_result", "clear_test_results",
    "append_practice_result", "get_practice_results",
    "get_all_sessions",
    # WebSocket
    "push_ws_message", "pop_ws_messages",
    # 频率限制
    "check_rate_limit",
    # LLM 缓存
    "get_llm_cache", "set_llm_cache",
    # 工作流追踪
    "add_trace_entry", "get_trace_entries",
    # Learner 上下文
    "resolve_learner_context", "flush_agent_logs_to_db",
]
