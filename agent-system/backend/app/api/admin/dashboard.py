"""数据看板 API"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin
from app.models.database import get_db
from app.models.learner import Learner
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["数据看板"])


@router.get("/overview")
async def get_overview(
    db: AsyncSession = Depends(get_db),
    _admin = Depends(require_admin),
):
    """数据看板概览：总学员数、待审批数、今日活跃、平均通过率、知识点分布"""
    from datetime import datetime, timezone

    # 总学员数：按 learner 角色账号统计。未提交画像的账号还没有 learners 记录，也应在管理端可见。
    total_result = await db.execute(select(func.count(User.id)).where(User.role == "learner"))
    total_learners = total_result.scalar() or 0

    # 待审批数
    pending_result = await db.execute(
        select(func.count(Learner.id)).where(Learner.machine_approval_status == "pending")
    )
    pending_approvals = pending_result.scalar() or 0

    # 今日活跃（今天更新过画像的学员）
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    active_result = await db.execute(
        select(func.count(Learner.id)).where(Learner.updated_at >= today)
    )
    active_today = active_result.scalar() or 0

    # 平均通过率（从 report_caches 表计算。hallucination_rate 存储为百分比 0-100，需转为小数）
    from app.models.agent_state import ReportCache
    all_rc = await db.execute(select(ReportCache.cache_data))
    rates = []
    for row in all_rc.scalars():
        if row and isinstance(row, dict):
            rate = row.get("hallucination_rate")
            if rate is not None:
                rates.append(1.0 - rate / 100)
    avg_pass_rate = sum(rates) / len(rates) if rates else 0.0

    # 知识点分布（从所有学员 knowledge_points 聚合）
    knowledge_dist: dict[str, dict[str, int]] = {}
    all_kp = await db.execute(select(Learner.knowledge_points))
    for row in all_kp.scalars():
        if row and isinstance(row, list):
            for kp in row:
                name = kp.get("name", "未知")
                level = kp.get("level", "medium")
                if name not in knowledge_dist:
                    knowledge_dist[name] = {"low": 0, "medium": 0, "high": 0}
                if level in ("beginner", "low"):
                    knowledge_dist[name]["low"] += 1
                elif level in ("intermediate", "medium"):
                    knowledge_dist[name]["medium"] += 1
                else:
                    knowledge_dist[name]["high"] += 1

    # 知识图谱进度统计（从 learners.kg_progress 聚合）
    kg_learners_with_progress = 0
    kg_avg_percentage = 0.0
    all_kg = await db.execute(select(Learner.kg_progress))
    kg_percentages = []
    for row in all_kg.scalars():
        if row and isinstance(row, dict) and row.get("percentage") is not None:
            kg_percentages.append(float(row["percentage"]))
    if kg_percentages:
        kg_learners_with_progress = len(kg_percentages)
        kg_avg_percentage = round(sum(kg_percentages) / len(kg_percentages), 1)

    return {
        "total_learners": total_learners,
        "pending_approvals": pending_approvals,
        "active_today": active_today,
        "avg_pass_rate": round(avg_pass_rate, 4),
        "knowledge_distribution": knowledge_dist,
        "kg_stats": {
            "learners_with_progress": kg_learners_with_progress,
            "avg_percentage": kg_avg_percentage,
        },
    }


@router.get("/trends")
async def get_trends(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    db: AsyncSession = Depends(get_db),
    _admin = Depends(require_admin),
):
    """学习趋势：每日新增学员、每日活跃"""
    from datetime import datetime, timezone, timedelta

    end_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=days)

    # 每日新增学员
    new_users_result = await db.execute(
        select(func.date(User.created_at), func.count(User.id))
        .where(User.created_at >= start_date, User.role == "learner")
        .group_by(func.date(User.created_at))
        .order_by(func.date(User.created_at))
    )
    new_learners_daily = {row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]): row[1] for row in new_users_result.all()}

    # 每日学习活动（learner updated_at）
    active_result = await db.execute(
        select(func.date(Learner.updated_at), func.count(Learner.id))
        .where(Learner.updated_at >= start_date)
        .group_by(func.date(Learner.updated_at))
        .order_by(func.date(Learner.updated_at))
    )
    active_daily = {row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]): row[1] for row in active_result.all()}

    # 审批趋势
    from app.models.approval_log import ApprovalLog
    approval_result = await db.execute(
        select(func.date(ApprovalLog.created_at), func.count(ApprovalLog.id))
        .where(ApprovalLog.created_at >= start_date)
        .group_by(func.date(ApprovalLog.created_at))
        .order_by(func.date(ApprovalLog.created_at))
    )
    approval_daily = {row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]): row[1] for row in approval_result.all()}

    return {
        "days": days,
        "new_learners_daily": new_learners_daily,
        "active_daily": active_daily,
        "approval_daily": approval_daily,
    }


@router.get("/domain-stats")
async def get_domain_stats(
    db: AsyncSession = Depends(get_db),
    _admin = Depends(require_admin),
):
    """领域统计：各领域学员分布、通过率对比"""
    # 按学历背景分组统计
    bg_result = await db.execute(
        select(Learner.education_background, func.count(Learner.id))
        .group_by(Learner.education_background)
    )
    by_background = {row[0] or "未知": row[1] for row in bg_result.all()}

    # 按整体水平分组
    level_result = await db.execute(
        select(Learner.overall_level, func.count(Learner.id))
        .where(Learner.overall_level.isnot(None))
        .group_by(Learner.overall_level)
    )
    by_level = {row[0] or "未知": row[1] for row in level_result.all()}

    # 按学习风格分组
    style_result = await db.execute(
        select(Learner.learning_style, func.count(Learner.id))
        .where(Learner.learning_style.isnot(None))
        .group_by(Learner.learning_style)
    )
    by_style = {row[0] or "未知": row[1] for row in style_result.all()}

    return {
        "by_education_background": by_background,
        "by_level": by_level,
        "by_learning_style": by_style,
    }
