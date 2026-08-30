"""LangGraph 工作流装配器与运行入口。

- 主工作流（含审核纠偏 + 条件路由重试）：``build_workflow`` / ``get_workflow`` / ``run_workflow``
- 消融版本（无审核纠偏）：``build_workflow_no_debate`` / ``get_workflow_no_debate`` / ``run_workflow_no_debate``
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.core.career_tracks import get_career_track_from_input
from app.graph.nodes import (
    analyze_node,
    decide_node,
    finalize_node,
    finalize_node_no_debate,
    generate_node,
    plan_path_node,
    review_correct_node,
)
from app.graph.state import AgentState


# ──────────────────────────────────────────────
# 主工作流（含审核纠偏）
# ──────────────────────────────────────────────

def build_workflow() -> StateGraph:
    workflow = StateGraph(AgentState)

    # 5 个节点（试题生成已独立为按需接口）
    workflow.add_node("analyze", analyze_node)                # ① 学情分析
    workflow.add_node("plan_path", plan_path_node)            # ② 路径规划
    workflow.add_node("generate", generate_node)              # ③ 知识生成
    workflow.add_node("review_correct", review_correct_node)  # ③½ 审核纠偏
    workflow.add_node("finalize", finalize_node)              # 最终输出

    workflow.set_entry_point("analyze")
    workflow.add_edge("analyze", "plan_path")
    workflow.add_edge("plan_path", "generate")
    workflow.add_edge("generate", "review_correct")

    workflow.add_conditional_edges(
        "review_correct",
        decide_node,
        {
            "complete": "finalize",
            "retry": "generate",
        },
    )

    workflow.add_edge("finalize", END)

    return workflow.compile()


_workflow = None


def get_workflow():
    global _workflow
    if _workflow is None:
        _workflow = build_workflow()
    return _workflow


async def run_workflow(learner_input: dict, topic: str, session_id: str = "", profile: dict = None) -> dict:
    """运行完整 6 Agent 工作流（包含审核纠偏机制）"""
    workflow = get_workflow()

    if profile:
        learner_input = {**learner_input, **profile}

    track = get_career_track_from_input(learner_input)

    initial_state: AgentState = {
        "learner_input": learner_input,
        "topic": topic,
        "retry_count": 0,
        "generated_content": {},
        "review_results": {},
        "question_set": {},
        "learning_path": {},
        "final_resources": [],
        "feedback_history": [],
        "decision_log": [],
        "session_id": session_id,
        "career_track": track.code,
    }

    return await workflow.ainvoke(initial_state)


# ──────────────────────────────────────────────
# 无辩论版本（消融实验）
# ──────────────────────────────────────────────

def build_workflow_no_debate() -> StateGraph:
    """构建无审核版本的工作流（用于消融实验对比）"""
    workflow = StateGraph(AgentState)

    workflow.add_node("analyze", analyze_node)                # ① 学情分析
    workflow.add_node("plan_path", plan_path_node)            # ② 路径规划
    workflow.add_node("generate", generate_node)              # ③ 知识生成
    workflow.add_node("finalize", finalize_node_no_debate)    # 最终输出（无审核）

    workflow.set_entry_point("analyze")
    workflow.add_edge("analyze", "plan_path")
    workflow.add_edge("plan_path", "generate")
    workflow.add_edge("generate", "finalize")
    workflow.add_edge("finalize", END)

    return workflow.compile()


_workflow_no_debate = None


def get_workflow_no_debate():
    """获取无辩论工作流单例"""
    global _workflow_no_debate
    if _workflow_no_debate is None:
        _workflow_no_debate = build_workflow_no_debate()
    return _workflow_no_debate


async def run_workflow_no_debate(learner_input: dict, topic: str, session_id: str = "", profile: dict = None) -> dict:
    """
    运行无审核版本的工作流（用于消融实验）

    与 run_workflow 的区别：
    - 跳过审核纠偏节点，直接使用生成的内容
    - 不进行质量验证
    - 用于对比有/无审核纠偏机制对谬误率的影响
    """
    workflow = get_workflow_no_debate()

    if profile:
        learner_input = {**learner_input, **profile}

    track = get_career_track_from_input(learner_input)

    initial_state: AgentState = {
        "learner_input": learner_input,
        "topic": topic,
        "retry_count": 0,
        "generated_content": {},
        "review_results": {},
        "question_set": {},
        "learning_path": {},
        "final_resources": [],
        "feedback_history": [],
        "decision_log": [],
        "session_id": session_id,
        "career_track": track.code,
    }

    return await workflow.ainvoke(initial_state)
