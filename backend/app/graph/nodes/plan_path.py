"""② 路径规划 Agent 节点。"""

from __future__ import annotations

import time as _time

from app.graph.nodes._common import _broadcast, _save_node_trace, path_planner
from app.graph.state import AgentState


async def plan_path_node(state: AgentState) -> dict:
    session_id = state.get("session_id", "")
    start = _time.time()
    path_planner._trace_agent_name = "路径规划 Agent"
    path_planner._trace_calls = []

    _broadcast(session_id, "路径规划 Agent", "running", "正在规划学习路径...", 20)

    existing_path = state.get("learning_path")
    feedback_history = state.get("feedback_history", [])

    if existing_path and feedback_history:
        result = await path_planner.adjust_path(existing_path, feedback_history[-1])
    else:
        result = await path_planner.plan_path(
            profile=state.get("profile", {}),
            topic=state.get("topic", ""),
        )

    _broadcast(session_id, "路径规划 Agent", "completed", "学习路径规划完成", 30)

    output = {
        "learning_path": result,
        "decision_log": ["② 路径规划完成"],
    }
    _save_node_trace(session_id, "plan_path", "路径规划 Agent",
                     {"profile": state.get("profile", {}), "topic": state.get("topic", "")},
                     {"learning_path_stages": len(result.get("path", [])) if result else 0},
                     path_planner.collect_trace(), start)
    return output
