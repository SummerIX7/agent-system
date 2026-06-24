from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.store import get_session
from app.models.database import get_db
from app.models.learner import Learner
from app.models.schemas import QuestionSet
from app.models.user import User
from app.agents.question_generator import QuestionGeneratorAgent

router = APIRouter(prefix="/api/questions", tags=["试题生成"])

question_agent = QuestionGeneratorAgent()


@router.get("/{session_id}", response_model=QuestionSet)
async def get_questions(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """根据学习者画像动态生成试题（需登录）"""
    # 1. 从数据库获取 Learner 记录
    stmt = select(Learner).where(Learner.user_id == current_user.id)
    result = await db.execute(stmt)
    learner = result.scalar_one_or_none()

    # 2. 从内存 store 获取 session 数据
    session_data = get_session(session_id)
    profile = session_data.get("profile", {})

    # 3. 推断 topic 和 difficulty
    goals = profile.get("goals", [])
    if not goals and learner and learner.goals:
        goals = learner.goals
    topic = goals[0] if goals else "Python 数据分析基础"

    difficulty = profile.get("recommended_difficulty", "beginner")
    if difficulty == "beginner" and learner:
        assessment = learner.self_assessment or {}
        if assessment:
            levels = list(assessment.values())
            if any("advanced" in str(v).lower() or "高级" in str(v) for v in levels):
                difficulty = "advanced"
            elif any("intermediate" in str(v).lower() or "中级" in str(v) for v in levels):
                difficulty = "intermediate"

    # 4. 构建 profile dict 供 Agent 使用
    profile_dict = {
        "education_background": learner.education_background if learner else "",
        "major": learner.major if learner else "",
        "goals": goals,
        "knowledge_points": profile.get("knowledge_points", []),
        "blind_spots": profile.get("blind_spots", []),
    }

    # 5. 调用试题生成 Agent
    try:
        result_dict = await question_agent.generate_questions(
            topic=topic,
            difficulty=difficulty,
            profile=profile_dict,
            count=6,
        )
    except Exception as e:
        print(f"[警告] 试题生成失败: {e}")
        result_dict = {"topic": topic, "difficulty": difficulty, "questions": []}

    return QuestionSet(
        topic=result_dict.get("topic", topic),
        difficulty=result_dict.get("difficulty", difficulty),
        questions=result_dict.get("questions", []),
    )
