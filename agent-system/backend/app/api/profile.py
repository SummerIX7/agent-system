import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.schemas import LearnerProfileInput, LearnerProfile
from app.agents.diagnosis import DiagnosisAgent
from app.core.store import update_session, get_session

router = APIRouter(prefix="/api/profile", tags=["学习者画像"])

diagnosis_agent = DiagnosisAgent()


@router.post("/", response_model=LearnerProfile)
async def create_profile(
    profile_input: LearnerProfileInput,
    db: AsyncSession = Depends(get_db),
):
    """提交学习者画像，触发学情诊断"""
    result = await diagnosis_agent.run(profile_input.model_dump())

    profile_data = result.get("profile", {})
    learner_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    # 存入 store
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
    """获取学习者画像"""
    # 从 store 查找
    for session in get_session.__wrapped__() if hasattr(get_session, '__wrapped__') else []:
        pass

    # 简单遍历查找
    from app.core.store import _sessions
    for sid, session in _sessions.items():
        if session.get("profile", {}).get("id") == learner_id:
            p = session["profile"]
            return LearnerProfile(
                id=learner_id,
                education_background=p.get("education_background", ""),
                major=p.get("major", ""),
                work_experience_years=p.get("work_experience_years", 0),
                self_assessment=p.get("self_assessment", {}),
                learning_style=p.get("learning_style", "practice"),
                goals=p.get("goals", []),
                knowledge_points=p.get("knowledge_points", []),
                blind_spots=p.get("blind_spots", []),
                overall_level=p.get("overall_level", "beginner"),
                recommended_difficulty=p.get("recommended_difficulty", "beginner"),
            )

    # 未找到返回默认
    return LearnerProfile(
        id=learner_id,
        education_background="未知",
        major="未知",
        work_experience_years=0,
        self_assessment={},
        learning_style="practice",
        goals=[],
    )
