"""⑤ 试题生成 Agent 节点（含无辩论变体）。"""

from __future__ import annotations

import time as _time

from app.graph.nodes._common import (
    _broadcast,
    _save_node_trace,
    _validate_questions,
    question_generator,
)
from app.graph.state import AgentState


async def gen_questions_node(state: AgentState) -> dict:
    session_id = state.get("session_id", "")
    start = _time.time()
    question_generator._trace_agent_name = "试题生成 Agent"
    question_generator._trace_calls = []

    _broadcast(session_id, "试题生成 Agent", "running", "正在生成试题...", 88)

    topic = state.get("topic", "")
    difficulty = state.get("difficulty", "beginner")
    profile = state.get("profile", {})

    result = await question_generator.generate_questions(topic, difficulty, profile)

    # 试题格式校验
    raw_questions = result.get("questions", [])
    valid_questions, q_issues = _validate_questions(raw_questions)
    result["questions"] = valid_questions

    log_msg = "⑤ 试题生成完成"
    if q_issues:
        log_msg += f"（{len(q_issues)}题格式异常已过滤: {'; '.join(q_issues[:3])}）"

    _broadcast(session_id, "试题生成 Agent", "completed", log_msg, 92)

    output = {
        "question_set": result,
        "decision_log": [log_msg],
    }
    _save_node_trace(session_id, "gen_questions", "试题生成 Agent",
                     {"topic": topic, "difficulty": difficulty},
                     {"question_count": len(result.get("questions", [])) if result else 0},
                     question_generator.collect_trace(), start)
    return output


async def gen_questions_node_no_debate(state: AgentState) -> dict:
    """试题生成节点（无辩论/无审核版本，用于消融实验）。"""
    session_id = state.get("session_id", "")
    _broadcast(session_id, "试题生成 Agent", "running", "正在生成试题...", 88)

    topic = state.get("topic", "")
    difficulty = state.get("difficulty", "beginner")
    profile = state.get("profile", {})

    result = await question_generator.generate_questions(topic, difficulty, profile)

    _broadcast(session_id, "试题生成 Agent", "completed", "试题生成完成", 92)

    return {
        "question_set": result,
        "decision_log": ["⑤ 试题生成完成（无辩论）"],
    }
