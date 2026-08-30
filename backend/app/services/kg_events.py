"""知识图谱 —— 学习事件触发的自动打点。

这些函数由其它 API（学习路径完成、答题结束等）调用，用于把学习行为
反映到知识图谱的掌握度上，实现"学生学到就点亮"。

进度以 DB（learners.kg_progress）为唯一真源读写。
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.learner import Learner
from app.models.user import User
from app.services.kg_progress import (
    apply_score_update,
    clamp_score,
    empty_kg_progress,
    load_user_progress,
    sync_progress_to_db,
)
from app.services.kg_tree import (
    collect_leaf_index,
    match_leaf_id,
)

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
    progress = await load_user_progress(learner.user_id, db)
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
        await sync_progress_to_db(learner.user_id, progress, db)
    elif learner.kg_progress is None:
        learner.kg_progress = empty_kg_progress()

    return {
        "marked_count": len(matched),
        "matched": matched,
    }
