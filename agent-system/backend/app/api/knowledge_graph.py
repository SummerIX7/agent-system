"""
知识图谱 API — 树状图数据结构，支持学习进度标记。
从 cnc_domain 目录结构构建 ECharts Tree 适配的 JSON 数据。
学习进度同时持久化到数据库（learners.kg_progress）和本地 JSON 文件。
"""
import asyncio
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_admin
from app.core.config import get_settings
from app.models.database import get_db
from app.models.learner import Learner
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["知识图谱"])

# ── 路径配置 ──
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_PROJECT_ROOT = _BACKEND_DIR.parent


def _resolve_kb_dir() -> Path:
    """从 .env 的 KNOWLEDGE_BASE_DIRS 解析知识库目录，避免硬编码本机路径。"""
    first_dir = get_settings().KNOWLEDGE_BASE_DIRS.split(",")[0].strip()
    path = Path(first_dir)
    if not path.is_absolute():
        path = _BACKEND_DIR / path
    return path.resolve()


_KNOWLEDGE_BASE_DIR = _resolve_kb_dir()
_PROGRESS_DIR = (_PROJECT_ROOT / "data" / "progress").resolve()

# ── 分类中文标签映射 ──
_CATEGORY_LABELS: dict[str, str] = {}


def _init_category_labels() -> None:
    """根据实际子文件夹名动态生成标签映射。"""
    predefined = {
        "theory": "理论基础",
        "practice": "实践技能",
        "standards": "标准规范",
    }
    if _KNOWLEDGE_BASE_DIR.exists():
        for d in _KNOWLEDGE_BASE_DIR.iterdir():
            if d.is_dir():
                _CATEGORY_LABELS[d.name] = predefined.get(d.name, d.name)


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """解析 Markdown 文件的 YAML 前置元数据"""
    metadata = {}
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1].strip()
            body = parts[2].strip()
            for line in frontmatter.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    metadata[key.strip()] = value.strip()
            return metadata, body
    return metadata, content


def _node_id_from_path(rel_path: str) -> str:
    """基于相对路径生成唯一节点 ID"""
    return hashlib.md5(rel_path.encode("utf-8")).hexdigest()[:12]


def _category_label(cat: str) -> str:
    """分类英文 → 中文标签"""
    return _CATEGORY_LABELS.get(cat, cat)


def _build_tree() -> dict:
    """
    从 cnc_domain 目录结构构建树形数据。
    根节点: 数控加工知识体系
    一级节点: 子文件夹（theory / practice / standards）
    二级节点（叶子）: Markdown 文件
    """
    if not _KNOWLEDGE_BASE_DIR.exists():
        return {"name": "数控加工知识体系", "children": []}

    if not _CATEGORY_LABELS:
        _init_category_labels()

    root = {
        "name": "数控加工知识体系",
        "id": "root",
        "children": [],
    }

    # 获取所有子文件夹
    subdirs = sorted([d for d in _KNOWLEDGE_BASE_DIR.iterdir() if d.is_dir()],
                     key=lambda d: d.name)

    for subdir in subdirs:
        category_key = subdir.name
        category_name = _category_label(category_key)
        cat_id = _node_id_from_path(category_key)

        cat_node = {
            "name": category_name,
            "id": cat_id,
            "category": category_key,
            "children": [],
        }

        # 获取子文件夹下的所有 Markdown 文件
        md_files = sorted(subdir.glob("*.md"), key=lambda f: f.stem)

        for md_file in md_files:
            rel_path = str(md_file.relative_to(_KNOWLEDGE_BASE_DIR))
            file_id = _node_id_from_path(rel_path)

            try:
                content = md_file.read_text(encoding="utf-8")
                metadata, _ = _parse_frontmatter(content)
            except Exception:
                metadata = {}

            leaf_node = {
                "name": metadata.get("title", md_file.stem),
                "id": file_id,
                "category": category_key,
                "file": rel_path,
                "is_leaf": True,
                "source_type": metadata.get("source_type", ""),
                "author": metadata.get("author", ""),
                "year": metadata.get("year", ""),
                "chapter": metadata.get("chapter", ""),
                "source_name": metadata.get("source_name", ""),
            }
            cat_node["children"].append(leaf_node)

        root["children"].append(cat_node)

    # 统计叶子节点总数
    leaf_count = sum(
        sum(1 for c2 in c1["children"] if c2.get("is_leaf"))
        for c1 in root["children"]
    )
    root["total_leaves"] = leaf_count

    return root


