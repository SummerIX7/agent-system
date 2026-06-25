from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.core.store import get_session
from app.models.resource import Resource
from app.models.agent_state import FeedbackRecord

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
    metrics: Optional[dict] = None


@router.get("/visualization/{session_id}", response_model=VisualizationData)
async def get_visualization(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取可视化数据（雷达图、盲区、匹配曲线、核心指标）"""
    from app.models.learner import Learner

    session = get_session(session_id)
    profile = session.get("profile", {})

    # 如果内存 store 中没有诊断数据，从数据库降级读取
    if not profile.get("knowledge_points"):
        learner = None

        # 方式 1：通过 session 中的 learner_id 查找
        learner_id = session.get("learner_id")
        if learner_id:
            stmt_lp = select(Learner).where(Learner.id == learner_id)
            result_lp = await db.execute(stmt_lp)
            learner = result_lp.scalar_one_or_none()

        # 方式 2：通过 session_id 格式推断（"user-{user_id}"）
        if not learner and session_id.startswith("user-"):
            try:
                user_id = int(session_id.split("-", 1)[1])
                stmt_lp = select(Learner).where(Learner.user_id == user_id)
                result_lp = await db.execute(stmt_lp)
                learner = result_lp.scalar_one_or_none()
            except (ValueError, IndexError):
                pass

        # 方式 3：兜底 — 查找有诊断数据的 Learner
        if not learner:
            stmt_lp = select(Learner).where(Learner.knowledge_points.isnot(None))
            result_lp = await db.execute(stmt_lp)
            learner = result_lp.scalars().first()

        if learner and learner.knowledge_points:
            profile = {
                **profile,
                "knowledge_points": learner.knowledge_points,
                "blind_spots": learner.blind_spots or [],
                "overall_level": learner.overall_level or "beginner",
                "recommended_difficulty": learner.recommended_difficulty or "beginner",
            }

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

    # 学习路径：优先从 Learner 表读取 PathPlannerAgent 的真实输出
    learning_path_data = None
    learner_id = session.get("learner_id")
    if learner_id:
        from app.models.learner import Learner as LearnerModel
        stmt_path = select(LearnerModel).where(LearnerModel.id == learner_id)
        result_path = await db.execute(stmt_path)
        learner_record = result_path.scalar_one_or_none()
        if learner_record and learner_record.learning_path:
            learning_path_data = learner_record.learning_path

    # 降级：从 session_id 推断
    if not learning_path_data and session_id.startswith("user-"):
        try:
            user_id = int(session_id.split("-", 1)[1])
            stmt_path = select(LearnerModel).where(LearnerModel.user_id == user_id)
            result_path = await db.execute(stmt_path)
            learner_record = result_path.scalar_one_or_none()
            if learner_record and learner_record.learning_path:
                learning_path_data = learner_record.learning_path
        except (ValueError, IndexError):
            pass

    # 降级：从内存 store 中的 resources 查找
    if not learning_path_data:
        for res in session.get("resources", []):
            if res.get("type") == "learning_path":
                learning_path_data = res.get("content", {})
                break

    # 构建前端需要的学习路径列表
    learning_path = []
    if learning_path_data and learning_path_data.get("path"):
        for stage in learning_path_data["path"]:
            learning_path.append({
                "stage": stage.get("stage", 0),
                "title": stage.get("title", ""),
                "topics": stage.get("topics", []),
                "estimated_hours": stage.get("estimated_hours", 0),
                "difficulty": stage.get("difficulty", "beginner"),
                "prerequisites": stage.get("prerequisites", []),
                "resources_type": stage.get("resources_type", []),
                "completed": False,
            })
    else:
        # 兜底：从知识点生成简化路径
        for kp in profile.get("knowledge_points", []):
            learning_path.append({
                "stage": 0,
                "title": kp.get("name", ""),
                "topics": [kp.get("name", "")],
                "estimated_hours": 0,
                "difficulty": kp.get("level", "beginner"),
                "prerequisites": [],
                "resources_type": [],
                "completed": kp.get("score", 0) >= 60,
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

    # === 计算三项核心指标 ===
    hallucination_rate = None
    difficulty_match_rate = None
    knowledge_coverage_rate = None

    # 查询该 session 的所有资源
    stmt = select(Resource).where(Resource.session_id == session_id)
    result = await db.execute(stmt)
    db_resources = result.scalars().all()

    if db_resources:
        # 1. 知识谬误率：从辩论质量分数计算
        scores = [r.review_score for r in db_resources if r.review_score is not None]
        if scores:
            avg_score = sum(scores) / len(scores)
            hallucination_rate = round((1 - avg_score) * 100, 1)

        # 2. 难度匹配准确率：比较推荐难度与实际资源难度
        recommended = profile.get("recommended_difficulty", "beginner")
        difficulty_map = {"beginner": 1, "intermediate": 2, "advanced": 3, "expert": 4}
        rec_level = difficulty_map.get(recommended, 1)
        match_count = 0
        total_with_difficulty = 0
        for r in db_resources:
            if r.difficulty:
                res_level = difficulty_map.get(r.difficulty, 1)
                total_with_difficulty += 1
                if abs(res_level - rec_level) <= 1:
                    match_count += 1
        if total_with_difficulty > 0:
            difficulty_match_rate = round(match_count / total_with_difficulty * 100, 1)

    # 3. 知识点覆盖率：检查知识点是否在生成内容中被提及
    kp_list = profile.get("knowledge_points", [])
    if kp_list and db_resources:
        all_content = " ".join(str(r.content) for r in db_resources)
        covered = sum(1 for kp in kp_list if kp.get("name", "") in all_content)
        knowledge_coverage_rate = round(covered / len(kp_list) * 100, 1)

    return VisualizationData(
        knowledge_points=knowledge_points,
        blind_spots=blind_spots,
        learning_path=learning_path,
        match_curve=match_curve,
        agent_logs=agent_logs,
        metrics={
            "hallucination_rate": hallucination_rate,
            "difficulty_match_rate": difficulty_match_rate,
            "knowledge_coverage_rate": knowledge_coverage_rate,
        },
        learning_path_meta={
            "total_estimated_hours": learning_path_data.get("total_estimated_hours", 0),
            "current_stage": learning_path_data.get("current_stage", 1),
            "recommended_order": learning_path_data.get("recommended_order", ""),
        } if learning_path_data else None,
    )


@router.get("/history/{learner_id}")
async def get_history(
    learner_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取学习历史记录（从数据库读取）"""
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
