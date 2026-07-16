"""知识图谱 —— 掌握度评分与进度持久化。

包含：
- 分数规范化与状态映射（``clamp_score``、``status_from_score``、``status_label``）
- 进度结构统一（``normalize_progress``、``normalize_node_scores``）
- 单节点评分更新（``apply_score_update``）
- 文件缓存与 DB 同步（``load_progress``、``save_progress``、``sync_progress_to_db``、``load_progress_from_db``）
- 构造可写入 ``learner.kg_progress`` 的字典（``build_kg_progress_for_learner``）
"""

from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.learner import Learner
from app.services.kg_tree import PROGRESS_DIR, build_tree, leaf_ids_from_tree

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════
# 评分/状态工具
# ═══════════════════════════════════════════

def clamp_score(score: Any, default: int = 0) -> int:
    """标准化掌握度分数，兼容 0-1 和 0-100 两种输入。"""
    try:
        value = float(score)
    except (TypeError, ValueError):
        value = float(default)
    if 0 < value <= 1:
        value *= 100
    return max(0, min(100, int(round(value))))


def status_from_score(score: int) -> str:
    """掌握度状态：mastered / learning / weak / recommended。"""
    if score >= 80:
        return "mastered"
    if score >= 60:
        return "learning"
    if score > 0:
        return "weak"
    return "recommended"


def status_label(status: str) -> str:
    labels = {
        "mastered": "掌握度 >= 80%",
        "learning": "掌握度 60-79%",
        "weak": "掌握度 < 60%",
        "recommended": "建议重点学习",
    }
    return labels.get(status, status)


def normalize_node_scores(raw_scores: Any) -> dict[str, dict]:
    """兼容旧/新 node_scores 结构，统一为 {node_id: {score, status, ...}}。"""
    node_scores: dict[str, dict] = {}
    if not isinstance(raw_scores, dict):
        return node_scores

    for node_id, value in raw_scores.items():
        if not node_id:
            continue
        if isinstance(value, dict):
            entry = dict(value)
            score = clamp_score(entry.get("score", 0))
        else:
            entry = {}
            score = clamp_score(value)
        entry["score"] = score
        entry["status"] = status_from_score(score)
        node_scores[str(node_id)] = entry
    return node_scores


def normalize_progress(data: Any) -> dict:
    """
    统一学习进度结构。
    兼容旧版 {completed_nodes, history}，新版额外包含 node_scores。
    """
    if not isinstance(data, dict):
        data = {}

    history = data.get("history", [])
    if not isinstance(history, list):
        history = []

    completed = data.get("completed_nodes", [])
    if not isinstance(completed, list):
        completed = []

    # 旧文件可能只有 history，没有 completed_nodes，先从历史重建。
    if not completed and history:
        completed_set = set()
        for entry in history:
            if not isinstance(entry, dict):
                continue
            nid = entry.get("node_id", "")
            action = entry.get("action", "")
            if not nid:
                continue
            if action in ("completed", "auto_completed", "score_update"):
                score = clamp_score(entry.get("score", 100 if action != "score_update" else 0))
                if score >= 80:
                    completed_set.add(nid)
            elif action == "uncompleted":
                completed_set.discard(nid)
        completed = sorted(completed_set)

    node_scores = normalize_node_scores(data.get("node_scores", {}))

    # 旧版 completed_nodes 视为已掌握，补齐 node_scores。
    for node_id in completed:
        current = node_scores.get(node_id, {})
        if clamp_score(current.get("score", 0)) < 80:
            current.update({
                "score": 100,
                "status": "mastered",
                "source": current.get("source", "legacy_completed"),
            })
            node_scores[node_id] = current

    completed_nodes = sorted(
        node_id
        for node_id, entry in node_scores.items()
        if clamp_score(entry.get("score", 0)) >= 80
    )

    return {
        "completed_nodes": completed_nodes,
        "node_scores": node_scores,
        "history": history,
    }


def progress_stats(progress: dict, total_leaves: int, leaf_ids: set[str] | None = None) -> dict:
    """按叶子知识点统计掌握度分布。"""
    progress = normalize_progress(progress)
    node_scores = progress.get("node_scores", {})
    target_ids = leaf_ids or set(node_scores.keys())
    scores = [
        clamp_score(node_scores.get(node_id, {}).get("score", 0))
        for node_id in target_ids
    ]
    total = total_leaves if total_leaves else len(scores)
    mastered = sum(1 for score in scores if score >= 80)
    learning = sum(1 for score in scores if 60 <= score < 80)
    weak = sum(1 for score in scores if 0 < score < 60)
    recommended = max(0, total - mastered - learning - weak)
    average_score = round(sum(scores) / total, 1) if total > 0 else 0
    percentage = round(mastered / total * 100, 1) if total > 0 else 0
    return {
        "total": total,
        "mastered": mastered,
        "learning": learning,
        "weak": weak,
        "recommended": recommended,
        "to_improve": max(0, total - mastered),
        "average_score": average_score,
        "percentage": percentage,
    }


