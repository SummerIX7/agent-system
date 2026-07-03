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
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_admin
from app.models.database import get_db
from app.models.learner import Learner
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["知识图谱"])

# ── 路径配置 ──
_KNOWLEDGE_BASE_DIR = Path(r"D:\agent-system\agent-system\knowledge-base\cnc_domain")
_PROGRESS_DIR = Path(r"D:\agent-system\agent-system\data\progress")

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


def auto_mark_completed(username: str, knowledge_items: list[str]) -> dict:
    """
    根据分析报告涉及的知识点，自动标记对应知识图谱节点为已学习。

    Args:
        username: 用户名
        knowledge_items: 知识点名称列表（从分析报告或 learner profile 中提取）

    Returns:
        dict: { marked_count, total_provided, ... }
    """
    if not _CATEGORY_LABELS:
        _init_category_labels()

    tree = _build_tree()
    progress = _load_progress(username)
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
    _save_progress(username, progress)

    total_leaves = tree.get("total_leaves", 0)
    percentage = round(len(completed) / total_leaves * 100, 1) if total_leaves > 0 else 0

    logger.info(
        f"[知识图谱自动标记] 用户={username}, "
        f"提供知识点={len(knowledge_items)}, 匹配成功={marked_count}, "
        f"总进度={len(completed)}/{total_leaves} ({percentage}%)"
    )

    return {
        "username": username,
        "marked_count": marked_count,
        "total_provided": len(knowledge_items),
        "completed_nodes": sorted(completed),
        "total": total_leaves,
        "percentage": percentage,
    }


# ── 进度文件管理（文件作为持久化备份，DB 作为主存储）──

def _progress_file_path(username: str) -> Path:
    """获取用户进度文件路径"""
    _PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
    # 安全处理用户名，避免路径遍历
    safe_name = "".join(c for c in username if c.isalnum() or c in "_-")
    if not safe_name:
        safe_name = "anonymous"
    return _PROGRESS_DIR / f"{safe_name}.json"


def _load_progress(username: str) -> dict:
    """加载用户学习进度，返回 {completed_nodes: [...], history: [...]}"""
    file_path = _progress_file_path(username)
    if file_path.exists():
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                completed = data.get("completed_nodes", [])
                history = data.get("history", [])
                # 如果 completed_nodes 为空但 history 有记录，从 history 重建
                if not completed and history:
                    completed_set = set()
                    for entry in history:
                        nid = entry.get("node_id", "")
                        action = entry.get("action", "")
                        if nid:
                            if action in ("completed", "auto_completed"):
                                completed_set.add(nid)
                            elif action == "uncompleted":
                                completed_set.discard(nid)
                    completed = sorted(completed_set)
                return {
                    "completed_nodes": completed,
                    "history": history,
                }
        except Exception:
            logger.warning(f"进度文件损坏，重新创建: {file_path}")
    return {"completed_nodes": [], "history": []}


