from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.schemas import FeedbackInput, FeedbackResponse
from app.core.llm import get_llm
from app.core.store import add_feedback

router = APIRouter(prefix="/api/feedback", tags=["交互反馈"])


async def generate_heuristic_question(topic: str, question: str, correct_answer: str) -> str:
    """生成苏格拉底式追问"""
    llm = get_llm()
    prompt = f"""基于以下题目，生成一个启发式追问，引导学习者自己思考出正确答案，而不是直接告诉答案。

[主题] {topic}
[题目] {question}
[正确答案] {correct_answer}

要求：
1. 不要直接说出正确答案
2. 通过提问引导学习者从不同角度思考
3. 简洁明了，一句话即可

只输出追问内容，不要其他文字。"""

    response = await llm.ainvoke(prompt)
    return response.content.strip()


@router.post("/", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: FeedbackInput,
    db: AsyncSession = Depends(get_db),
):
    """提交答题反馈，触发动态调整"""
    is_correct = feedback.user_answer.strip().lower() == feedback.correct_answer.strip().lower()
    correctness = 1.0 if is_correct else 0.0

    # 生成苏格拉底式追问（答错时）
    heuristic = None
    if not is_correct:
        heuristic = await generate_heuristic_question(
            feedback.topic, feedback.question, feedback.correct_answer
        )

    # 存入 store
    add_feedback(feedback.session_id, {
        "topic": feedback.topic,
        "question": feedback.question,
        "user_answer": feedback.user_answer,
        "correct_answer": feedback.correct_answer,
        "is_correct": is_correct,
        "correctness": correctness,
        "heuristic_question": heuristic,
    })

    return FeedbackResponse(
        is_correct=is_correct,
        correct_answer=feedback.correct_answer,
        heuristic_question=heuristic,
        topic=feedback.topic,
        correctness=correctness,
    )
