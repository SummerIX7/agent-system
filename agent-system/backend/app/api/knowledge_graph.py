"""
知识图谱 API — 薄 FastAPI 路由。

业务逻辑已拆分到 ``app.services.kg_*``：
- kg_tree：目录解析 / 树 / 叶子索引 / 主题匹配
- kg_progress：掌握度评分 / 进度规范化 / 文件缓存 / DB 同步
- kg_events：学习事件触发的自动打点
- kg_graph：力导向图数据构造

本文件仅负责：请求参数校验、鉴权、DB 依赖注入、调用 service、组装响应。
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_admin
from app.models.database import get_db
from app.models.learner import Learner
from app.models.user import User
from app.services.kg_events import (
    auto_mark_completed,  # noqa: F401 (re-export for legacy imports)
    mark_learning_event_by_learner_id,
)
from app.services.kg_graph import build_graph
from app.services.kg_progress import (
    apply_score_update,
    build_kg_progress_for_learner,
    clamp_score,
    load_progress,
    load_progress_from_db,
    normalize_progress,
    progress_stats,
    save_progress,
    status_from_score,
    status_label,
    sync_progress_to_db,
)
from app.services.kg_tree import (
    CATEGORY_LABELS,
    PROGRESS_DIR,
    build_tree,
    category_label,
    init_category_labels,
    leaf_ids_from_tree,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["知识图谱"])


# ── 请求模型 ──

class ProgressRequest(BaseModel):
    node_id: str
    completed: bool
    score: Optional[float] = None
    source: Optional[str] = "manual"


class ProgressResponse(BaseModel):
    username: str
    completed_nodes: list[str]
    node_scores: dict[str, dict] = {}
    total: int
    percentage: float


# ── API 端点 ──

@router.get("/knowledge-graph")
async def get_knowledge_graph():
    """获取知识图谱树状图数据（适配 ECharts Tree）。"""
    if not CATEGORY_LABELS:
        init_category_labels()
    return build_tree()


@router.get("/knowledge-graph/graph")
async def get_knowledge_graph_as_graph():
    """获取无个人进度的力导向图数据（适配 ECharts Graph）。"""
    return build_graph(normalize_progress({}))


@router.get("/knowledge-graph/files")
async def get_knowledge_files(
    category: Optional[str] = Query(None, description="按分类筛选：theory / practice / standards"),
):
    """获取知识库文件列表，支持按分类筛选。"""
    if not CATEGORY_LABELS:
        init_category_labels()

    tree = build_tree()
    files = []

    for cat_node in tree.get("children", []):
        cat_key = cat_node.get("category", "")
        if category and cat_key != category:
            continue
        for leaf in cat_node.get("children", []):
            if leaf.get("is_leaf"):
                files.append({
                    "title": leaf["name"],
                    "id": leaf["id"],
                    "file": leaf["file"],
                    "category": category_label(cat_key),
                    "category_key": cat_key,
                    "source_type": leaf.get("source_type", ""),
                    "author": leaf.get("author", ""),
                    "year": leaf.get("year", ""),
                    "chapter": leaf.get("chapter", ""),
                    "source_name": leaf.get("source_name", ""),
                })

    return {
        "domain": "cnc",
        "domain_name": "数控加工领域",
        "category_filter": category,
        "total": len(files),
        "files": files,
    }


@router.post("/knowledge-graph/progress")
async def mark_progress(
    req: ProgressRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    标记/取消标记某知识点为"已学习"。同时同步进度到数据库。
    """
    user_id = current_user.id
    progress = load_progress(user_id)
    target_score = req.score
    if target_score is None:
        target_score = 100 if req.completed else 0
    action = "completed" if req.completed else "uncompleted"
    progress = apply_score_update(
        progress,
        req.node_id,
        target_score,
        source=req.source or "manual",
        action=action,
    )
    save_progress(user_id, progress)
    await sync_progress_to_db(user_id, progress, db)

    tree = build_tree()
    total_leaves = tree.get("total_leaves", 0)
    leaf_ids = leaf_ids_from_tree(tree)
    stats = progress_stats(progress, total_leaves, leaf_ids)

    return {
        "username": current_user.username,
        "completed_nodes": progress.get("completed_nodes", []),
        "node_scores": progress.get("node_scores", {}),
        "total": total_leaves,
        "percentage": stats["percentage"],
        "stats": stats,
    }


