from langgraph.graph import END, StateGraph

from app.agents.diagnosis import DiagnosisAgent
from app.agents.path_planner import PathPlannerAgent
from app.agents.generation import GenerationAgent
from app.agents.debate import DebateManager
from app.agents.judge import JudgeAgent
from app.agents.question_generator import QuestionGeneratorAgent
from app.agents.orchestrator import DecisionOrchestrator
from app.graph.state import AgentState

# Agent 实例
diagnosis_agent = DiagnosisAgent()
path_planner = PathPlannerAgent()
generation_agent = GenerationAgent()
debate_manager = DebateManager()
judge_agent = JudgeAgent()
question_generator = QuestionGeneratorAgent()
orchestrator = DecisionOrchestrator()


def _broadcast(session_id: str, agent: str, status: str, message: str, progress: float = 0):
    """广播 Agent 状态"""
    if session_id:
        try:
            from app.api.ws import broadcast_agent_status
            broadcast_agent_status(session_id, agent, status, message, progress)
        except Exception:
            pass


# ──────────────────────────────────────────────
# ① 学情分析 Agent
# ──────────────────────────────────────────────
async def analyze_node(state: AgentState) -> dict:
    session_id = state.get("session_id", "")
    _broadcast(session_id, "学情分析 Agent", "running", "正在分析学习者画像...", 5)

    result = await diagnosis_agent.run(state.get("learner_input", {}))

    _broadcast(session_id, "学情分析 Agent", "completed", "学情分析完成", 15)

    return {
        "profile": result.get("profile", {}),
        "difficulty": result.get("difficulty", "beginner"),
        "decision_log": ["① 学情分析完成"],
    }


# ──────────────────────────────────────────────
# ② 路径规划 Agent
# ──────────────────────────────────────────────
async def plan_path_node(state: AgentState) -> dict:
    session_id = state.get("session_id", "")
    _broadcast(session_id, "路径规划 Agent", "running", "正在规划学习路径...", 20)

    # 如果有反馈历史，调整路径；否则生成新路径
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

    return {
        "learning_path": result,
        "decision_log": ["② 路径规划完成"],
    }


# ──────────────────────────────────────────────
# ③ 知识生成 Agent
# ──────────────────────────────────────────────
async def generate_node(state: AgentState) -> dict:
    session_id = state.get("session_id", "")
    topic = state.get("topic", "")
    profile = state.get("profile", {})
    generated = {}
    logs = []

    _broadcast(session_id, "知识生成 Agent", "running", "正在生成讲义...", 35)
    generated["lecture"] = await generation_agent.generate_lecture_notes(topic, profile)
    logs.append("讲义生成完成")

    _broadcast(session_id, "知识生成 Agent", "running", "正在生成实验指导...", 45)
    generated["guide"] = await generation_agent.generate_practical_guide(topic, profile)
    logs.append("实验指导生成完成")

    _broadcast(session_id, "知识生成 Agent", "running", "正在生成项目案例...", 55)
    generated["project"] = await generation_agent.generate_project_case(topic, profile)
    logs.append("项目案例生成完成")

    # 注意：不在这里标记完成，因为还需要辩论验证
    _broadcast(session_id, "知识生成 Agent", "running", "内容已生成，等待辩论验证...", 58)

    return {
        "generated_content": generated,
        "decision_log": [f"③ 知识生成完成: {', '.join(logs)}"],
    }


# ──────────────────────────────────────────────
# ④ 审核纠偏 Agent（辩论 + 独立裁判）
# ──────────────────────────────────────────────
async def debate_node(state: AgentState) -> dict:
    session_id = state.get("session_id", "")
    topic = state.get("topic", "")
    generated = state.get("generated_content", {})
    retry_count = state.get("retry_count", 0)
    debate_results = {}
    all_rounds = []

    _broadcast(session_id, "审核纠偏 Agent", "running", "启动辩论机制...", 62)

    for content_type, content in generated.items():
        progress = 62 + len(debate_results) * 3
        _broadcast(session_id, "审核纠偏 Agent", "running",
                   f"正在审核: {content_type}...", progress)

        # 跳过非文本内容
        if content_type == "test":
            debate_results[content_type] = {"passed": True, "reason": "试题不参与辩论", "final_content": content}
            continue

        # 达到最大重试次数，强制通过
        if retry_count >= 3:
            debate_results[content_type] = {"passed": True, "reason": "达到最大重试次数，强制通过", "final_content": content}
            continue

        # 第1-2轮：辩论（审核质疑 → 生成反驳）
        debate_result = await debate_manager.run_debate(content, topic, content_type)

        all_rounds.append({
            "content_type": content_type,
            "challenge_issues": debate_result.challenge_issues,
            "defend_responses": debate_result.defend_responses,
        })

        # 第3轮：独立裁判判决
        _broadcast(session_id, "裁判 Agent", "running", f"正在判决: {content_type}...", 75)
        judge_result = await judge_agent.run(
            original_content=debate_result.original_content,
            topic=topic,
            content_type=content_type,
            challenge_issues=debate_result.challenge_issues,
            defend_responses=debate_result.defend_responses,
            revised_content=debate_result.revised_content,
        )

        final_content = debate_result.revised_content if judge_result.get("adopted_side") == "defender" else content

        debate_results[content_type] = {
            "passed": judge_result.get("passed", True),
            "adopted_side": judge_result.get("adopted_side", "defender"),
            "reason": judge_result.get("reason", ""),
            "quality_score": judge_result.get("quality_score", 0),
            "final_content": final_content,
        }

    # 检查是否全部通过，未通过则递增重试计数
    all_passed = all(r.get("passed", False) for r in debate_results.values())
    new_retry = retry_count if all_passed else retry_count + 1

    if not all_passed:
        _broadcast(session_id, "裁判 Agent", "completed", f"判决：有内容未通过（第{new_retry}次），将重新生成", 85)
        _broadcast(session_id, "审核纠偏 Agent", "completed", f"辩论结束：未通过，需重新生成", 82)
        _broadcast(session_id, "知识生成 Agent", "error", "内容未通过验证，需重新生成", 60)
    else:
        _broadcast(session_id, "裁判 Agent", "completed", "判决：所有内容通过", 85)
        _broadcast(session_id, "审核纠偏 Agent", "completed", "辩论结束：所有内容通过验证", 82)
        _broadcast(session_id, "知识生成 Agent", "completed", "内容生成并通过验证", 65)

    return {
        "debate_results": debate_results,
        "debate_rounds": all_rounds,
        "retry_count": new_retry,
        "decision_log": [f"④ 辩论+裁判完成（{'通过' if all_passed else f'未通过，第{new_retry}次'}）"],
    }


