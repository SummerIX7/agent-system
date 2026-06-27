import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.schemas import FeedbackInput, FeedbackResponse, PracticalFeedbackInput, PracticalFeedbackResponse
from app.models.agent_state import FeedbackRecord
from app.models.learner import Learner
from app.core.llm import get_llm
from app.core.store import add_feedback, get_session, get_all_sessions
from app.agents.orchestrator import DecisionOrchestrator

router = APIRouter(prefix="/api/feedback", tags=["交互反馈"])

# 决策调度 Agent（用于学习路径调整）
orchestrator = DecisionOrchestrator()


async def generate_heuristic_question(
    topic: str,
    question: str,
    correct_answer: str,
    round: int = 1,
    previous_context: str = "",
) -> str:
    """生成苏格拉底式追问（支持多轮，逐层降级）"""
    llm = get_llm()

    if round == 1:
        style = "通过提问引导学习者从不同角度思考，不要说出答案"
    elif round == 2:
        style = "用生活中的类比或比喻来启发学习者，让抽象概念变得具体，仍然不要直接说出答案"
    else:
        style = "直接给出提示线索，明确指出正确答案的关键原因"

    context_part = ""
    if previous_context:
        context_part = f"\n[之前的追问] {previous_context}\n学习者仍然没有理解，请换一个角度。"

    prompt = f"""你是一位数控加工（CNC）领域的教学专家。基于以下数控相关的题目，生成一个启发式追问（第 {round} 轮）。

[主题] {topic}
[题目] {question}
[正确答案] {correct_answer}
[追问风格] {style}
{context_part}

要求：
1. 简洁明了，一到两句话
2. 第 {round} 轮追问，难度逐轮降低
3. 结合数控加工的实际场景来引导思考（如机床操作、切削过程、G 代码执行等）

只输出追问内容，不要其他文字。"""

    response = await llm.ainvoke(prompt)
    return response.content.strip()


@router.post("/", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: FeedbackInput,
    db: AsyncSession = Depends(get_db),
):
    """提交答题反馈，支持多轮苏格拉底式追问"""
    MAX_ROUNDS = 3
    is_correct = feedback.user_answer.strip().lower() == feedback.correct_answer.strip().lower()
    correctness = 1.0 if is_correct else 0.0
    current_round = feedback.round
    reveal = False
    heuristic = None

    if not is_correct:
        if current_round >= MAX_ROUNDS:
            reveal = True
            heuristic = None
        else:
            try:
                heuristic = await generate_heuristic_question(
                    feedback.topic,
                    feedback.question,
                    feedback.correct_answer,
                    round=current_round,
                    previous_context=feedback.heuristic_context,
                )
            except Exception as e:
                print(f"[警告] 启发式追问生成失败: {e}")

    session = get_session(feedback.session_id)
    learner_id = session.get("learner_id", "")

    record = FeedbackRecord(
        session_id=feedback.session_id,
        learner_id=learner_id or "unknown",
        topic=feedback.topic,
        question=feedback.question,
        user_answer=feedback.user_answer,
        correct_answer=feedback.correct_answer,
        is_correct=correctness,
        heuristic_question=heuristic,
    )
    db.add(record)
    await db.flush()

    add_feedback(feedback.session_id, {
        "topic": feedback.topic,
        "question": feedback.question,
        "user_answer": feedback.user_answer,
        "correct_answer": feedback.correct_answer,
        "is_correct": is_correct,
        "correctness": correctness,
        "heuristic_question": heuristic,
        "round": current_round,
    })

    # P2-2: 学习路径二次更新闭环
    # 根据答题反馈动态调整学习路径，并持久化到数据库
    if learner_id:
        try:
            # 获取当前学习路径
            current_path = session.get("learning_path", {})
            feedback_history = session.get("feedback", [])

            if current_path and feedback_history:
                # 调用决策调度 Agent 调整学习路径
                adjusted_path = await orchestrator.adjust_learning_path(
                    current_path,
                    feedback_history
                )

                # 如果路径有变化，持久化到数据库
                if adjusted_path != current_path:
                    # 更新内存 store
                    session["learning_path"] = adjusted_path

                    # 持久化到数据库
                    stmt = select(Learner).where(Learner.id == learner_id)
                    result = await db.execute(stmt)
                    learner = result.scalar_one_or_none()
                    if learner:
                        learner.learning_path = adjusted_path
                        await db.flush()
                        print(f"[学习路径] 已根据答题反馈调整并持久化: learner_id={learner_id}")
        except Exception as e:
            print(f"[警告] 学习路径调整失败: {e}")
            # 路径调整失败不影响反馈返回

    return FeedbackResponse(
        is_correct=is_correct,
        correct_answer=feedback.correct_answer,
        heuristic_question=heuristic,
        topic=feedback.topic,
        correctness=correctness,
        round=current_round,
        reveal_answer=reveal,
    )


