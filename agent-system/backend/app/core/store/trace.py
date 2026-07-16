"""工作流追踪（Trace）—— 记录 Agent/节点执行链路，供 /trace 页面还原。"""

from __future__ import annotations

from datetime import datetime

from app.core.store.session import _update_field, get_session


def add_trace_entry(session_id: str, entry: dict) -> None:
    """追加一条工作流追踪记录"""
    session = get_session(session_id)
    entries = session.get("trace_entries", [])
    entries.append({**entry, "timestamp": datetime.now().isoformat()})
    _update_field(session_id, "trace_entries", entries)


def get_trace_entries(session_id: str) -> list[dict]:
    """获取该 session 的完整追踪记录"""
    session = get_session(session_id)
    return session.get("trace_entries", [])
