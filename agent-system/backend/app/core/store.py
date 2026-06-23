"""
内存存储层 — 会话级数据存储
后续可迁移到 MySQL，接口保持不变
"""

from datetime import datetime
from typing import Any

# 会话数据存储
_sessions: dict[str, dict] = {}

# WebSocket 消息队列
_ws_queues: dict[str, list] = {}


def get_session(session_id: str) -> dict:
    """获取会话数据，不存在则创建空会话"""
    if session_id not in _sessions:
        _sessions[session_id] = {
            "session_id": session_id,
            "learner_id": "",
            "profile": {},
            "resources": [],
            "feedback": [],
            "agent_logs": [],
            "created_at": datetime.now().isoformat(),
        }
    return _sessions[session_id]


def update_session(session_id: str, data: dict) -> None:
    """更新会话数据（合并）"""
    session = get_session(session_id)
    session.update(data)


def add_resource(session_id: str, resource: dict) -> None:
    """添加生成的资源"""
    session = get_session(session_id)
    session["resources"].append({
        **resource,
        "created_at": datetime.now().isoformat(),
    })


def add_feedback(session_id: str, feedback: dict) -> None:
    """添加反馈记录"""
    session = get_session(session_id)
    session["feedback"].append({
        **feedback,
        "created_at": datetime.now().isoformat(),
    })


def add_agent_log(session_id: str, log: dict) -> None:
    """添加 Agent 日志"""
    session = get_session(session_id)
    session["agent_logs"].append({
        **log,
        "timestamp": datetime.now().isoformat(),
    })


def get_all_sessions() -> list[dict]:
    """获取所有会话"""
    return list(_sessions.values())


# === WebSocket 队列管理 ===

def get_ws_queue(session_id: str) -> list:
    """获取会话的 WebSocket 消息队列"""
    if session_id not in _ws_queues:
        _ws_queues[session_id] = []
    return _ws_queues[session_id]


def push_ws_message(session_id: str, message: dict) -> None:
    """向会话的 WebSocket 队列推送消息"""
    queue = get_ws_queue(session_id)
    queue.append(message)


def pop_ws_messages(session_id: str) -> list:
    """取出并清空会话的所有待发消息"""
    queue = get_ws_queue(session_id)
    messages = queue[:]
    queue.clear()
    return messages