def apply_score_update(
    progress: dict,
    node_id: str,
    score: Any,
    source: str = "manual",
    action: str = "score_update",
    extra: dict | None = None,
) -> dict:
    """更新单个节点掌握度，并同步 completed_nodes。"""
    progress = normalize_progress(progress)
    score_value = clamp_score(score)
    status = status_from_score(score_value)

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    previous = progress["node_scores"].get(node_id, {})
    previous_score = clamp_score(previous.get("score", 0))
    entry = dict(previous)
    entry.update({
        "score": score_value,
        "status": status,
        "source": source,
        "updated_at": now,
    })
    progress["node_scores"][node_id] = entry

    history_entry = {
        "node_id": node_id,
        "action": action,
        "timestamp": now,
        "source": source,
        "score": score_value,
        "status": status,
        "previous_score": previous_score,
    }
    if extra:
        history_entry.update(extra)
    progress["history"].append(history_entry)

    progress["completed_nodes"] = sorted(
        nid
        for nid, node_score in progress["node_scores"].items()
        if clamp_score(node_score.get("score", 0)) >= 80
    )
    return progress


# ═══════════════════════════════════════════
# 文件缓存
# ═══════════════════════════════════════════

def progress_file_path(user_id: int | str) -> Path:
    """获取用户进度文件路径（按 user_id 索引，避免同用户名跨账户共享残留数据）。"""
    PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
    safe_id = "".join(c for c in str(user_id) if c.isalnum())
    if not safe_id:
        safe_id = "anonymous"
    return PROGRESS_DIR / f"user_{safe_id}.json"


def load_progress(user_id: int | str) -> dict:
    """加载用户学习进度，返回 {completed_nodes, node_scores, history}。"""
    file_path = progress_file_path(user_id)
    if file_path.exists():
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return normalize_progress(data)
        except Exception:  # noqa: BLE001
            logger.warning("进度文件损坏，重新创建: %s", file_path)
    return normalize_progress({})


def save_progress(user_id: int | str, progress: dict) -> None:
    """保存用户学习进度到文件（仅作为 DB 降级缓存）。"""
    file_path = progress_file_path(user_id)
    file_path.write_text(
        json.dumps(progress, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ═══════════════════════════════════════════
# DB 同步
# ═══════════════════════════════════════════

async def sync_progress_to_db(user_id: int | str, progress: dict, db: AsyncSession) -> None:
    """将知识图谱进度同步到数据库 learners.kg_progress。"""
    tree = build_tree()
    total_leaves = tree.get("total_leaves", 0)
    leaf_ids = leaf_ids_from_tree(tree)
    progress = normalize_progress(progress)
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

    try:
        stmt = select(Learner).where(Learner.user_id == int(user_id))
        result = await db.execute(stmt)
        learner = result.scalar_one_or_none()
        if learner:
            learner.kg_progress = kg_data
            await db.flush()
            logger.info("[KG进度同步到DB] user_id=%s, 进度=%s%%", user_id, stats["percentage"])
    except Exception as e:  # noqa: BLE001
        logger.warning("[KG进度同步到DB失败] user_id=%s: %s", user_id, e)


async def load_progress_from_db(user_id: int | str, db: AsyncSession) -> dict | None:
    """从数据库加载知识图谱进度。"""
    try:
        stmt = select(Learner).where(Learner.user_id == int(user_id))
        result = await db.execute(stmt)
        learner = result.scalar_one_or_none()
        if learner and learner.kg_progress and isinstance(learner.kg_progress, dict):
            kg = learner.kg_progress
            return normalize_progress({
                "completed_nodes": kg.get("completed_nodes", []),
                "node_scores": kg.get("node_scores", {}),
                "history": kg.get("history", []),
            })
    except Exception as e:  # noqa: BLE001
        logger.warning("[KG进度从DB加载失败] user_id=%s: %s", user_id, e)
    return None


def build_kg_progress_for_learner(user_id: int | str = "") -> dict:
    """
    构建可写入 learner.kg_progress 的知识图谱进度字典。
    纯同步函数，不依赖 DB session，可安全地在任何上下文中调用。
    user_id 为空时返回空进度（用于初始化）。
    """
    tree = build_tree()
    total_leaves = tree.get("total_leaves", 0)
    leaf_ids = leaf_ids_from_tree(tree)
    progress = load_progress(user_id) if user_id != "" else normalize_progress({})
    stats = progress_stats(progress, total_leaves, leaf_ids)
    return {
        "completed_nodes": progress.get("completed_nodes", []),
        "node_scores": progress.get("node_scores", {}),
        "history": progress.get("history", []),
        "percentage": stats["percentage"],
        "total": total_leaves,
        "stats": stats,
    }
