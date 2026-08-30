"""职业方向配置 API"""

from fastapi import APIRouter

from app.core.career_tracks import get_all_career_tracks

router = APIRouter(prefix="/api", tags=["职业方向"])


@router.get("/career-tracks")
async def list_career_tracks():
    """获取所有 CNC 职业方向（操机工 / 调机工 / 编程师）"""
    tracks = get_all_career_tracks()
    return [
        {
            "code": t.code,
            "name": t.name,
            "description": t.description,
            "order": t.order,
            "difficulty_levels": t.difficulty_levels,
            "self_assessment_skills": t.self_assessment_skills,
            "prerequisite_knowledge": t.prerequisite_knowledge,
            "core_topics": t.core_topics,
        }
        for t in tracks
    ]
