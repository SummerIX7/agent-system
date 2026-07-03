"""学员管理 API"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin
from app.models.database import get_db
from app.models.learner import Learner
from app.models.user import User

router = APIRouter(prefix="/users", tags=["学员管理"])


@router.get("/list")
async def list_users(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="用户名/邮箱搜索"),
    status: Optional[str] = Query(None, description="学习状态筛选"),
    approval_status: Optional[str] = Query(None, description="审批状态筛选"),
    domain: Optional[str] = Query(None, description="领域筛选"),
    level: Optional[str] = Query(None, description="等级筛选"),
    db: AsyncSession = Depends(get_db),
    _admin = Depends(require_admin),
):
    """学员列表（分页 + 搜索 + 筛选）"""
    # 基础查询：关联 User 表
    base_query = select(
        Learner.id,
        User.username,
        User.email,
        Learner.education_background,
        Learner.major,
        Learner.overall_level,
        Learner.machine_approval_status,
        Learner.updated_at,
        Learner.learning_path,
    ).join(User, Learner.user_id == User.id).where(User.role == "learner")

    # 关键词搜索
    if keyword:
        base_query = base_query.where(
            or_(
                User.username.like(f"%{keyword}%"),
                User.email.like(f"%{keyword}%"),
            )
        )

    # 审批状态筛选
    if approval_status:
        base_query = base_query.where(Learner.machine_approval_status == approval_status)

    # 等级筛选
    if level:
        base_query = base_query.where(Learner.overall_level == level)

    # 学历/领域筛选
    if domain:
        base_query = base_query.where(Learner.education_background == domain)

    # 计数
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页
    offset = (page - 1) * page_size
    rows_result = await db.execute(base_query.order_by(Learner.updated_at.desc()).offset(offset).limit(page_size))
    rows = rows_result.all()

    items = []
    for row in rows:
        # 计算学习进度（学习路径中已完成节点占比）
        learning_path = row.learning_path
        progress = 0.0
        if learning_path and isinstance(learning_path, dict):
            path_nodes = learning_path.get("path", [])
            if path_nodes and len(path_nodes) > 0:
                completed = sum(1 for node in path_nodes if node.get("advanced_test_passed") or node.get("completed"))
                progress = round(completed / len(path_nodes), 4)

        items.append({
            "id": row.id,
            "username": row.username,
            "email": row.email,
            "education_background": row.education_background,
            "major": row.major,
            "overall_level": row.overall_level,
            "learning_progress": progress,
            "machine_approval_status": row.machine_approval_status,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        })

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


@router.get("/{learner_id}")
async def get_user_detail(
    learner_id: int,
    db: AsyncSession = Depends(get_db),
    _admin = Depends(require_admin),
):
    """学员详情"""
    result = await db.execute(
        select(Learner, User.username, User.email)
        .join(User, Learner.user_id == User.id)
        .where(Learner.id == learner_id)
    )
    row = result.one_or_none()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="学员不存在")

    learner, username, email = row

    # 学习路径进度
    learning_path = learner.learning_path or {}
    path_nodes = learning_path.get("path", []) if isinstance(learning_path, dict) else []
    progress = 0.0
    if path_nodes and len(path_nodes) > 0:
        completed = sum(1 for node in path_nodes if node.get("advanced_test_passed") or node.get("completed"))
        progress = round(completed / len(path_nodes), 4)

    # 知识图谱进度
    kg_progress = learner.kg_progress or {}
    kg_data = {
        "completed_nodes": kg_progress.get("completed_nodes", []) if isinstance(kg_progress, dict) else [],
        "percentage": kg_progress.get("percentage", 0) if isinstance(kg_progress, dict) else 0,
        "total": kg_progress.get("total", 0) if isinstance(kg_progress, dict) else 0,
    }

    return {
        "id": learner.id,
        "user_id": learner.user_id,
        "username": username,
        "email": email,
        "education_background": learner.education_background,
        "major": learner.major,
        "work_experience_years": learner.work_experience_years,
        "learning_style": learner.learning_style,
        "goals": learner.goals,
        "knowledge_points": learner.knowledge_points,
        "blind_spots": learner.blind_spots,
        "overall_level": learner.overall_level,
        "recommended_difficulty": learner.recommended_difficulty,
        "learning_path": path_nodes,
        "learning_progress": progress,
        "kg_progress": kg_data,
        "machine_approval_status": learner.machine_approval_status,
        "machine_approval_at": learner.machine_approval_at.isoformat() if learner.machine_approval_at else None,
        "machine_approval_by": learner.machine_approval_by,
        "report_cache": learner.report_cache,
        "created_at": learner.created_at.isoformat() if learner.created_at else None,
        "updated_at": learner.updated_at.isoformat() if learner.updated_at else None,
    }


@router.get("/{learner_id}/learning-detail")
async def get_learning_detail(
    learner_id: int,
    db: AsyncSession = Depends(get_db),
    _admin = Depends(require_admin),
):
    """学员学习详情：节点状态、答题记录、审批历史"""
    from app.models.agent_state import FeedbackRecord
    from app.models.approval_log import ApprovalLog

    # 获取学员
    learner_result = await db.execute(select(Learner).where(Learner.id == learner_id))
    learner = learner_result.scalar_one_or_none()
    if not learner:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="学员不存在")

    # 答题记录
    feedback_result = await db.execute(
        select(FeedbackRecord)
        .where(FeedbackRecord.learner_id == learner_id)
        .order_by(FeedbackRecord.created_at.desc())
        .limit(50)
    )
    feedbacks = []
    for fb in feedback_result.scalars():
        feedbacks.append({
            "id": fb.id,
            "session_id": fb.session_id,
            "stage": fb.stage,
            "test_level": fb.test_level,
            "question": fb.question,
            "user_answer": fb.user_answer,
            "correct_answer": fb.correct_answer,
            "is_correct": fb.is_correct,
            "heuristic_question": fb.heuristic_question,
            "created_at": fb.created_at.isoformat() if fb.created_at else None,
        })

    # 审批历史
    approval_result = await db.execute(
        select(ApprovalLog, User.username)
        .join(User, ApprovalLog.operator_id == User.id)
        .where(ApprovalLog.learner_id == learner_id)
        .order_by(ApprovalLog.created_at.desc())
    )
    approval_logs = []
    for log, op_name in approval_result.all():
        approval_logs.append({
            "id": log.id,
            "action": log.action,
            "operator_name": op_name,
            "reason": log.reason,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })

    return {
        "learner_id": learner_id,
        "learning_path": (learner.learning_path or {}).get("path", []) if isinstance(learner.learning_path, dict) else [],
        "recent_feedbacks": feedbacks,
        "approval_logs": approval_logs,
    }
