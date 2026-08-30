"""③½ 审核纠偏 Agent 节点（双视角审查 + 修正）。"""

from __future__ import annotations

import time as _time

from app.graph.nodes._common import (
    MAX_RETRIES,
    _broadcast,
    _save_node_trace,
    _stage_learning_topic,
    review_agent,
)
from app.graph.state import AgentState


async def review_correct_node(state: AgentState) -> dict:
    session_id = state.get("session_id", "")
    start = _time.time()
    review_agent._trace_agent_name = "审核纠偏 Agent"
    review_agent._trace_calls = []

    topic = state.get("topic", "")
    learning_path = state.get("learning_path", {})
    stage_one = next((s for s in learning_path.get("path", []) if s.get("stage") == 1), None)
    if stage_one:
        topic = _stage_learning_topic(stage_one)
    generated = state.get("generated_content", {})
    retry_count = state.get("retry_count", 0)
    review_results = {}

    _broadcast(session_id, "审核纠偏 Agent", "running", "启动双视角审核纠偏...", 59)

    for content_type, content in generated.items():
        progress = 59 + len(review_results) * 5

        # 跳过非文本内容
        if content_type == "test":
            review_results[content_type] = {
                "passed": True, "score": 1.0, "issues": [],
                "final_content": content, "correction_applied": False,
            }
            continue

        # 达到最大重试次数，标记为降级
        if retry_count >= MAX_RETRIES:
            review_results[content_type] = {
                "passed": False, "score": 0, "issues": [],
                "final_content": content, "correction_applied": False,
                "degraded": True,
            }
            continue

        _broadcast(session_id, "审核纠偏 Agent", "running",
                   f"审核+纠偏: {content_type}...", progress)

        try:
            result = await review_agent.corrective_review(content, topic)
            review_results[content_type] = result
        except Exception as e:  # noqa: BLE001
            review_results[content_type] = {
                "passed": False, "score": 0,
                "issues": [f"审核纠偏异常: {str(e)}"],
                "final_content": content, "correction_applied": False,
            }

    all_passed = all(r.get("passed", False) for r in review_results.values())
    has_degraded = any(r.get("degraded", False) for r in review_results.values())
    new_retry = retry_count if all_passed else retry_count + 1

    # 本轮重试耗尽 → 标记为降级
    if not all_passed and new_retry >= MAX_RETRIES and not has_degraded:
        has_degraded = True
        for ct in review_results:
            if not review_results[ct].get("passed", False):
                review_results[ct]["degraded"] = True

    # 构建调试日志
    debug_lines = []
    for ct, r in review_results.items():
        status = "通过" if r.get("passed") else ("降级" if r.get("degraded") else "未通过")
        score = r.get("score", 0)
        issue_count = len(r.get("issues", []))
        corrected = "已修正" if r.get("correction_applied") else "未修正"
        debug_lines.append(f"  {ct}: {status} | 评分={score:.2f} | 问题数={issue_count} | {corrected}")
    debug_log = f"③½ 审核纠偏 第{new_retry}次 | {'全部通过' if all_passed else '需重试'}\n" + "\n".join(debug_lines)

    # 广播
    if has_degraded:
        _broadcast(session_id, "审核纠偏 Agent", "completed",
                   f"审核完成：已降级（超过最大重试{MAX_RETRIES}次）", 82)
        _broadcast(session_id, "知识生成 Agent", "completed", "内容已生成（降级通过）", 65)
    elif all_passed:
        _broadcast(session_id, "审核纠偏 Agent", "completed", "审核完成：全部内容通过", 82)
        _broadcast(session_id, "知识生成 Agent", "completed", "内容已生成并通过审核", 65)
    else:
        _broadcast(session_id, "审核纠偏 Agent", "completed",
                   f"审核完成：有内容未通过（第{new_retry}次），触发重新生成", 82)
        _broadcast(session_id, "知识生成 Agent", "error", "内容未通过审核，需重新生成", 60)

    # 存储调试信息到 session
    if session_id:
        try:
            from app.core.store import add_agent_log
            add_agent_log(session_id, {
                "agent_name": "审核纠偏 Agent",
                "status": "completed",
                "message": debug_log,
                "progress": 82,
            })
        except Exception:  # noqa: BLE001
            pass

    output = {
        "review_results": review_results,
        "retry_count": new_retry,
        "decision_log": [debug_log],
    }
    _save_node_trace(session_id, "review_correct", "审核纠偏 Agent",
                     {"content_types": list(generated.keys()), "retry_count": retry_count, "topic": topic},
                     {"all_passed": all_passed, "has_degraded": has_degraded, "new_retry": new_retry,
                      "results_summary": {ct: {"passed": r.get("passed"), "score": r.get("score"),
                                               "issues": len(r.get("issues", [])),
                                               "corrected": r.get("correction_applied")}
                                          for ct, r in review_results.items()}},
                     review_agent.collect_trace(), start)
    return output
