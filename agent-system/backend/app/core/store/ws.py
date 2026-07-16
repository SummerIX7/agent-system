"""WebSocket 消息队列 —— 双轨道：rpush（历史积压）+ publish（实时分发）。"""

from __future__ import annotations

import json
import logging

from app.core.store._client import (
    KEY_WS,
    KEY_WS_PUB,
    SESSION_TTL,
    _fallback_ws_queues,
    _get_redis,
    _is_redis_ok,
)

logger = logging.getLogger(__name__)


def push_ws_message(session_id: str, message: dict) -> None:
    """向会话的 WebSocket 队列推送消息。

    双轨道策略（兼容旧轮询与新 Pub/Sub）：
    - rpush 到 List：作为"历史积压"，保障 WS 未连接时途中产生的消息可被后连接方 pop 取回。
    - publish 到 pub/sub：已连接的 WS 处理器可实时收到，免去 500ms 轮询。
    """
    r = _get_redis()

    if not _is_redis_ok(r):
        if session_id not in _fallback_ws_queues:
            _fallback_ws_queues[session_id] = []
        _fallback_ws_queues[session_id].append(message)
        return

    key = f"{KEY_WS}:{session_id}"
    payload = json.dumps(message, ensure_ascii=False)
    r.rpush(key, payload)
    r.expire(key, SESSION_TTL)

    # Pub/Sub 实时分发
    try:
        r.publish(f"{KEY_WS_PUB}:{session_id}", payload)
    except Exception as e:  # noqa: BLE001
        # publish 失败不影响主链路（订阅端仍可从 List 回补）
        logger.debug("WS publish 失败，仅轮询可拿到: %s", e)


def pop_ws_messages(session_id: str) -> list[dict]:
    """取出并清空会话的所有待发消息（原子操作）。"""
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
