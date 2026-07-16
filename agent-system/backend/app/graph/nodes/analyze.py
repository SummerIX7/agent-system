"""① 学情分析 Agent 节点。"""

from __future__ import annotations

import time as _time

from app.graph.nodes._common import _broadcast, _save_node_trace, diagnosis_agent
from app.graph.state import AgentState


async def analyze_node(state: AgentState) -> dict:
    session_id = state.get("session_id", "")
    start = _time.time()
    diagnosis_agent._trace_agent_name = "学情分析 Agent"
    diagnosis_agent._trace_calls = []

    _broadcast(session_id, "学情分析 Agent", "running", "正在分析学习者画像...", 5)

    result = await diagnosis_agent.run(state.get("learner_input", {}))

    _broadcast(session_id, "学情分析 Agent", "completed", "学情分析完成", 15)

    output = {
        "profile": result.get("profile", {}),
        "difficulty": result.get("difficulty", "beginner"),
        "decision_log": ["① 学情分析完成"],
    }
    _save_node_trace(session_id, "analyze", "学情分析 Agent",
                     {"learner_input": state.get("learner_input", {})},
                     {"difficulty": output["difficulty"]},
                     diagnosis_agent.collect_trace(), start)
    return output