def _collect_leaf_index() -> dict[str, str]:
    """收集所有叶子节点：name → id 的索引"""
    if not _CATEGORY_LABELS:
        _init_category_labels()
    tree = _build_tree()
    leaf_nodes: dict[str, str] = {}

    def _collect(node: dict):
        if node.get("is_leaf"):
            leaf_nodes[node["name"]] = node["id"]
        for child in node.get("children", []):
            _collect(child)

    for child in tree.get("children", []):
        _collect(child)
    return leaf_nodes


def _clamp_score(score: Any, default: int = 0) -> int:
    """标准化掌握度分数，兼容 0-1 和 0-100 两种输入。"""
    try:
        value = float(score)
    except (TypeError, ValueError):
        value = float(default)
    if 0 < value <= 1:
        value *= 100
    return max(0, min(100, int(round(value))))


def _status_from_score(score: int) -> str:
    """掌握度状态：mastered / learning / weak / recommended。"""
    if score >= 80:
        return "mastered"
    if score >= 60:
        return "learning"
    if score > 0:
        return "weak"
    return "recommended"


def _status_label(status: str) -> str:
    labels = {
        "mastered": "掌握度 >= 80%",
        "learning": "掌握度 60-79%",
        "weak": "掌握度 < 60%",
        "recommended": "建议重点学习",
    }
    return labels.get(status, status)


def _normalize_node_scores(raw_scores: Any) -> dict[str, dict]:
    """兼容旧/新 node_scores 结构，统一为 {node_id: {score, status, ...}}。"""
    node_scores: dict[str, dict] = {}
    if not isinstance(raw_scores, dict):
        return node_scores

    for node_id, value in raw_scores.items():
        if not node_id:
            continue
        if isinstance(value, dict):
            entry = dict(value)
            score = _clamp_score(entry.get("score", 0))
        else:
            entry = {}
            score = _clamp_score(value)
        entry["score"] = score
        entry["status"] = _status_from_score(score)
        node_scores[str(node_id)] = entry
    return node_scores


def _normalize_progress(data: Any) -> dict:
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
                score = _clamp_score(entry.get("score", 100 if action != "score_update" else 0))
                if score >= 80:
                    completed_set.add(nid)
            elif action == "uncompleted":
                completed_set.discard(nid)
        completed = sorted(completed_set)

    node_scores = _normalize_node_scores(data.get("node_scores", {}))

    # 旧版 completed_nodes 视为已掌握，补齐 node_scores。
    for node_id in completed:
        current = node_scores.get(node_id, {})
        if _clamp_score(current.get("score", 0)) < 80:
            current.update({
                "score": 100,
                "status": "mastered",
                "source": current.get("source", "legacy_completed"),
            })
            node_scores[node_id] = current

    completed_nodes = sorted(
        node_id
        for node_id, entry in node_scores.items()
        if _clamp_score(entry.get("score", 0)) >= 80
    )

    return {
        "completed_nodes": completed_nodes,
        "node_scores": node_scores,
        "history": history,
    }


def _leaf_ids_from_tree(tree: dict) -> set[str]:
    ids: set[str] = set()

    def _walk(node: dict) -> None:
        if node.get("is_leaf") and node.get("id"):
            ids.add(node["id"])
        for child in node.get("children", []):
            _walk(child)

    _walk(tree)
    return ids


