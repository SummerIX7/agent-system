from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.schemas import FeedbackInput, FeedbackResponse
from app.models.agent_state import FeedbackRecord
from app.core.llm import get_llm
from app.core.store import add_feedback, get_session

router = APIRouter(prefix="/api/feedback", tags=["交互反馈"])


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

    prompt = f"""基于以下题目，生成一个启发式追问（第 {round} 轮）。

[主题] {topic}
[题目] {question}
[正确答案] {correct_answer}
[追问风格] {style}
{context_part}

要求：
1. 简洁明了，一到两句话
2. 第 {round} 轮追问，难度逐轮降低

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

    return FeedbackResponse(
        is_correct=is_correct,
        correct_answer=feedback.correct_answer,
        heuristic_question=heuristic,
        topic=feedback.topic,
        correctness=correctness,
        round=current_round,
        reveal_answer=reveal,
    )