@router.get("/knowledge-graph/progress")
async def get_progress(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取当前用户的学习进度。
    DB 优先（可信源），文件作为降级缓存。
    """
    user_id = current_user.id
    db_progress = await load_progress_from_db(user_id, db)
    if db_progress and (db_progress.get("completed_nodes") or db_progress.get("node_scores")):
        progress = db_progress
    else:
        progress = load_progress(user_id)

    tree = build_tree()
    total_leaves = tree.get("total_leaves", 0)
    leaf_ids = leaf_ids_from_tree(tree)
    stats = progress_stats(progress, total_leaves, leaf_ids)

    return {
        "username": current_user.username,
        "completed_nodes": progress.get("completed_nodes", []),
        "node_scores": progress.get("node_scores", {}),
        "total": total_leaves,
        "percentage": stats["percentage"],
        "stats": stats,
    }


@router.get("/knowledge-graph/progress/graph")
async def get_graph_with_progress(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取带当前用户掌握度的力导向图数据。
    DB 优先（可信源），文件作为降级缓存。
    """
    user_id = current_user.id
    db_progress = await load_progress_from_db(user_id, db)
    if db_progress and (db_progress.get("completed_nodes") or db_progress.get("node_scores")):
        progress = db_progress
    else:
        progress = load_progress(user_id)
    return build_graph(progress)


@router.get("/knowledge-graph/progress/all")
async def get_all_progress(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    管理员查看所有学员的学习进度。
    优先从数据库读取 kg_progress，降级到文件读取。
    """
    tree = build_tree()
    total_leaves = tree.get("total_leaves", 0)
    leaf_ids = leaf_ids_from_tree(tree)

    all_progress = []
    stmt = (
        select(User.id, User.username, Learner.kg_progress)
        .select_from(User)
        .outerjoin(Learner, Learner.user_id == User.id)
        .where(User.role == "learner")
    )
    result = await db.execute(stmt)
    rows = result.all()

    for uid, username, kg_progress in rows:
        if kg_progress and isinstance(kg_progress, dict):
            kg = normalize_progress(kg_progress)
        else:
            kg = load_progress(uid)

        completed = kg.get("completed_nodes", [])
        stats = progress_stats(kg, total_leaves, leaf_ids)

        all_progress.append({
            "username": username,
            "completed_nodes": completed,
            "node_scores": kg.get("node_scores", {}),
            "completed_count": len(completed),
            "total": total_leaves,
            "percentage": stats["percentage"],
            "stats": stats,
        })

    return {
        "total_learners": len(all_progress),
        "total_knowledge_points": total_leaves,
        "learners": all_progress,
    }


@router.get("/knowledge-graph/progress/tree")
async def get_tree_with_progress(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取带当前用户学习进度标记的树状图数据。每个叶子节点附加 completed 字段。
    DB 优先（可信源），文件作为降级缓存。
    """
    if not CATEGORY_LABELS:
        init_category_labels()

    tree = build_tree()
    user_id = current_user.id
    db_progress = await load_progress_from_db(user_id, db)
    if db_progress and (db_progress.get("completed_nodes") or db_progress.get("node_scores")):
        progress = db_progress
    else:
        progress = load_progress(user_id)
    completed = set(progress.get("completed_nodes", []))
    node_scores = progress.get("node_scores", {})

    def _attach_progress(node: dict) -> None:
        if node.get("is_leaf"):
            score = clamp_score(node_scores.get(node.get("id"), {}).get("score", 0))
            status = status_from_score(score)
            node["score"] = score
            node["status"] = status
            node["status_label"] = status_label(status)
            node["completed"] = node.get("id") in completed
        for child in node.get("children", []):
            _attach_progress(child)

    for child in tree.get("children", []):
        _attach_progress(child)

    return tree


# ── 管理员端：同步所有学员进度到 DB ──

@router.post("/knowledge-graph/progress/sync-all")
async def sync_all_progress_to_db(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """管理员触发：将所有学员的本地进度文件同步到数据库。"""
    tree = build_tree()
    total_leaves = tree.get("total_leaves", 0)
    leaf_ids = leaf_ids_from_tree(tree)
    synced = 0
    failed = 0

    if PROGRESS_DIR.exists():
        for f in PROGRESS_DIR.glob("*.json"):
            stem = f.stem
            try:
                # 文件名格式：user_{user_id}.json
                if not stem.startswith("user_"):
                    logger.warning("跳过旧格式进度文件: %s（应为 user_{id}.json）", f.name)
                    continue
                id_str = stem[5:]
                if not id_str.isdigit():
                    logger.warning("跳过非法进度文件: %s", f.name)
                    continue
                user_id = int(id_str)

                data = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    progress = normalize_progress(data)
                    completed = progress.get("completed_nodes", [])
                    stats = progress_stats(progress, total_leaves, leaf_ids)

                    kg_data = {
                        "completed_nodes": completed,
                        "node_scores": progress.get("node_scores", {}),
                        "history": progress.get("history", []),
                        "percentage": stats["percentage"],
                        "total": total_leaves,
                        "stats": stats,
                    }

                    stmt = select(Learner).where(Learner.user_id == user_id)
                    r = await db.execute(stmt)
                    learner = r.scalar_one_or_none()
                    if learner:
                        learner.kg_progress = kg_data
                        synced += 1
                    else:
                        failed += 1
            except Exception as e:  # noqa: BLE001
                logger.warning("同步进度失败 %s: %s", stem, e)
                failed += 1

        if synced > 0:
            await db.flush()

    return {
        "ok": True,
        "synced": synced,
        "failed": failed,
        "message": f"已同步 {synced} 个学员的知识图谱进度到数据库" + (f"，{failed} 个失败" if failed else ""),
    }


# ── 向后兼容 re-export ──
# 保留旧路径 ``from app.api.knowledge_graph import build_kg_progress_for_learner``
# 以及 ``from app.api.knowledge_graph import mark_learning_event_by_learner_id`` 可用。
__all__ = [
    "router",
    "ProgressRequest",
    "ProgressResponse",
    "build_kg_progress_for_learner",
    "mark_learning_event_by_learner_id",
    "auto_mark_completed",
]