def _progress_stats(progress: dict, total_leaves: int, leaf_ids: set[str] | None = None) -> dict:
    """按叶子知识点统计掌握度分布。"""
    progress = _normalize_progress(progress)
    node_scores = progress.get("node_scores", {})
    target_ids = leaf_ids or set(node_scores.keys())
    scores = [
        _clamp_score(node_scores.get(node_id, {}).get("score", 0))
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


def _apply_score_update(
    progress: dict,
    node_id: str,
    score: Any,
    source: str = "manual",
    action: str = "score_update",
    extra: dict | None = None,
) -> dict:
    """更新单个节点掌握度，并同步 completed_nodes。"""
    progress = _normalize_progress(progress)
    score_value = _clamp_score(score)
    status = _status_from_score(score_value)

    import datetime
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    previous = progress["node_scores"].get(node_id, {})
    previous_score = _clamp_score(previous.get("score", 0))
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
        if _clamp_score(node_score.get("score", 0)) >= 80
    )
    return progress


def _match_leaf_id(item_name: str, leaf_nodes: dict[str, str]) -> str | None:
    """将学习路径主题/知识点名称匹配到知识库叶子节点 ID。"""
    if not item_name:
        return None

    def _normalize(s: str) -> str:
        return s.replace(" ", "").replace("　", "").strip()

    norm_item = _normalize(item_name)
    matched_id = leaf_nodes.get(item_name)
    if matched_id:
        return matched_id

    for leaf_name, leaf_id in leaf_nodes.items():
        if _normalize(leaf_name) == norm_item:
            return leaf_id

    for leaf_name, leaf_id in leaf_nodes.items():
        norm_leaf = _normalize(leaf_name)
        if norm_item in norm_leaf or norm_leaf in norm_item:
            return leaf_id

    if len(item_name) >= 2:
        keywords = item_name.replace("（", " ").replace("）", " ")
        keywords = keywords.replace("(", " ").replace(")", " ")
        keywords = keywords.replace("/", " ").replace("、", " ").replace("，", " ")
        keywords = keywords.replace("与", " ").replace("及", " ").replace("的", " ")
        for kw in keywords.split():
            if len(kw) < 2:
                continue
            norm_kw = _normalize(kw)
            for leaf_name, leaf_id in leaf_nodes.items():
                if norm_kw in _normalize(leaf_name):
                    return leaf_id

    return None


