from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.models.database import get_db
from app.models.schemas import LearnerProfileInput, LearnerProfile
from app.models.learner import Learner
from app.models.user import User
from app.agents.diagnosis import DiagnosisAgent
from app.core.store import update_session

router = APIRouter(prefix="/api/profile", tags=["学习者画像"])

diagnosis_agent = DiagnosisAgent()


@router.post("/", response_model=LearnerProfile)
async def create_profile(
    profile_input: LearnerProfileInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """提交学习者画像，触发学情诊断（需登录）"""
    # 1. 检查是否已有画像，有则更新
    stmt = select(Learner).where(Learner.user_id == current_user.id)
    result = await db.execute(stmt)
    existing_learner = result.scalar_one_or_none()

    # 2. 调用诊断 Agent
    try:
        diag_result = await diagnosis_agent.run(profile_input.model_dump())
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=f"LLM 服务不可用: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"诊断失败: {e}")

    profile_data = diag_result.get("profile", {})
    session_id = f"user-{current_user.id}"

    if existing_learner:
        # 更新已有画像
        existing_learner.education_background = profile_input.education_background
        existing_learner.major = profile_input.major
        existing_learner.work_experience_years = profile_input.work_experience_years
        existing_learner.self_assessment = profile_input.self_assessment
        existing_learner.learning_style = profile_input.learning_style
        existing_learner.goals = profile_input.goals
        # 写入诊断结果
        existing_learner.knowledge_points = profile_data.get("knowledge_points", [])
        existing_learner.blind_spots = profile_data.get("blind_spots", [])
        existing_learner.overall_level = profile_data.get("overall_level", "beginner")
        existing_learner.recommended_difficulty = profile_data.get("recommended_difficulty", "beginner")
        learner = existing_learner
    else:
        # 创建新画像
        learner = Learner(
            user_id=current_user.id,
            education_background=profile_input.education_background,
            major=profile_input.major,
            work_experience_years=profile_input.work_experience_years,
            self_assessment=profile_input.self_assessment,
            learning_style=profile_input.learning_style,
            goals=profile_input.goals,
            # 写入诊断结果
            knowledge_points=profile_data.get("knowledge_points", []),
            blind_spots=profile_data.get("blind_spots", []),
            overall_level=profile_data.get("overall_level", "beginner"),
            recommended_difficulty=profile_data.get("recommended_difficulty", "beginner"),
        )
        db.add(learner)

    await db.flush()

    # 3. 存入内存 store（用于 WebSocket 等实时功能）
    update_session(session_id, {
        "learner_id": learner.id,
        "profile": {
            **profile_input.model_dump(),
            "id": learner.id,
            "session_id": session_id,
            "knowledge_points": profile_data.get("knowledge_points", []),
            "blind_spots": profile_data.get("blind_spots", []),
            "overall_level": profile_data.get("overall_level", "beginner"),
            "recommended_difficulty": profile_data.get("recommended_difficulty", "beginner"),
        },
    })

    # 4. 返回结果
    return LearnerProfile(
        id=learner.id,
        session_id=session_id,
        education_background=profile_input.education_background,
        major=profile_input.major,
        work_experience_years=profile_input.work_experience_years,
        self_assessment=profile_input.self_assessment,
        learning_style=profile_input.learning_style,
        goals=profile_input.goals,
        knowledge_points=[
            {"name": kp.get("name", ""), "level": kp.get("level", "beginner"),
             "score": kp.get("score", 0), "confidence": kp.get("confidence", 0)}
            for kp in profile_data.get("knowledge_points", [])
        ],
        blind_spots=profile_data.get("blind_spots", []),
        overall_level=profile_data.get("overall_level", "beginner"),
        recommended_difficulty=profile_data.get("recommended_difficulty", "beginner"),
    )


@router.get("/me", response_model=LearnerProfile)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的画像（需登录）"""
    stmt = select(Learner).where(Learner.user_id == current_user.id)
    result = await db.execute(stmt)
    learner = result.scalar_one_or_none()

    if not learner:
        raise HTTPException(status_code=404, detail="尚未创建学习者画像")

    # 优先从数据库读取诊断结果
    knowledge_points = learner.knowledge_points or []
    blind_spots = learner.blind_spots or []
    overall_level = learner.overall_level or "beginner"
    recommended_difficulty = learner.recommended_difficulty or "beginner"

    # 如果数据库没有诊断结果，从内存 store 降级读取
    if not knowledge_points:
        from app.core.store import _sessions
        for sid, session in _sessions.items():
            if session.get("profile", {}).get("id") == learner.id:
                p = session["profile"]
                knowledge_points = p.get("knowledge_points", [])
                blind_spots = p.get("blind_spots", [])
                overall_level = p.get("overall_level", "beginner")
                recommended_difficulty = p.get("recommended_difficulty", "beginner")
                break

    return LearnerProfile(
        id=learner.id,
        education_background=learner.education_background,
        major=learner.major,
        work_experience_years=learner.work_experience_years,
        self_assessment=learner.self_assessment or {},
        learning_style=learner.learning_style or "practice",
        goals=learner.goals or [],
        knowledge_points=knowledge_points,
        blind_spots=blind_spots,
        overall_level=overall_level,
        recommended_difficulty=recommended_difficulty,
    )
