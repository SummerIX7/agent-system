"""知识图谱 —— 学习事件触发的自动打点。

这些函数由其它 API（学习路径完成、答题结束等）调用，用于把学习行为
反映到知识图谱的掌握度上，实现"学生学到就点亮"。
"""

from __future__ import annotations

import datetime
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.learner import Learner
from app.models.user import User
from app.services.kg_progress import (
    apply_score_update,
    build_kg_progress_for_learner,
    clamp_score,
    load_progress,
    normalize_progress,
    save_progress,
    sync_progress_to_db,
)
from app.services.kg_tree import (
    build_tree,
    collect_leaf_index,
    init_category_labels,
    match_leaf_id,
)
from app.services.kg_tree import CATEGORY_LABELS

logger = logging.getLogger(__name__)


async def mark_learning_event_by_learner_id(
    db: AsyncSession,
    learner_id: str | int,
    knowledge_items: list[str],
    score: Any,
    source: str,
) -> dict:
    """
    根据学习路径/考核事件更新知识图谱掌握度。
    用于"学生学习了会点亮"的自动触发，不改变原有业务表结构。
    """
    try:
        lid = int(learner_id)
    except (ValueError, TypeError):
        return {"marked_count": 0, "matched": []}

    stmt = select(Learner, User.username).join(User, Learner.user_id == User.id).where(Learner.id == lid)
    result = await db.execute(stmt)
    row = result.one_or_none()
    if not row:
        return {"marked_count": 0, "matched": []}

    learner, username = row  # noqa: F841 (保留结构便于将来审计)
    # 进度按 user_id 索引（而非 username），避免同用户名跨账户共享残留数据
    progress = load_progress(learner.user_id)
    leaf_nodes = collect_leaf_index()
    matched: list[dict] = []

    for item in knowledge_items:
        leaf_id = match_leaf_id(str(item), leaf_nodes)
        if not leaf_id:
            continue
        current_score = clamp_score(progress.get("node_scores", {}).get(leaf_id, {}).get("score", 0))
        target_score = max(current_score, clamp_score(score))
        progress = apply_score_update(
            progress,
            leaf_id,
            target_score,
            source=source,
            action="score_update",
            extra={"matched_name": item},
        )
        matched.append({
            "node_id": leaf_id,
            "matched_name": item,
            "score": target_score,
        })

    if matched:
        save_progress(learner.user_id, progress)
        await sync_progress_to_db(learner.user_id, progress, db)
    elif learner.kg_progress is None:
        learner.kg_progress = build_kg_progress_for_learner(learner.user_id)

    return {
        "marked_count": len(matched),
        "matched": matched,
    }


def auto_mark_completed(user_id: int | str, knowledge_items: list[str]) -> dict:
    """
    根据分析报告涉及的知识点，自动标记对应知识图谱节点为已学习。

    Args:
        user_id: 用户 ID
        knowledge_items: 知识点名称列表（从分析报告或 learner profile 中提取）

    Returns:
        dict: { marked_count, total_provided, ... }
    """
    if not CATEGORY_LABELS:
        init_category_labels()

    tree = build_tree()
    progress = load_progress(user_id)
    completed = set(progress["completed_nodes"])

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    marked_count = 0

    leaf_nodes = collect_leaf_index()

    for item_name in knowledge_items:
        if not item_name:
            continue

        matched_id = match_leaf_id(item_name, leaf_nodes)

        if matched_id and matched_id not in completed:
            completed.add(matched_id)
            progress["history"].append({
                "node_id": matched_id,
                "action": "auto_completed",
                "timestamp": now,
                "source": "analysis_report",
                "matched_name": item_name,
            })
            marked_count += 1

    progress["completed_nodes"] = sorted(completed)
    progress = normalize_progress(progress)
    save_progress(user_id, progress)

    total_leaves = tree.get("total_leaves", 0)
    percentage = round(len(completed) / total_leaves * 100, 1) if total_leaves > 0 else 0

    logger.info(
        "[知识图谱自动标记] user_id=%s, 提供知识点=%d, 匹配成功=%d, 总进度=%d/%d (%s%%)",
        user_id, len(knowledge_items), marked_count, len(completed), total_leaves, percentage,
    )

    return {
        "user_id": user_id,
        "marked_count": marked_count,
        "total_provided": len(knowledge_items),
        "completed_nodes": progress.get("completed_nodes", []),
        "total": total_leaves,
        "percentage": percentage,
    }
