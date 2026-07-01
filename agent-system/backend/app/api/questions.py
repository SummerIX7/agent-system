from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.store import get_session, save_practice_state, get_practice_state, save_cached_questions, get_cached_questions, clear_cached_questions
from app.core.domains import get_domain_from_input, get_default_domain
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
    regenerate: bool = False,
):
    """根据学习者画像动态生成试题（需登录）。默认优先返回缓存，传 regenerate=true 重新生成。"""
    # ── 0. 先查缓存（非主动重新生成时） ──
    if not regenerate:
        cached = get_cached_questions(session_id)
        if cached and cached.get("questions"):
            print(f"[试题] 命中缓存，共 {len(cached['questions'])} 题")
            return QuestionSet(
                topic=cached.get("topic", ""),
                difficulty=cached.get("difficulty", "beginner"),
                questions=cached.get("questions", []),
            )

    # ── 1. 从数据库获取 Learner 记录 ──
    stmt = select(Learner).where(Learner.user_id == current_user.id)
    result = await db.execute(stmt)
    learner = result.scalar_one_or_none()

    # 2. 从内存 store 获取 session 数据
    session_data = get_session(session_id)
    profile = session_data.get("profile", {})

    # 3. 推断领域配置（支持多领域，不再硬编码 CNC）
    goals = profile.get("goals", [])
    if not goals and learner and learner.goals:
        goals = learner.goals

    # 构建输入数据用于推断领域
    input_data = {
        "domain": profile.get("domain", ""),
        "goals": goals,
    }
    domain = get_domain_from_input(input_data)

    # 构建 topic（基于领域和目标）
    raw_goal = goals[0] if goals else ""
    topic = f"{domain.name} - {raw_goal}" if raw_goal else f"{domain.name}基础"

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
        "domain": domain.code,
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
        result_dict = {"topic": topic, "difficulty": difficulty, "domain": domain.code, "questions": []}

    # ── 6. 写入缓存 ──
    cache_data = {
        "topic": result_dict.get("topic", topic),
        "difficulty": result_dict.get("difficulty", difficulty),
        "questions": result_dict.get("questions", []),
    }
    save_cached_questions(session_id, cache_data)
    # 新试题生成后清除旧进度
    save_practice_state(session_id, {})
    print(f"[试题] 生成并缓存完成，共 {len(cache_data['questions'])} 题")

    return QuestionSet(
        topic=cache_data["topic"],
        difficulty=cache_data["difficulty"],
        questions=cache_data["questions"],
    )


# ── 答题进度持久化 ──

class PracticeStateRequest(BaseModel):
    current_index: int = 0
    questions: list = []


@router.post("/practice/state/{session_id}")
async def save_state(session_id: str, state: PracticeStateRequest):
    """保存答题进度到 session"""
    save_practice_state(session_id, state.model_dump())
    return {"ok": True}


@router.get("/practice/state/{session_id}")
async def get_state(session_id: str):
    """恢复答题进度"""
    return get_practice_state(session_id)


@router.post("/practice/regenerate/{session_id}")
async def regenerate_questions(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """清除缓存并重新生成试题"""
    clear_cached_questions(session_id)
    save_practice_state(session_id, {})
    # 调用 get_questions 重新生成
    return await get_questions(session_id, db, current_user, regenerate=True)
