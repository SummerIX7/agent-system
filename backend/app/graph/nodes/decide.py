"""⑥ 决策调度 Agent（条件边路由）。"""

from __future__ import annotations

from app.graph.nodes._common import MAX_RETRIES, _broadcast
from app.graph.state import AgentState


async def decide_node(state: AgentState) -> str:
    session_id = state.get("session_id", "")
    _broadcast(session_id, "决策调度 Agent", "running", "正在决策...", 95)

    review_results = state.get("review_results", {})
    retry_count = state.get("retry_count", 0)

    all_passed = all(r.get("passed", False) for r in review_results.values())
    has_degraded = any(r.get("degraded", False) for r in review_results.values())

    if all_passed:
        _broadcast(session_id, "决策调度 Agent", "completed", "审核通过，正在生成最终内容...", 82)
        return "complete"
    elif has_degraded or retry_count >= MAX_RETRIES:
        _broadcast(session_id, "决策调度 Agent", "completed", "审核完成（降级），正在生成最终内容...", 82)
        return "complete"
    else:
        _broadcast(session_id, "决策调度 Agent", "running", f"审核未通过（第{retry_count}次），触发重新生成...", 25)
        _broadcast(session_id, "知识生成 Agent", "running", "重新生成内容...", 30)
        return "retry"