async def mark_learning_event_by_learner_id(
    db: AsyncSession,
    learner_id: str | int,
    knowledge_items: list[str],
    score: Any,
    source: str,
) -> dict:
    """
    根据学习路径/考核事件更新知识图谱掌握度。
    用于“学生学习了会点亮”的自动触发，不改变原有业务表结构。
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

    learner, username = row
    # 进度按 user_id 索引（而非 username），避免同用户名跨账户共享残留数据
    progress = _load_progress(learner.user_id)
    leaf_nodes = _collect_leaf_index()
    matched: list[dict] = []

    for item in knowledge_items:
        leaf_id = _match_leaf_id(str(item), leaf_nodes)
        if not leaf_id:
            continue
        current_score = _clamp_score(progress.get("node_scores", {}).get(leaf_id, {}).get("score", 0))
        target_score = max(current_score, _clamp_score(score))
        progress = _apply_score_update(
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
        _save_progress(learner.user_id, progress)
        await _sync_progress_to_db(learner.user_id, progress, db)
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
    if not _CATEGORY_LABELS:
        _init_category_labels()

    tree = _build_tree()
    progress = _load_progress(user_id)
    completed = set(progress["completed_nodes"])

    import datetime
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    marked_count = 0

    # 收集所有叶子节点 → 按名称建立索引
    leaf_nodes = _collect_leaf_index()

    # 遍历知识点名称，匹配并标记
    for item_name in knowledge_items:
        if not item_name:
            continue

        matched_id = None

        # 归一化比较函数：去空格后比较
        def _normalize(s: str) -> str:
            return s.replace(" ", "").replace("　", "").strip()

        norm_item = _normalize(item_name)

        # 1. 精确匹配（原始名称）
        matched_id = leaf_nodes.get(item_name)

        # 2. 归一化后精确匹配（去空格）
        if not matched_id:
            for leaf_name, leaf_id in leaf_nodes.items():
                if _normalize(leaf_name) == norm_item:
                    matched_id = leaf_id
                    break

        # 3. 模糊匹配：归一化后子串包含
        if not matched_id:
            for leaf_name, leaf_id in leaf_nodes.items():
                norm_leaf = _normalize(leaf_name)
                if norm_item in norm_leaf or norm_leaf in norm_item:
                    matched_id = leaf_id
                    break

        # 4. 尝试匹配关键字（拆分后至少有一个关键字匹配）
        if not matched_id and len(item_name) >= 2:
            keywords = item_name.replace("（", " ").replace("）", " ")
            keywords = keywords.replace("(", " ").replace(")", " ")
            keywords = keywords.replace("/", " ").replace("、", " ").replace("，", " ")
            keywords = keywords.replace("与", " ").replace("及", " ").replace("的", " ")
            keywords = keywords.split()
            for kw in keywords:
                if len(kw) < 2:
                    continue
                norm_kw = _normalize(kw)
                for leaf_name, leaf_id in leaf_nodes.items():
                    if norm_kw in _normalize(leaf_name):
                        matched_id = leaf_id
                        break
                if matched_id:
                    break

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
    progress = _normalize_progress(progress)
    _save_progress(user_id, progress)

    total_leaves = tree.get("total_leaves", 0)
    percentage = round(len(completed) / total_leaves * 100, 1) if total_leaves > 0 else 0

    logger.info(
        f"[知识图谱自动标记] user_id={user_id}, "
        f"提供知识点={len(knowledge_items)}, 匹配成功={marked_count}, "
        f"总进度={len(completed)}/{total_leaves} ({percentage}%)"
    )

    return {
        "user_id": user_id,
        "marked_count": marked_count,
        "total_provided": len(knowledge_items),
        "completed_nodes": progress.get("completed_nodes", []),
        "total": total_leaves,
        "percentage": percentage,
    }


# ── 进度文件管理（文件作为持久化备份，DB 作为主存储）──

def _progress_file_path(user_id: int | str) -> Path:
    """获取用户进度文件路径（按 user_id 索引，避免同用户名跨账户共享残留数据）"""
    _PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
    safe_id = "".join(c for c in str(user_id) if c.isalnum())
    if not safe_id:
        safe_id = "anonymous"
    return _PROGRESS_DIR / f"user_{safe_id}.json"


def _load_progress(user_id: int | str) -> dict:
    """加载用户学习进度，返回 {completed_nodes, node_scores, history}"""
    file_path = _progress_file_path(user_id)
    if file_path.exists():
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return _normalize_progress(data)
        except Exception:
            logger.warning(f"进度文件损坏，重新创建: {file_path}")
    return _normalize_progress({})


def _save_progress(user_id: int | str, progress: dict) -> None:
    """保存用户学习进度到文件（仅作为 DB 降级缓存）"""
    file_path = _progress_file_path(user_id)
    file_path.write_text(
        json.dumps(progress, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


async def _sync_progress_to_db(user_id: int | str, progress: dict, db: AsyncSession) -> None:
    """将知识图谱进度同步到数据库 learners.kg_progress"""
    tree = _build_tree()
    total_leaves = tree.get("total_leaves", 0)
    leaf_ids = _leaf_ids_from_tree(tree)
    leaf_ids = _leaf_ids_from_tree(tree)
    progress = _normalize_progress(progress)
    completed = progress.get("completed_nodes", [])
    stats = _progress_stats(progress, total_leaves, leaf_ids)

    kg_data = {
        "completed_nodes": completed,
        "node_scores": progress.get("node_scores", {}),
        "history": progress.get("history", []),
        "percentage": stats["percentage"],
        "total": total_leaves,
        "stats": stats,
    }

    try:
        # 通过 user_id 直接查找 learner（无需 join User 表）
        stmt = select(Learner).where(Learner.user_id == int(user_id))
        result = await db.execute(stmt)
        learner = result.scalar_one_or_none()
        if learner:
            learner.kg_progress = kg_data
            await db.flush()
            logger.info(f"[KG进度同步到DB] user_id={user_id}, 进度={stats['percentage']}%")
    except Exception as e:
        logger.warning(f"[KG进度同步到DB失败] user_id={user_id}: {e}")


async def _load_progress_from_db(user_id: int | str, db: AsyncSession) -> dict | None:
    """从数据库加载知识图谱进度"""
    try:
        stmt = select(Learner).where(Learner.user_id == int(user_id))
        result = await db.execute(stmt)
        learner = result.scalar_one_or_none()
        if learner and learner.kg_progress and isinstance(learner.kg_progress, dict):
            kg = learner.kg_progress
            return _normalize_progress({
                "completed_nodes": kg.get("completed_nodes", []),
                "node_scores": kg.get("node_scores", {}),
                "history": kg.get("history", []),
            })
    except Exception as e:
        logger.warning(f"[KG进度从DB加载失败] user_id={user_id}: {e}")
    return None


def build_kg_progress_for_learner(user_id: int | str = "") -> dict:
    """
    构建可写入 learner.kg_progress 的知识图谱进度字典。
    纯同步函数，不依赖 DB session，可安全地在任何上下文中调用。
    user_id 为空时返回空进度（用于初始化）。
    """
    tree = _build_tree()
    total_leaves = tree.get("total_leaves", 0)
    leaf_ids = _leaf_ids_from_tree(tree)
    progress = _load_progress(user_id) if user_id != "" else _normalize_progress({})
    stats = _progress_stats(progress, total_leaves, leaf_ids)
    return {
        "completed_nodes": progress.get("completed_nodes", []),
        "node_scores": progress.get("node_scores", {}),
        "history": progress.get("history", []),
        "percentage": stats["percentage"],
        "total": total_leaves,
        "stats": stats,
    }


def _get_or_init_progress(user_id: int | str, db: AsyncSession | None = None) -> dict:
    """获取用户进度：优先从文件读取，DB 作为补充"""
    return _load_progress(user_id)


def _build_graph(progress: dict | None = None) -> dict:
    """
    构建力导向图数据。
    nodes / links 适配 ECharts graph；叶子节点附带 score/status。
    """
    if not _CATEGORY_LABELS:
        _init_category_labels()

    tree = _build_tree()
    progress = _normalize_progress(progress or {})
    node_scores = progress.get("node_scores", {})

    nodes: list[dict] = []
    links: list[dict] = []
    category_stats: list[dict] = []
    leaf_ids: set[str] = set()
    leaf_scores: list[int] = []

    def _node_score(node_id: str) -> int:
        return _clamp_score(node_scores.get(node_id, {}).get("score", 0))

    root_id = tree.get("id", "root")
    nodes.append({
        "id": root_id,
        "name": tree.get("name", "数控加工知识体系"),
        "type": "root",
        "category": "root",
        "category_label": "知识体系",
        "score": 0,
        "status": "recommended",
        "status_label": _status_label("recommended"),
        "is_leaf": False,
    })

    for cat_node in tree.get("children", []):
        cat_id = cat_node.get("id")
        cat_key = cat_node.get("category", "")
        cat_label = cat_node.get("name", _category_label(cat_key))
        cat_leaf_scores: list[int] = []

        nodes.append({
            "id": cat_id,
            "name": cat_label,
            "type": "category",
            "category": cat_key,
            "category_label": cat_label,
            "score": 0,
            "status": "recommended",
            "status_label": _status_label("recommended"),
            "is_leaf": False,
        })
        links.append({
            "source": root_id,
            "target": cat_id,
            "relation": "contains",
        })

        for leaf in cat_node.get("children", []):
            if not leaf.get("is_leaf"):
                continue
            leaf_id = leaf.get("id")
            score = _node_score(leaf_id)
            status = _status_from_score(score)
            leaf_ids.add(leaf_id)
            leaf_scores.append(score)
            cat_leaf_scores.append(score)

            nodes.append({
                "id": leaf_id,
                "name": leaf.get("name", ""),
                "type": "knowledge",
                "category": cat_key,
                "category_label": cat_label,
                "score": score,
                "status": status,
                "status_label": _status_label(status),
                "is_leaf": True,
                "file": leaf.get("file", ""),
                "source_type": leaf.get("source_type", ""),
                "source_name": leaf.get("source_name", ""),
                "author": leaf.get("author", ""),
                "year": leaf.get("year", ""),
                "chapter": leaf.get("chapter", ""),
                "completed": score >= 80,
            })
            links.append({
                "source": cat_id,
                "target": leaf_id,
                "relation": "contains",
            })

        cat_total = len(cat_leaf_scores)
        cat_mastered = sum(1 for score in cat_leaf_scores if score >= 80)
        cat_average = round(sum(cat_leaf_scores) / cat_total, 1) if cat_total else 0
        cat_status = _status_from_score(int(cat_average))
        category_stats.append({
            "key": cat_key,
            "name": cat_label,
            "total": cat_total,
            "mastered": cat_mastered,
            "to_improve": max(0, cat_total - cat_mastered),
            "average_score": cat_average,
            "percentage": round(cat_mastered / cat_total * 100, 1) if cat_total else 0,
        })
        for node in nodes:
            if node.get("id") == cat_id:
                node["score"] = cat_average
                node["status"] = cat_status
                node["status_label"] = _status_label(cat_status)
                break

    root_average = round(sum(leaf_scores) / len(leaf_scores), 1) if leaf_scores else 0
    root_status = _status_from_score(int(root_average))
    nodes[0]["score"] = root_average
    nodes[0]["status"] = root_status
    nodes[0]["status_label"] = _status_label(root_status)

    total_leaves = tree.get("total_leaves", len(leaf_ids))
    stats = _progress_stats(progress, total_leaves, leaf_ids)

    return {
        "domain": "cnc",
        "domain_name": "数控加工领域",
        "nodes": nodes,
        "links": links,
        "stats": stats,
        "categories": category_stats,
        "legend": [
            {"status": "mastered", "label": "掌握度 >= 80%", "color": "#22C55E"},
            {"status": "learning", "label": "掌握度 60-79%", "color": "#A3E635"},
            {"status": "weak", "label": "掌握度 < 60%", "color": "#FACC15"},
            {"status": "recommended", "label": "建议重点学习", "color": "#D1D5DB"},
        ],
    }


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
    """
    获取知识图谱树状图数据。
    返回适配 ECharts Tree 的结构。
    """
    if not _CATEGORY_LABELS:
        _init_category_labels()
    tree = _build_tree()
    return tree


@router.get("/knowledge-graph/graph")
async def get_knowledge_graph_as_graph():
    """
    获取无个人进度的力导向图数据。
    返回适配 ECharts Graph 的 nodes / links。
    """
    return _build_graph(_normalize_progress({}))


@router.get("/knowledge-graph/files")
async def get_knowledge_files(
    category: Optional[str] = Query(None, description="按分类筛选：theory / practice / standards"),
):
    """
    获取知识库文件列表，支持按分类筛选。
    """
    if not _CATEGORY_LABELS:
        _init_category_labels()

    tree = _build_tree()
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
                    "category": _category_label(cat_key),
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
    标记/取消标记某知识点为"已学习"。
    同时同步进度到数据库。
    """
    user_id = current_user.id
    progress = _load_progress(user_id)
    target_score = req.score
    if target_score is None:
        target_score = 100 if req.completed else 0
    action = "completed" if req.completed else "uncompleted"
    progress = _apply_score_update(
        progress,
        req.node_id,
        target_score,
        source=req.source or "manual",
        action=action,
    )
    _save_progress(user_id, progress)

    # 同步到数据库
    await _sync_progress_to_db(user_id, progress, db)

    # 计算进度百分比
    tree = _build_tree()
    total_leaves = tree.get("total_leaves", 0)
    leaf_ids = _leaf_ids_from_tree(tree)
    stats = _progress_stats(progress, total_leaves, leaf_ids)

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
    # DB 优先：避免删库重建后读到同用户名的旧文件残留
    db_progress = await _load_progress_from_db(user_id, db)
    if db_progress and (db_progress.get("completed_nodes") or db_progress.get("node_scores")):
        progress = db_progress
    else:
        progress = _load_progress(user_id)

    tree = _build_tree()
    total_leaves = tree.get("total_leaves", 0)
    leaf_ids = _leaf_ids_from_tree(tree)
    stats = _progress_stats(progress, total_leaves, leaf_ids)

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
    db_progress = await _load_progress_from_db(user_id, db)
    if db_progress and (db_progress.get("completed_nodes") or db_progress.get("node_scores")):
        progress = db_progress
    else:
        progress = _load_progress(user_id)
    return _build_graph(progress)


