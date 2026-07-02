"""机台使用审批 API"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin
from app.models.approval_log import ApprovalLog
from app.models.database import get_db
from app.models.learner import Learner
from app.models.user import User

router = APIRouter(prefix="/approval", tags=["审批管理"])


class ApprovalAction(BaseModel):
    reason: Optional[str] = None


@router.post("/{learner_id}/approve")
async def approve_learner(
    learner_id: int,
    body: ApprovalAction = ApprovalAction(),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """批准学员机台使用申请"""
    learner_result = await db.execute(select(Learner).where(Learner.id == learner_id))
    learner = learner_result.scalar_one_or_none()
    if not learner:
        raise HTTPException(status_code=404, detail="学员不存在")

    if learner.machine_approval_status != "pending":
        raise HTTPException(status_code=400, detail="该学员当前不在待审批状态")

    from datetime import datetime, timezone

    learner.machine_approval_status = "approved"
    learner.machine_approval_at = datetime.now(timezone.utc)
    learner.machine_approval_by = admin.id

    # 记录审批日志
    log = ApprovalLog(
        learner_id=learner_id,
        action="approve",
        operator_id=admin.id,
        reason=body.reason,
    )
    db.add(log)
    await db.flush()

    return {
        "message": "审批通过",
        "learner_id": learner_id,
        "status": "approved",
    }


@router.post("/{learner_id}/reject")
async def reject_learner(
    learner_id: int,
    body: ApprovalAction,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """拒绝学员机台使用申请"""
    if not body.reason:
        raise HTTPException(status_code=400, detail="拒绝时必须填写理由")

    learner_result = await db.execute(select(Learner).where(Learner.id == learner_id))
    learner = learner_result.scalar_one_or_none()
    if not learner:
        raise HTTPException(status_code=404, detail="学员不存在")

    if learner.machine_approval_status != "pending":
        raise HTTPException(status_code=400, detail="该学员当前不在待审批状态")

    from datetime import datetime, timezone

    learner.machine_approval_status = "rejected"
    learner.machine_approval_at = datetime.now(timezone.utc)
    learner.machine_approval_by = admin.id

    # 记录审批日志
    log = ApprovalLog(
        learner_id=learner_id,
        action="reject",
        operator_id=admin.id,
        reason=body.reason,
    )
    db.add(log)
    await db.flush()

    return {
        "message": "已拒绝申请",
        "learner_id": learner_id,
        "status": "rejected",
    }


@router.get("/pending")
async def list_pending(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin = Depends(require_admin),
):
    """待审批学员列表"""
    base_query = (
        select(Learner, User.username)
        .join(User, Learner.user_id == User.id)
        .where(Learner.machine_approval_status == "pending")
    )

    # 计数
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页
    offset = (page - 1) * page_size
    rows_result = await db.execute(base_query.order_by(Learner.updated_at.desc()).offset(offset).limit(page_size))
    rows = rows_result.all()

    items = []
    for learner, username in rows:
        learning_path = learner.learning_path or []
        progress = 0.0
        if learning_path and len(learning_path) > 0:
            completed = sum(1 for node in learning_path if node.get("status") == "completed")
            progress = round(completed / len(learning_path), 4)

        items.append({
            "id": learner.id,
            "username": username,
            "overall_level": learner.overall_level,
            "learning_progress": progress,
            "updated_at": learner.updated_at.isoformat() if learner.updated_at else None,
        })

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


@router.get("/logs")
async def list_logs(
    learner_id: Optional[int] = Query(None, description="按学员筛选"),
    action: Optional[str] = Query(None, description="按操作类型筛选: submit | approve | reject"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin = Depends(require_admin),
):
    """审批操作日志"""
    base_query = select(ApprovalLog, User.username).join(
        User, ApprovalLog.operator_id == User.id
    )

    if learner_id:
        base_query = base_query.where(ApprovalLog.learner_id == learner_id)
    if action:
        base_query = base_query.where(ApprovalLog.action == action)

    # 计数
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页
    offset = (page - 1) * page_size
    rows_result = await db.execute(
        base_query.order_by(ApprovalLog.created_at.desc()).offset(offset).limit(page_size)
    )
    rows = rows_result.all()

    items = []
    for log, op_name in rows:
        items.append({
            "id": log.id,
            "learner_id": log.learner_id,
            "action": log.action,
            "operator_name": op_name,
            "reason": log.reason,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }
