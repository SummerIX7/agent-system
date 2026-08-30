"""③ 知识生成 Agent 节点。"""

from __future__ import annotations

import time as _time

from app.core.career_tracks import get_career_track_from_input
from app.graph.nodes._common import (
    _broadcast,
    _save_node_trace,
    _stage_learning_topic,
    generation_agent,
)
from app.graph.state import AgentState


async def generate_node(state: AgentState) -> dict:
    session_id = state.get("session_id", "")
    start = _time.time()
    generation_agent._trace_agent_name = "知识生成 Agent"
    generation_agent._trace_calls = []

    topic = state.get("topic", "")
    learning_path = state.get("learning_path", {})
    stage_one = next((s for s in learning_path.get("path", []) if s.get("stage") == 1), None)
    if stage_one:
        topic = _stage_learning_topic(stage_one)
    profile = state.get("profile", {})
    career_code = state.get("career_track", "operator")
    track = get_career_track_from_input({"career_track": career_code, **profile})
    retry_count = state.get("retry_count", 0)
    generated = {}
    logs = []

    # 重试时收集上一轮审核反馈，注入到生成 prompt 中
    retry_context = ""
    if retry_count > 0:
        issues_parts = []
        review_results = state.get("review_results", {})
        for ct, review in review_results.items():
            if review.get("issues"):
                for issue in review["issues"]:
                    issues_parts.append(f"[审核-{ct}] {issue}")
        if issues_parts:
            retry_context = "\n".join(issues_parts)
            logs.append(f"注入上一轮反馈: {len(issues_parts)} 条问题")

    _broadcast(session_id, "知识生成 Agent", "running",
               "正在重新生成讲义（已注入审核反馈）..." if retry_context else "正在生成讲义...", 35)
    generated["lecture"] = await generation_agent.generate_lecture_notes(topic, profile, track, retry_context)
    logs.append("讲义生成完成")

    _broadcast(session_id, "知识生成 Agent", "running",
               "正在重新生成实验指导..." if retry_context else "正在生成实验指导...", 45)
    generated["guide"] = await generation_agent.generate_practical_guide(topic, profile, track, retry_context)
    logs.append("实验指导生成完成")

    _broadcast(session_id, "知识生成 Agent", "running",
               "正在重新生成项目案例..." if retry_context else "正在生成项目案例...", 55)
    generated["project"] = await generation_agent.generate_project_case(topic, profile, track, retry_context)
    logs.append("项目案例生成完成")

    _broadcast(session_id, "知识生成 Agent", "running", "内容已生成，等待审核验证...", 58)

    output = {
        "generated_content": generated,
        "decision_log": [f"③ 知识生成完成: {', '.join(logs)}"],
    }
    _save_node_trace(session_id, "generate", "知识生成 Agent",
                     {"topic": topic, "retry_count": retry_count, "has_retry_context": bool(retry_context)},
                     {"content_types": list(generated.keys()),
                      "lecture_len": len(generated.get("lecture", "")),
                      "guide_len": len(generated.get("guide", "")),
                      "project_len": len(generated.get("project", ""))},
                     generation_agent.collect_trace(), start)
    return output
