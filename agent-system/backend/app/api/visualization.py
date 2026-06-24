from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.core.store import get_session

router = APIRouter(prefix="/api", tags=["可视化数据"])


class KnowledgePoint(BaseModel):
    name: str
    score: float
    level: str


class BlindSpot(BaseModel):
    name: str
    severity: float


class VisualizationData(BaseModel):
    knowledge_points: List[KnowledgePoint]
    blind_spots: List[BlindSpot]
    learning_path: List[dict]
    match_curve: Optional[dict] = None
    agent_logs: List[dict] = []


@router.get("/visualization/{session_id}", response_model=VisualizationData)
async def get_visualization(session_id: str):
    """获取可视化数据（雷达图、盲区、匹配曲线）"""
    session = get_session(session_id)
    profile = session.get("profile", {})

    # 从画像中提取知识点
    knowledge_points = [
        KnowledgePoint(
            name=kp.get("name", ""),
            score=kp.get("score", 0),
            level=kp.get("level", "beginner"),
        )
        for kp in profile.get("knowledge_points", [])
    ]

    # 从画像中提取盲区
    blind_spots = [
        BlindSpot(name=bs, severity=0.7)
        for bs in profile.get("blind_spots", [])
    ]

    # 生成学习路径（基于知识点掌握度）
    learning_path = []
    for kp in profile.get("knowledge_points", []):
        learning_path.append({
            "title": kp.get("name", ""),
            "completed": kp.get("score", 0) >= 60,
            "score": kp.get("score", 0),
        })

    # 匹配曲线数据
    match_curve = None
    if knowledge_points:
        match_curve = {
            "learner_level": profile.get("recommended_difficulty", "beginner"),
            "resources": [
                {"name": kp.name, "difficulty": kp.score / 20, "match": min(1.0, kp.score / 80)}
                for kp in knowledge_points
            ],
        }

    # Agent 日志
    agent_logs = session.get("agent_logs", [])

    return VisualizationData(
        knowledge_points=knowledge_points,
        blind_spots=blind_spots,
        learning_path=learning_path,
        match_curve=match_curve,
        agent_logs=agent_logs,
    )


@router.get("/history/{learner_id}")
async def get_history(
    learner_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取学习历史记录（从数据库读取）"""
    from app.models.agent_state import FeedbackRecord
    from app.models.resource import Resource
    from app.models.learner import Learner

    history = []

    # 查找学习者
    stmt = select(Learner).where(Learner.id == learner_id)
    result = await db.execute(stmt)
    learner = result.scalar_one_or_none()

    if learner:
        history.append({
            "title": "完成学情诊断",
            "date": learner.created_at.isoformat() if learner.created_at else "",
            "description": f"学历: {learner.education_background}, 专业: {learner.major}",
            "tags": ["画像构建", "学情诊断"],
        })

    # 资源生成记录
    stmt = select(Resource).where(Resource.learner_id == learner_id)
    result = await db.execute(stmt)
    resources = result.scalars().all()
    for res in resources:
        history.append({
            "title": f"生成{res.resource_type}",
            "date": res.created_at.isoformat() if res.created_at else "",
            "description": f"主题: {res.topic}",
            "tags": ["资源生成", res.resource_type],
        })

    # 反馈记录
    stmt = select(FeedbackRecord).where(FeedbackRecord.learner_id == learner_id)
    result = await db.execute(stmt)
    feedbacks = result.scalars().all()
    for fb in feedbacks:
        history.append({
            "title": f"答题 {'✓' if fb.is_correct else '✗'}",
            "date": fb.created_at.isoformat() if fb.created_at else "",
            "description": fb.question,
            "tags": ["反馈", "正确" if fb.is_correct else "错误"],
        })

    # 按时间排序
    history.sort(key=lambda x: x.get("date", ""), reverse=True)
    return history
