"""知识图谱 —— 树/叶节点解析与主题匹配。

从磁盘的 ``cnc_domain`` 目录结构派生：
- 树形数据（``build_tree``）
- 叶子节点索引（``collect_leaf_index``、``leaf_ids_from_tree``）
- 学习路径主题 → 叶子 ID 的模糊匹配（``match_leaf_id``）
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.core.config import get_settings

# ── 路径配置 ──
_BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = _BACKEND_DIR.parent


def _resolve_kb_dir() -> Path:
    """从 .env 的 KNOWLEDGE_BASE_DIRS 解析知识库目录，避免硬编码本机路径。"""
    first_dir = get_settings().KNOWLEDGE_BASE_DIRS.split(",")[0].strip()
    path = Path(first_dir)
    if not path.is_absolute():
        path = _BACKEND_DIR / path
    return path.resolve()


KNOWLEDGE_BASE_DIR = _resolve_kb_dir()
PROGRESS_DIR = (PROJECT_ROOT / "data" / "progress").resolve()

# ── 分类中文标签映射 ──
CATEGORY_LABELS: dict[str, str] = {}


def init_category_labels() -> None:
    """根据实际子文件夹名动态生成标签映射（幂等）。"""
    predefined = {
        "theory": "理论基础",
        "practice": "实践技能",
        "standards": "标准规范",
    }
    if KNOWLEDGE_BASE_DIR.exists():
        for d in KNOWLEDGE_BASE_DIR.iterdir():
            if d.is_dir():
                CATEGORY_LABELS[d.name] = predefined.get(d.name, d.name)


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """解析 Markdown 文件的 YAML 前置元数据。"""
    metadata: dict = {}
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


def node_id_from_path(rel_path: str) -> str:
    """基于相对路径生成唯一节点 ID"""
    return hashlib.md5(rel_path.encode("utf-8")).hexdigest()[:12]


def category_label(cat: str) -> str:
    """分类英文 → 中文标签"""
    return CATEGORY_LABELS.get(cat, cat)


def build_tree() -> dict:
    """
    从 cnc_domain 目录结构构建树形数据。
    根节点: 数控加工知识体系
    一级节点: 子文件夹（theory / practice / standards）
    二级节点（叶子）: Markdown 文件
    """
    if not KNOWLEDGE_BASE_DIR.exists():
        return {"name": "数控加工知识体系", "children": []}

    if not CATEGORY_LABELS:
        init_category_labels()

    root = {
        "name": "数控加工知识体系",
        "id": "root",
        "children": [],
    }

    subdirs = sorted([d for d in KNOWLEDGE_BASE_DIR.iterdir() if d.is_dir()],
                     key=lambda d: d.name)

    for subdir in subdirs:
        category_key = subdir.name
        category_name = category_label(category_key)
        cat_id = node_id_from_path(category_key)

        cat_node = {
            "name": category_name,
            "id": cat_id,
            "category": category_key,
            "children": [],
        }

        md_files = sorted(subdir.glob("*.md"), key=lambda f: f.stem)

        for md_file in md_files:
            rel_path = str(md_file.relative_to(KNOWLEDGE_BASE_DIR))
            file_id = node_id_from_path(rel_path)

            try:
                content = md_file.read_text(encoding="utf-8")
                metadata, _ = _parse_frontmatter(content)
            except Exception:  # noqa: BLE001
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

    leaf_count = sum(
        sum(1 for c2 in c1["children"] if c2.get("is_leaf"))
        for c1 in root["children"]
    )
    root["total_leaves"] = leaf_count

    return root


def collect_leaf_index() -> dict[str, str]:
    """收集所有叶子节点：name → id 的索引。"""
    if not CATEGORY_LABELS:
        init_category_labels()
    tree = build_tree()
    leaf_nodes: dict[str, str] = {}

    def _collect(node: dict):
        if node.get("is_leaf"):
            leaf_nodes[node["name"]] = node["id"]
        for child in node.get("children", []):
            _collect(child)

    for child in tree.get("children", []):
        _collect(child)
    return leaf_nodes


def leaf_ids_from_tree(tree: dict) -> set[str]:
    """遍历树，收集所有叶子节点 ID。"""
    ids: set[str] = set()

    def _walk(node: dict) -> None:
        if node.get("is_leaf") and node.get("id"):
            ids.add(node["id"])
        for child in node.get("children", []):
            _walk(child)

    _walk(tree)
    return ids


def match_leaf_id(item_name: str, leaf_nodes: dict[str, str]) -> str | None:
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