@router.get("/knowledge-graph/progress/all")
async def get_all_progress(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    管理员查看所有学员的学习进度。
    优先从数据库读取 kg_progress，降级到文件读取。
    """
    tree = _build_tree()
    total_leaves = tree.get("total_leaves", 0)
    leaf_ids = _leaf_ids_from_tree(tree)

    all_progress = []

    # 从数据库查询所有 learner 账号；未建档账号没有 Learner 记录，按 0 进度展示。
    stmt = (
        select(User.id, User.username, Learner.kg_progress)
        .select_from(User)
        .outerjoin(Learner, Learner.user_id == User.id)
        .where(User.role == "learner")
    )
    result = await db.execute(stmt)
    rows = result.all()

    for uid, username, kg_progress in rows:
        # 优先从 DB 的 kg_progress 读取
        if kg_progress and isinstance(kg_progress, dict):
            kg = _normalize_progress(kg_progress)
        else:
            # 降级到文件（按 user_id 索引）
            kg = _load_progress(uid)

        completed = kg.get("completed_nodes", [])
        stats = _progress_stats(kg, total_leaves, leaf_ids)

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
    获取带当前用户学习进度标记的树状图数据。
    每个叶子节点附加 completed 字段。
    DB 优先（可信源），文件作为降级缓存。
    """
    if not _CATEGORY_LABELS:
        _init_category_labels()

    tree = _build_tree()
    user_id = current_user.id
    db_progress = await _load_progress_from_db(user_id, db)
    if db_progress and (db_progress.get("completed_nodes") or db_progress.get("node_scores")):
        progress = db_progress
    else:
        progress = _load_progress(user_id)
    completed = set(progress.get("completed_nodes", []))
    node_scores = progress.get("node_scores", {})

    def _attach_progress(node: dict) -> None:
        if node.get("is_leaf"):
            score = _clamp_score(node_scores.get(node.get("id"), {}).get("score", 0))
            status = _status_from_score(score)
            node["score"] = score
            node["status"] = status
            node["status_label"] = _status_label(status)
            node["completed"] = node.get("id") in completed
        for child in node.get("children", []):
            _attach_progress(child)

    for child in tree.get("children", []):
        _attach_progress(child)

    return tree


# ── 管理员端：同步单个学员的知识图谱进度到 DB ──

@router.post("/knowledge-graph/progress/sync-all")
async def sync_all_progress_to_db(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    管理员触发：将所有学员的本地进度文件同步到数据库。
    用于数据迁移或修复不一致。
    """
    tree = _build_tree()
    total_leaves = tree.get("total_leaves", 0)
    leaf_ids = _leaf_ids_from_tree(tree)
    synced = 0
    failed = 0

    if _PROGRESS_DIR.exists():
        for f in _PROGRESS_DIR.glob("*.json"):
            stem = f.stem
            try:
                # 文件名格式：user_{user_id}.json
                if not stem.startswith("user_"):
                    logger.warning(f"跳过旧格式进度文件: {f.name}（应为 user_{{id}}.json）")
                    continue
                id_str = stem[5:]
                if not id_str.isdigit():
                    logger.warning(f"跳过非法进度文件: {f.name}")
                    continue
                user_id = int(id_str)

                data = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    progress = _normalize_progress(data)
                    completed = progress.get("completed_nodes", [])
                    stats = _progress_stats(progress, total_leaves, leaf_ids)

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
            except Exception as e:
                logger.warning(f"同步进度失败 {stem}: {e}")
                failed += 1

        if synced > 0:
            await db.flush()

    return {
        "ok": True,
        "synced": synced,
        "failed": failed,
        "message": f"已同步 {synced} 个学员的知识图谱进度到数据库" + (f"，{failed} 个失败" if failed else ""),
    }