# ──────────────────────────────────────────────
# 实操题批改
# ──────────────────────────────────────────────

async def grade_practical_answer(
    topic: str,
    question: str,
    user_answer: str,
    correct_answer: str,
    explanation: str,
) -> dict:
    """使用 LLM 对实操题答案进行语义批改"""
    llm = get_llm()

    prompt = f"""你是一位数控加工（CNC）领域的考评专家。请对学习者的实操题答案进行批改评分。

[题目]
{question}

[参考答案]
{correct_answer}

[评分标准]
{explanation if explanation else "按数控加工的规范性、正确性、完整性评分"}

[学习者答案]
{user_answer}

[批改要求]
1. 对比学习者答案与参考答案，从以下维度评分：
   - 关键步骤/代码是否正确（核心得分点）
   - 工艺参数是否合理（切削参数、刀具选择等）
   - 是否遗漏重要步骤或存在安全隐患
   - 整体逻辑是否清晰完整
2. 给出 0-100 的综合评分
3. 列出关键要点（正确的和需要改进的）

输出 JSON 格式：
{{
    "score": 85,
    "feedback": "详细的批改反馈，说明哪些地方做得好，哪些需要改进",
    "key_points": ["要点1", "要点2", "要点3"]
}}

只输出 JSON，不要其他文字。"""

    response = await llm.ainvoke(prompt)
    try:
        result = json.loads(response.content.strip().strip("```json").strip("```"))
    except (json.JSONDecodeError, AttributeError):
        result = {
            "score": 50,
            "feedback": "批改结果解析失败，请参考标准答案自行对照。",
            "key_points": [],
        }
    return result


@router.post("/practical", response_model=PracticalFeedbackResponse)
async def submit_practical_feedback(
    feedback: PracticalFeedbackInput,
    db: AsyncSession = Depends(get_db),
):
    """提交实操题答案，由 LLM Agent 批改"""
    # 1. 调用 LLM 批改
    try:
        grading = await grade_practical_answer(
            topic=feedback.topic,
            question=feedback.question,
            user_answer=feedback.user_answer,
            correct_answer=feedback.correct_answer,
            explanation=feedback.explanation,
        )
    except Exception as e:
        print(f"[警告] 实操题批改失败: {e}")
        grading = {
            "score": 0,
            "feedback": f"批改服务暂时不可用: {str(e)}",
            "key_points": [],
        }

    score = grading.get("score", 0)
    is_correct = score >= 60

    # 2. 存入数据库（需要有效的 learner_id）
    session = get_session(feedback.session_id)
    learner_id = session.get("learner_id", "")

    if learner_id:
        record = FeedbackRecord(
            session_id=feedback.session_id,
            learner_id=learner_id,
            topic=feedback.topic,
            question=feedback.question[:500],
            user_answer=feedback.user_answer,
            correct_answer=feedback.correct_answer,
            is_correct=1.0 if is_correct else 0.0,
            heuristic_question=None,
        )
        db.add(record)
        await db.flush()

    # 3. 存入内存 store
    add_feedback(feedback.session_id, {
        "topic": feedback.topic,
        "question": feedback.question,
        "user_answer": feedback.user_answer,
        "correct_answer": feedback.correct_answer,
        "is_correct": is_correct,
        "score": score,
        "feedback": grading.get("feedback", ""),
        "key_points": grading.get("key_points", []),
    })

    # 4. 返回结果
    return PracticalFeedbackResponse(
        score=score,
        is_correct=is_correct,
        feedback=grading.get("feedback", ""),
        key_points=grading.get("key_points", []),
        reference_answer=feedback.correct_answer,
    )
