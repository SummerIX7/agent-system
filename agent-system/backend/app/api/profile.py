import uuid
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.schemas import LearnerProfileInput, LearnerProfile
from app.models.learner import Learner
from app.agents.diagnosis import DiagnosisAgent
from app.core.store import update_session

router = APIRouter(prefix="/api/profile", tags=["学习者画像"])

diagnosis_agent = DiagnosisAgent()


@router.post("/", response_model=LearnerProfile)
async def create_profile(
    profile_input: LearnerProfileInput,
    db: AsyncSession = Depends(get_db),
):
    """提交学习者画像，触发学情诊断"""
    # 1. 调用诊断 Agent
    try:
        result = await diagnosis_agent.run(profile_input.model_dump())
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=f"LLM 服务不可用: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"诊断失败: {e}")

    profile_data = result.get("profile", {})
    learner_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    # 2. 写入 MySQL
    learner = Learner(
        id=learner_id,
        education_background=profile_input.education_background,
        major=profile_input.major,
        work_experience_years=profile_input.work_experience_years,
        self_assessment=profile_input.self_assessment,
        learning_style=profile_input.learning_style,
        goals=profile_input.goals,
    )
    db.add(learner)
    await db.flush()

    # 3. 同时存入内存 store（用于 WebSocket 等实时功能）
    update_session(session_id, {
        "learner_id": learner_id,
        "profile": {
            **profile_input.model_dump(),
            "id": learner_id,
            "session_id": session_id,
            "knowledge_points": profile_data.get("knowledge_points", []),
            "blind_spots": profile_data.get("blind_spots", []),
            "overall_level": profile_data.get("overall_level", "beginner"),
            "recommended_difficulty": profile_data.get("recommended_difficulty", "beginner"),
        },
    })

    # 4. 返回结果
    return LearnerProfile(
        id=learner_id,
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


@router.get("/{learner_id}", response_model=LearnerProfile)
async def get_profile(
    learner_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取学习者画像（从数据库读取）"""
    # 从 MySQL 查询
    stmt = select(Learner).where(Learner.id == learner_id)
    result = await db.execute(stmt)
    learner = result.scalar_one_or_none()

    if not learner:
        raise HTTPException(status_code=404, detail="学习者不存在")

    # 尝试从内存 store 获取诊断结果（知识盲区等）
    from app.core.store import _sessions
    knowledge_points = []
    blind_spots = []
    overall_level = "beginner"
    recommended_difficulty = "beginner"

    for sid, session in _sessions.items():
        if session.get("profile", {}).get("id") == learner_id:
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
