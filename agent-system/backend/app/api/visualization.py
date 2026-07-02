import logging
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.schemas import VisualizationData, KnowledgePoint as SchemaKnowledgePoint, BlindSpot as SchemaBlindSpot
from app.core.store import get_session
from app.models.resource import Resource
from app.models.agent_state import FeedbackRecord
from app.models.learner import Learner

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["可视化数据"])


@router.get("/visualization/{session_id}", response_model=VisualizationData)
async def get_visualization(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取可视化数据。优先从 learner.report_cache 读取快照。"""
    from app.core.store import resolve_learner_context
    await resolve_learner_context(session_id, db)

    session = get_session(session_id)
    profile = session.get("profile", {})
    learner_id = session.get("learner_id", "")

    # ── 从 DB 获取 report_cache ──
    report_cache = {}
    learner = None
    if learner_id and learner_id != "unknown":
        stmt = select(Learner).where(Learner.id == learner_id)
        result = await db.execute(stmt)
        learner = result.scalar_one_or_none()

    if learner:
        report_cache = learner.report_cache or {}
        # 确保 profile 完整（session store 可能丢失）
        if not profile.get("knowledge_points") and learner.knowledge_points:
            profile = {
                **profile,
                "knowledge_points": learner.knowledge_points,
                "blind_spots": learner.blind_spots or [],
                "overall_level": learner.overall_level or "beginner",
                "recommended_difficulty": learner.recommended_difficulty or "beginner",
            }

    # ── 知识点 ──
    knowledge_points = [
        SchemaKnowledgePoint(
            name=kp.get("name", ""),
            score=kp.get("score", 0),
            level=kp.get("level", "beginner"),
        ).model_dump()
        for kp in profile.get("knowledge_points", [])
    ]

    # ── 盲区 ──
    blind_spots = [
        SchemaBlindSpot(name=bs, severity=0.7).model_dump()
        for bs in profile.get("blind_spots", [])
    ]

    # ── 学习路径 ──
    learning_path = {}
    for res in session.get("resources", []):
        if res.get("type") == "learning_path":
            learning_path = res.get("content", {})
            break
    if not learning_path and learner and learner.learning_path:
        learning_path = learner.learning_path

    learning_path_list = []
    for stage in learning_path.get("path", []):
        learning_path_list.append({
            "stage": stage.get("stage", 0),
            "title": stage.get("title", ""),
            "topics": stage.get("topics", []),
            "estimated_hours": stage.get("estimated_hours", 0),
            "difficulty": stage.get("difficulty", "beginner"),
            "prerequisites": stage.get("prerequisites", []),
            "resources_type": stage.get("resources_type", []),
            "completed": stage.get("completed", False),
        })
    if not learning_path_list:
        for kp in profile.get("knowledge_points", []):
            learning_path_list.append({
                "stage": 0, "title": kp.get("name", ""),
                "topics": [kp.get("name", "")],
                "estimated_hours": 0,
                "difficulty": kp.get("level", "beginner"),
                "prerequisites": [], "resources_type": [],
                "completed": kp.get("score", 0) >= 60,
            })

    # ── 指标：从 report_cache 读取 ──
    metrics = {
        "hallucination_rate": report_cache.get("hallucination_rate"),
        "difficulty_match_rate": report_cache.get("difficulty_match_rate"),
        "knowledge_coverage_rate": report_cache.get("knowledge_coverage_rate"),
    }

    # ── 匹配曲线：从 report_cache 读取 ──
    match_curve = report_cache.get("match_curve")
    if not match_curve and knowledge_points:
        rec = profile.get("recommended_difficulty", "beginner")
        match_curve = {
            "learner_level": rec,
            "resources": [
                {"name": kp["name"], "difficulty": kp["score"] / 20,
                 "match": min(1.0, kp["score"] / 80)}
                for kp in knowledge_points
            ],
        }

    # ── 学习路径元数据 ──
    learning_stats = report_cache.get("learning_stats", {})
    learning_path_meta = {
        "total_estimated_hours": learning_stats.get("total_hours", learning_path.get("total_estimated_hours", 0)),
        "current_stage": learning_path.get("current_stage", 1),
        "recommended_order": learning_path.get("recommended_order", ""),
    } if learning_path else None

    return VisualizationData(
        knowledge_points=knowledge_points,
        blind_spots=blind_spots,
        learning_path=learning_path_list,
        match_curve=match_curve,
        agent_logs=session.get("agent_logs", []),
        metrics=metrics,
        learning_path_meta=learning_path_meta,
    )


@router.get("/history/{learner_id}")
async def get_history(
    learner_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取学习历史记录（从数据库读取）"""
    history = []

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

    history.sort(key=lambda x: x.get("date", ""), reverse=True)
    return history

