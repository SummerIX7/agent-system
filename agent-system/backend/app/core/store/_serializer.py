"""会话数据序列化工具（供子模块共享）。"""

from __future__ import annotations

import json
from datetime import datetime


def new_session(session_id: str) -> dict:
    """创建新会话数据"""
    return {
        "session_id": session_id,
        "learner_id": "",
        "profile": {},
        "resources": [],
        "feedback": [],
        "practice_results": [],
        "agent_logs": [],
        "trace_entries": [],
        "created_at": datetime.now().isoformat(),
    }


# 需要 JSON 序列化的字段集合
_JSON_FIELDS = {
    "profile", "resources", "feedback", "agent_logs", "trace_entries",
    "cached_questions", "practice_state", "node_states", "node_resources",
    "tiered_questions", "tiered_questions_map", "comprehensive_questions",
    "test_results", "practice_results",
}


def serialize(data: dict) -> dict:
    """将 Python dict 序列化为 Redis Hash 兼容格式（全字符串）"""
    result: dict = {}
    for k, v in data.items():
        if k in _JSON_FIELDS and v is not None:
            result[k] = json.dumps(v, ensure_ascii=False)
        elif v is not None:
            result[k] = str(v)
        else:
            result[k] = ""
    return result


# 反序列化时各字段的默认值
_JSON_DEFAULTS: dict = {
    "profile": {},
    "resources": [],
    "feedback": [],
    "practice_results": [],
    "agent_logs": [],
    "trace_entries": [],
    "cached_questions": None,
    "practice_state": {},
    "node_states": {},
    "node_resources": {},
    "tiered_questions": None,
    "tiered_questions_map": {},
    "comprehensive_questions": None,
    "test_results": {},
}


def deserialize(raw: dict) -> dict:
    """将 Redis Hash（全字符串）还原为 Python dict"""
    result = dict(raw)
    for field, default in _JSON_DEFAULTS.items():
        if field in result and isinstance(result[field], str):
            try:
                result[field] = json.loads(result[field])
            except (json.JSONDecodeError, TypeError):
                result[field] = default
    return result