def _save_progress(username: str, progress: dict) -> None:
    """保存用户学习进度到文件"""
    file_path = _progress_file_path(username)
    file_path.write_text(
        json.dumps(progress, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


async def _sync_progress_to_db(username: str, progress: dict, db: AsyncSession) -> None:
    """将知识图谱进度同步到数据库 learners.kg_progress"""
    tree = _build_tree()
    total_leaves = tree.get("total_leaves", 0)
    completed = progress.get("completed_nodes", [])
    percentage = round(len(completed) / total_leaves * 100, 1) if total_leaves > 0 else 0

    kg_data = {
        "completed_nodes": completed,
        "history": progress.get("history", []),
        "percentage": percentage,
        "total": total_leaves,
    }

    try:
        # 通过 username 查找 learner
        stmt = select(Learner).join(User, Learner.user_id == User.id).where(User.username == username)
        result = await db.execute(stmt)
        learner = result.scalar_one_or_none()
        if learner:
            learner.kg_progress = kg_data
            await db.flush()
            logger.info(f"[KG进度同步到DB] 用户={username}, 进度={percentage}%")
    except Exception as e:
        logger.warning(f"[KG进度同步到DB失败] 用户={username}: {e}")


async def _load_progress_from_db(username: str, db: AsyncSession) -> dict | None:
    """从数据库加载知识图谱进度"""
    try:
        stmt = select(Learner).join(User, Learner.user_id == User.id).where(User.username == username)
        result = await db.execute(stmt)
        learner = result.scalar_one_or_none()
        if learner and learner.kg_progress and isinstance(learner.kg_progress, dict):
            kg = learner.kg_progress
            return {
                "completed_nodes": kg.get("completed_nodes", []),
                "history": kg.get("history", []),
            }
    except Exception as e:
        logger.warning(f"[KG进度从DB加载失败] 用户={username}: {e}")
    return None


def build_kg_progress_for_learner(username: str) -> dict:
    """
    构建可写入 learner.kg_progress 的知识图谱进度字典。
    纯同步函数，不依赖 DB session，可安全地在任何上下文中调用。
    """
    tree = _build_tree()
    total_leaves = tree.get("total_leaves", 0)
    progress = _load_progress(username)
    completed = progress.get("completed_nodes", [])
    pct = round(len(completed) / total_leaves * 100, 1) if total_leaves > 0 else 0
    return {
        "completed_nodes": completed,
        "history": progress.get("history", []),
        "percentage": pct,
        "total": total_leaves,
    }


def _get_or_init_progress(username: str, db: AsyncSession | None = None) -> dict:
    """获取用户进度：优先从文件读取，DB 作为补充"""
    return _load_progress(username)


# ── 请求模型 ──

class ProgressRequest(BaseModel):
    node_id: str
    completed: bool


class ProgressResponse(BaseModel):
    username: str
    completed_nodes: list[str]
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
    username = current_user.username
    progress = _load_progress(username)
    completed = progress["completed_nodes"]

    import datetime
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if req.completed:
        if req.node_id not in completed:
            completed.append(req.node_id)
            progress["history"].append({
                "node_id": req.node_id,
                "action": "completed",
                "timestamp": now,
            })
    else:
        if req.node_id in completed:
            completed.remove(req.node_id)
            progress["history"].append({
                "node_id": req.node_id,
                "action": "uncompleted",
                "timestamp": now,
            })

    progress["completed_nodes"] = sorted(completed)
    _save_progress(username, progress)

    # 同步到数据库
    await _sync_progress_to_db(username, progress, db)

    # 计算进度百分比
    tree = _build_tree()
    total_leaves = tree.get("total_leaves", 0)
    percentage = round(len(completed) / total_leaves * 100, 1) if total_leaves > 0 else 0

    return {
        "username": username,
        "completed_nodes": completed,
        "total": total_leaves,
        "percentage": percentage,
    }


@router.get("/knowledge-graph/progress")
async def get_progress(
    current_user: User = Depends(get_current_user),
):
    """
    获取当前用户的学习进度。
    """
    username = current_user.username
    progress = _load_progress(username)

    tree = _build_tree()
    total_leaves = tree.get("total_leaves", 0)
    completed = progress["completed_nodes"]
    percentage = round(len(completed) / total_leaves * 100, 1) if total_leaves > 0 else 0

    return {
        "username": username,
        "completed_nodes": completed,
        "total": total_leaves,
        "percentage": percentage,
    }


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

    all_progress = []

    # 从数据库查询所有学员
    stmt = select(Learner, User.username).join(User, Learner.user_id == User.id).where(User.role == "learner")
    result = await db.execute(stmt)
    rows = result.all()

    processed_usernames = set()

    for learner, username in rows:
        processed_usernames.add(username)

        # 优先从 DB 的 kg_progress 读取
        if learner.kg_progress and isinstance(learner.kg_progress, dict):
            kg = learner.kg_progress
            completed = kg.get("completed_nodes", [])
            pct = kg.get("percentage", 0)
            if not pct and total_leaves > 0:
                pct = round(len(completed) / total_leaves * 100, 1)
        else:
            # 降级到文件
            file_progress = _load_progress(username)
            completed = file_progress.get("completed_nodes", [])
            pct = round(len(completed) / total_leaves * 100, 1) if total_leaves > 0 else 0

        all_progress.append({
            "username": username,
            "completed_nodes": completed,
            "completed_count": len(completed),
            "total": total_leaves,
            "percentage": pct,
        })

    # 补充：文件中有但数据库中可能已删除的用户
    if _PROGRESS_DIR.exists():
        for f in sorted(_PROGRESS_DIR.glob("*.json")):
            f_username = f.stem
            if f_username in processed_usernames:
                continue
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                completed = data.get("completed_nodes", []) if isinstance(data, dict) else []
                pct = round(len(completed) / total_leaves * 100, 1) if total_leaves > 0 else 0
                all_progress.append({
                    "username": f_username,
                    "completed_nodes": completed,
                    "completed_count": len(completed),
                    "total": total_leaves,
                    "percentage": pct,
                })
            except Exception as e:
                logger.warning(f"读取进度文件失败 {f}: {e}")

    return {
        "total_learners": len(all_progress),
        "total_knowledge_points": total_leaves,
        "learners": all_progress,
    }


@router.get("/knowledge-graph/progress/tree")
async def get_tree_with_progress(
    current_user: User = Depends(get_current_user),
):
    """
    获取带当前用户学习进度标记的树状图数据。
    每个叶子节点附加 completed 字段。
    """
    if not _CATEGORY_LABELS:
        _init_category_labels()

    tree = _build_tree()
    progress = _load_progress(current_user.username)
    completed = set(progress["completed_nodes"])

    def _attach_progress(node: dict) -> None:
        if node.get("is_leaf"):
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
    synced = 0
    failed = 0

    if _PROGRESS_DIR.exists():
        for f in _PROGRESS_DIR.glob("*.json"):
            username = f.stem
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    completed = data.get("completed_nodes", [])
                    history = data.get("history", [])
                    # 如果 completed_nodes 为空但 history 有记录，从 history 重建
                    if not completed and history:
                        completed_set = set()
                        for entry in history:
                            nid = entry.get("node_id", "")
                            action = entry.get("action", "")
                            if nid:
                                if action in ("completed", "auto_completed"):
                                    completed_set.add(nid)
                                elif action == "uncompleted":
                                    completed_set.discard(nid)
                        completed = sorted(completed_set)
                    pct = round(len(completed) / total_leaves * 100, 1) if total_leaves > 0 else 0

                    kg_data = {
                        "completed_nodes": completed,
                        "history": history,
                        "percentage": pct,
                        "total": total_leaves,
                    }

                    stmt = select(Learner).join(User, Learner.user_id == User.id).where(User.username == username)
                    r = await db.execute(stmt)
                    learner = r.scalar_one_or_none()
                    if learner:
                        learner.kg_progress = kg_data
                        synced += 1
                    else:
                        failed += 1
            except Exception as e:
                logger.warning(f"同步进度失败 {username}: {e}")
                failed += 1

        if synced > 0:
            await db.flush()

    return {
        "ok": True,
        "synced": synced,
        "failed": failed,
        "message": f"已同步 {synced} 个学员的知识图谱进度到数据库" + (f"，{failed} 个失败" if failed else ""),
    }
