"""会话 CRUD 与业务字段追加/读取（resources/feedback/agent_log/practice_state/等）。"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from app.core.store._client import (
    KEY_SESSION,
    KEY_SESSION_INDEX,
    SESSION_TTL,
    _fallback_sessions,
    _get_redis,
    _is_redis_ok,
)
from app.core.store._serializer import deserialize, new_session, serialize


# ═══════════════════════════════════════════
# 基础 CRUD
# ═══════════════════════════════════════════

def get_session(session_id: str) -> dict:
    """获取会话数据，不存在则创建空会话"""
    r = _get_redis()

    if not _is_redis_ok(r):
        if session_id not in _fallback_sessions:
            _fallback_sessions[session_id] = new_session(session_id)
        return _fallback_sessions[session_id]

    key = f"{KEY_SESSION}:{session_id}"
    if not r.exists(key):
        session = new_session(session_id)
        r.hset(key, mapping=serialize(session))
        r.expire(key, SESSION_TTL)
        r.sadd(KEY_SESSION_INDEX, session_id)
        return session

    raw = r.hgetall(key)
    r.expire(key, SESSION_TTL)  # 续期
    return deserialize(raw)


def update_session(session_id: str, data: dict) -> None:
    """更新会话数据（合并写入）"""
    r = _get_redis()

    if not _is_redis_ok(r):
        session = _fallback_sessions.get(session_id)
        if session is None:
            session = new_session(session_id)
            _fallback_sessions[session_id] = session
        session.update(data)
        return

    get_session(session_id)  # 确保会话存在
    key = f"{KEY_SESSION}:{session_id}"
    r.hset(key, mapping=serialize(data))
    r.expire(key, SESSION_TTL)


def _update_field(session_id: str, field: str, value: Any) -> None:
    """更新单个字段（资源/反馈/日志追加用）"""
    r = _get_redis()

    if not _is_redis_ok(r):
        session = _fallback_sessions.get(session_id, {})
        if not session:
            session = new_session(session_id)
            _fallback_sessions[session_id] = session
        session[field] = value
        return

    key = f"{KEY_SESSION}:{session_id}"
    if not r.exists(key):
        get_session(session_id)  # 初始化
    r.hset(key, field, json.dumps(value, ensure_ascii=False))
    r.expire(key, SESSION_TTL)


# ═══════════════════════════════════════════
# 资源 / 反馈 / Agent 日志
# ═══════════════════════════════════════════

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


# ═══════════════════════════════════════════
# 答题进度
# ═══════════════════════════════════════════

def save_practice_state(session_id: str, state: dict) -> None:
    """保存答题进度到 session"""
    _update_field(session_id, "practice_state", state)


def get_practice_state(session_id: str) -> dict:
    """从 session 读取答题进度"""
    return get_session(session_id).get("practice_state", {})


# ═══════════════════════════════════════════
# 试题缓存（总缓存 + 阶段缓存 + 综合练习）
# ═══════════════════════════════════════════

def save_cached_questions(session_id: str, questions_data: dict) -> None:
    """缓存试题到 session（避免每次刷新都重新生成）"""
    _update_field(session_id, "cached_questions", questions_data)


def get_cached_questions(session_id: str) -> dict | None:
    """从 session 读取缓存的试题，没有则返回 None"""
    data = get_session(session_id).get("cached_questions")
    return data if data else None


def clear_cached_questions(session_id: str) -> None:
    """清除缓存的试题（用户主动重新生成时调用）"""
    r = _get_redis()

    if not _is_redis_ok(r):
        session = _fallback_sessions.get(session_id, {})
        session.pop("cached_questions", None)
        session.pop("tiered_questions", None)
        session.pop("comprehensive_questions", None)
        return

    key = f"{KEY_SESSION}:{session_id}"
    if r.exists(key):
        r.hdel(key, "cached_questions", "tiered_questions", "comprehensive_questions")


def save_tiered_questions(session_id: str, tiered: dict) -> None:
    """缓存节点练习 {node: QuestionSet}；保留函数名兼容旧调用。"""
    _update_field(session_id, "tiered_questions", tiered)


def get_tiered_questions(session_id: str) -> dict | None:
    """获取缓存的节点练习，没有则返回 None。"""
    data = get_session(session_id).get("tiered_questions")
    return data if data else None


def get_tier_questions(session_id: str, level: str) -> dict | None:
    """获取指定类型的缓存试题（node 或 comprehensive 以外的旧类型）。"""
    tiered = get_tiered_questions(session_id)
    if tiered and isinstance(tiered, dict):
        return tiered.get(level)
    return None


def save_tiered_questions_for_stage(session_id: str, stage: int, tiered: dict) -> None:
    """
    缓存指定节点的节点练习。
    存储在 session 的 tiered_questions_map 字段中，以 stage 为 key。
    """
    session = get_session(session_id)
    tq_map = session.get("tiered_questions_map", {})
    if isinstance(tq_map, str):
        try:
            tq_map = json.loads(tq_map)
        except Exception:
            tq_map = {}
    tq_map[str(stage)] = tiered
    _update_field(session_id, "tiered_questions_map", tq_map)


def get_tiered_questions_for_stage(session_id: str, stage: int) -> dict | None:
    """获取指定节点的节点练习缓存"""
    session = get_session(session_id)
    tq_map = session.get("tiered_questions_map", {})
    if isinstance(tq_map, str):
        try:
            tq_map = json.loads(tq_map)
        except Exception:
            tq_map = {}
    if not tq_map or not isinstance(tq_map, dict):
        return None
    return tq_map.get(str(stage))


def get_tier_questions_for_stage(session_id: str, stage: int, level: str) -> dict | None:
    """获取指定节点+类型的缓存试题"""
    tiered = get_tiered_questions_for_stage(session_id, stage)
    if tiered and isinstance(tiered, dict):
        return tiered.get(level)
    return None


def save_comprehensive_questions(session_id: str, question_set: dict) -> None:
    """缓存最终综合练习题，不绑定具体 stage。"""
    _update_field(session_id, "comprehensive_questions", question_set)


def get_comprehensive_questions(session_id: str) -> dict | None:
    """获取最终综合练习题缓存。"""
    data = get_session(session_id).get("comprehensive_questions")
    return data if data else None


# ═══════════════════════════════════════════
# 考核结果 / 练习结果
# ═══════════════════════════════════════════

def save_test_result(session_id: str, level: str, result: dict) -> None:
    """保存某轮考核结果（basic 或 advanced）"""
    results = get_session(session_id).get("test_results", {})
    if isinstance(results, str):
        results = {}
    results[level] = result
    _update_field(session_id, "test_results", results)


def get_test_result(session_id: str, level: str) -> dict | None:
    """获取某轮考核结果"""
    results = get_session(session_id).get("test_results", {})
    if isinstance(results, str):
        try:
            results = json.loads(results)
        except Exception:
            results = {}
    return results.get(level) if results else None


def append_practice_result(session_id: str, result: dict) -> list[dict]:
    """追加一轮练习结果，供报告页分析。"""
    results = get_session(session_id).get("practice_results", [])
    if isinstance(results, str):
        try:
            results = json.loads(results)
        except Exception:
            results = []
    results.append({**result, "created_at": datetime.now().isoformat()})
    _update_field(session_id, "practice_results", results)
    return results


def get_practice_results(session_id: str) -> list[dict]:
    """获取所有练习结果。"""
    results = get_session(session_id).get("practice_results", [])
    if isinstance(results, str):
        try:
            return json.loads(results)
        except Exception:
            return []
    return results if isinstance(results, list) else []


def clear_test_results(session_id: str) -> None:
    """清除所有考核结果（节点推进时调用）"""
    r = _get_redis()
    if not _is_redis_ok(r):
        session = _fallback_sessions.get(session_id, {})
        session.pop("test_results", None)
        return
    key = f"{KEY_SESSION}:{session_id}"
    if r.exists(key):
        r.hdel(key, "test_results")


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
            sessions.append(deserialize(raw))
        else:
            r.srem(KEY_SESSION_INDEX, sid)  # 清理过期引用
    return sessions
