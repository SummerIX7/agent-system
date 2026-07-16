"""Workflow 节点共享工具与常量。

集中托管：
- Agent 单例（避免多次实例化）
- 广播与 trace 记录辅助函数
- 学习节点主题提取、试题格式校验、节点状态初始化
- MAX_RETRIES 常量
"""

from __future__ import annotations

import logging
import time as _time

from app.agents.diagnosis import DiagnosisAgent
from app.agents.generation import GenerationAgent
from app.agents.orchestrator import DecisionOrchestrator
from app.agents.path_planner import PathPlannerAgent
from app.agents.question_generator import QuestionGeneratorAgent
from app.agents.review import ReviewAgent

logger = logging.getLogger(__name__)

# ── Agent 实例（模块级单例） ──
diagnosis_agent = DiagnosisAgent()
path_planner = PathPlannerAgent()
generation_agent = GenerationAgent()
review_agent = ReviewAgent()
question_generator = QuestionGeneratorAgent()
orchestrator = DecisionOrchestrator()

# 最大重试次数
MAX_RETRIES = 3


def _broadcast(session_id: str, agent: str, status: str, message: str, progress: float = 0):
    """广播 Agent 状态"""
    if session_id:
        try:
            from app.api.ws import broadcast_agent_status
            broadcast_agent_status(session_id, agent, status, message, progress)
        except Exception:  # noqa: BLE001
            pass


def _save_node_trace(session_id: str, node: str, agent_name: str,
                     input_data: dict, output_data: dict,
                     llm_calls: list, start_time: float):
    """保存节点追踪记录"""
    if not session_id:
        return
    try:
        from app.core.store import add_trace_entry
        add_trace_entry(session_id, {
            "node": node,
            "agent_name": agent_name,
            "input": input_data,
            "output": output_data,
            "llm_calls": llm_calls,
            "duration_ms": round((_time.time() - start_time) * 1000),
        })
    except Exception:  # noqa: BLE001
        pass


def _stage_learning_topic(stage_data: dict) -> str:
    """把一个学习节点压缩成资源/试题生成使用的主题。"""
    title = stage_data.get("title") or f"节点{stage_data.get('stage', '')}"
    topics = [str(t) for t in stage_data.get("topics", []) if t]
    if topics:
        return f"{title}（{'、'.join(topics)}）"
    return title


def _prepare_stage_states(learning_path: dict) -> list[dict]:
    """初始化学习节点状态；资源在协同阶段一次性生成，因此全部标记 has_resources。"""
    path_stages = learning_path.get("path", [])
    for stage_data in path_stages:
        stage_data.setdefault("completed", False)
        stage_data.setdefault("basic_test_passed", False)
        stage_data.setdefault("advanced_test_passed", False)
        stage_data["has_resources"] = True
    return path_stages


def _validate_questions(questions: list) -> tuple[list, list]:
    """
    试题格式校验：检查题目结构、选项合法性、答案是否在选项中。
    不依赖 LLM，纯规则检查，防止生成明显错误的试题。
    返回 (valid_questions, issues)
    """
    issues = []
    valid = []
    valid_letters = {"A", "B", "C", "D", "E", "F"}

    for i, q in enumerate(questions):
        q_type = q.get("question_type", "")
        q_issues = []

        # 必填字段检查
        if not q.get("question"):
            q_issues.append("缺少题目内容")
        if not q_type:
            q_issues.append("缺少题目类型")

        if q_type == "multiple_choice":
            options = q.get("options", [])
            if len(options) < 3:
                q_issues.append(f"选项数量不足({len(options)}，至少3个)")
            if not q.get("correct_answer") or q["correct_answer"] not in valid_letters:
                q_issues.append(f"正确答案格式无效({q.get('correct_answer')})")
            elif q["correct_answer"] in valid_letters:
                idx = ord(q["correct_answer"]) - 65
                if idx >= len(options):
                    q_issues.append(f"正确答案索引({q['correct_answer']})超出选项范围")
        elif q_type == "true_false":
            options = q.get("options", [])
            if "正确" not in str(options) and "错误" not in str(options):
                q_issues.append("判断题缺少正确/错误选项")
            if q.get("correct_answer") not in ("正确", "错误"):
                q_issues.append(f"判断题答案应为正确/错误，实际为: {q.get('correct_answer')}")
        elif q_type == "practical":
            if not q.get("explanation"):
                q_issues.append("实操缺少评分标准(explanation)")
        else:
            q_issues.append(f"未知题型: {q_type}")

        if q_issues:
            issues.append(f"题目{i+1}: {'; '.join(q_issues)}")
        valid.append(q)

    return valid, issues
