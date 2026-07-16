"""知识图谱 —— 力导向图数据构造。

将 ``kg_tree.build_tree()`` 输出的树形结构展开为 ECharts Graph 所需的
``nodes`` / ``links``，并携带用户掌握度、分类统计与图例。
"""

from __future__ import annotations

from app.services.kg_progress import (
    clamp_score,
    normalize_progress,
    progress_stats,
    status_from_score,
    status_label,
)
from app.services.kg_tree import (
    CATEGORY_LABELS,
    build_tree,
    category_label,
    init_category_labels,
)


def build_graph(progress: dict | None = None) -> dict:
    """
    构建力导向图数据。
    nodes / links 适配 ECharts graph；叶子节点附带 score/status。
    """
    if not CATEGORY_LABELS:
        init_category_labels()

    tree = build_tree()
    progress = normalize_progress(progress or {})
    node_scores = progress.get("node_scores", {})

    nodes: list[dict] = []
    links: list[dict] = []
    category_stats: list[dict] = []
    leaf_ids: set[str] = set()
    leaf_scores: list[int] = []

    def _node_score(node_id: str) -> int:
        return clamp_score(node_scores.get(node_id, {}).get("score", 0))

    root_id = tree.get("id", "root")
    nodes.append({
        "id": root_id,
        "name": tree.get("name", "数控加工知识体系"),
        "type": "root",
        "category": "root",
        "category_label": "知识体系",
        "score": 0,
        "status": "recommended",
        "status_label": status_label("recommended"),
        "is_leaf": False,
    })

    for cat_node in tree.get("children", []):
        cat_id = cat_node.get("id")
        cat_key = cat_node.get("category", "")
        cat_label = cat_node.get("name", category_label(cat_key))
        cat_leaf_scores: list[int] = []

        nodes.append({
            "id": cat_id,
            "name": cat_label,
            "type": "category",
            "category": cat_key,
            "category_label": cat_label,
            "score": 0,
            "status": "recommended",
            "status_label": status_label("recommended"),
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
            status = status_from_score(score)
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
                "status_label": status_label(status),
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
        cat_status = status_from_score(int(cat_average))
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
                node["status_label"] = status_label(cat_status)
                break

    root_average = round(sum(leaf_scores) / len(leaf_scores), 1) if leaf_scores else 0
    root_status = status_from_score(int(root_average))
    nodes[0]["score"] = root_average
    nodes[0]["status"] = root_status
    nodes[0]["status_label"] = status_label(root_status)

    total_leaves = tree.get("total_leaves", len(leaf_ids))
    stats = progress_stats(progress, total_leaves, leaf_ids)

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