# ──────────────────────────────────────────────
# ⑤ 试题生成 Agent
# ──────────────────────────────────────────────
async def gen_questions_node(state: AgentState) -> dict:
    session_id = state.get("session_id", "")
    _broadcast(session_id, "试题生成 Agent", "running", "正在生成试题...", 88)

    topic = state.get("topic", "")
    difficulty = state.get("difficulty", "beginner")
    profile = state.get("profile", {})

    result = await question_generator.generate_questions(topic, difficulty, profile)

    _broadcast(session_id, "试题生成 Agent", "completed", "试题生成完成", 92)

    return {
        "question_set": result,
        "decision_log": ["⑤ 试题生成完成"],
    }


# ──────────────────────────────────────────────
# ⑥ 决策调度 Agent
# ──────────────────────────────────────────────
async def decide_node(state: AgentState) -> str:
    session_id = state.get("session_id", "")
    _broadcast(session_id, "决策调度 Agent", "running", "正在决策...", 95)

    debate_results = state.get("debate_results", {})
    retry_count = state.get("retry_count", 0)

    all_passed = all(r.get("passed", False) for r in debate_results.values())

    if all_passed or retry_count >= 3:
        _broadcast(session_id, "决策调度 Agent", "completed", "工作流完成", 100)
        return "complete"
    else:
        _broadcast(session_id, "决策调度 Agent", "running", f"辩论未通过（第{retry_count}次），触发重新生成...", 25)
        # 重置相关 Agent 状态，准备重试
        _broadcast(session_id, "知识生成 Agent", "running", "重新生成内容...", 30)
        return "retry"


# ──────────────────────────────────────────────
# 最终输出
# ──────────────────────────────────────────────
async def finalize_node(state: AgentState) -> dict:
    final_resources = []

    # 使用辩论通过的最终内容
    debate_results = state.get("debate_results", {})
    for content_type, debate in debate_results.items():
        final_resources.append({
            "type": content_type,
            "content": debate.get("final_content", ""),
            "topic": state.get("topic", ""),
            "difficulty": state.get("difficulty", "beginner"),
        })

    # 添加试题
    question_set = state.get("question_set", {})
    if question_set.get("questions"):
        final_resources.append({
            "type": "test",
            "content": question_set,
            "topic": state.get("topic", ""),
            "difficulty": state.get("difficulty", "beginner"),
        })

    # 添加学习路径
    learning_path = state.get("learning_path", {})
    if learning_path:
        final_resources.append({
            "type": "learning_path",
            "content": learning_path,
            "topic": state.get("topic", ""),
            "difficulty": state.get("difficulty", "beginner"),
        })

    return {
        "final_resources": final_resources,
        "decision_log": ["⑥ 工作流完成"],
    }


# ──────────────────────────────────────────────
# 构建工作流
# ──────────────────────────────────────────────
def build_workflow() -> StateGraph:
    workflow = StateGraph(AgentState)

    # 6 个主节点 + finalize
    workflow.add_node("analyze", analyze_node)            # ① 学情分析
    workflow.add_node("plan_path", plan_path_node)        # ② 路径规划
    workflow.add_node("generate", generate_node)          # ③ 知识生成
    workflow.add_node("debate", debate_node)              # ④ 审核纠偏（辩论）
    workflow.add_node("gen_questions", gen_questions_node) # ⑤ 试题生成
    workflow.add_node("finalize", finalize_node)          # 最终输出

    # 流程
    workflow.set_entry_point("analyze")
    workflow.add_edge("analyze", "plan_path")
    workflow.add_edge("plan_path", "generate")
    workflow.add_edge("generate", "debate")

    # 辩论后条件路由
    workflow.add_conditional_edges(
        "debate",
        decide_node,
        {
            "complete": "gen_questions",
            "retry": "generate",
        },
    )

    workflow.add_edge("gen_questions", "finalize")
    workflow.add_edge("finalize", END)

    return workflow.compile()


_workflow = None


def get_workflow():
    global _workflow
    if _workflow is None:
        _workflow = build_workflow()
    return _workflow


async def run_workflow(learner_input: dict, topic: str, session_id: str = "", profile: dict = None) -> dict:
    """运行完整 6 Agent 工作流"""
    workflow = get_workflow()

    # 如果传入了 profile，合并到 learner_input
    if profile:
        learner_input = {**learner_input, **profile}

    initial_state: AgentState = {
        "learner_input": learner_input,
        "topic": topic,
        "retry_count": 0,
        "generated_content": {},
        "debate_results": {},
        "debate_rounds": [],
        "question_set": {},
        "learning_path": {},
        "final_resources": [],
        "feedback_history": [],
        "decision_log": [],
        "session_id": session_id,
    }

    result = await workflow.ainvoke(initial_state)
    return result
