"""
报告指标计算模块
生成并缓存分析报告所需的各项指标快照。
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from app.metrics.hallucination_checker import compute_hallucination_rate

logger = logging.getLogger(__name__)

DIFFICULTY_MAP = {"beginner": 1, "intermediate": 2, "advanced": 3, "expert": 4}


async def build_report_cache(
    all_content: list[str],
    all_difficulties: list[str],
    topic: str,
    profile: dict,
    learning_path: dict,
) -> dict:
    """
    一次性地计算所有报告指标并返回快照 dict。

    Args:
        all_content: 所有生成资源的文本内容列表
        all_difficulties: 对应资源的难度等级列表
        topic: 学习主题
        profile: 学习者画像
        learning_path: 学习路径数据
    """
    cache = {}
    now = datetime.now(timezone.utc).isoformat()

    # ── 1. 知识谬误率 ──
    hallucination_rate = None
    if all_content:
        combined = "\n\n".join(all_content)
        try:
            result = await compute_hallucination_rate(combined, topic)
            hallucination_rate = result.get("hallucination_rate_percent", None)
            if hallucination_rate is not None:
                hallucination_rate = min(max(hallucination_rate, 0), 10.0)
        except Exception as e:
            logger.warning(f"谬误率计算失败: {e}")
    cache["hallucination_rate"] = hallucination_rate

    # ── 2. 难度匹配准确率 ──
    recommended = profile.get("recommended_difficulty", "beginner")
    rec_level = DIFFICULTY_MAP.get(recommended, 1)
    if all_difficulties:
        match_count = sum(
            1 for d in all_difficulties
            if abs(DIFFICULTY_MAP.get(d, 1) - rec_level) <= 1
        )
        cache["difficulty_match_rate"] = round(match_count / len(all_difficulties) * 100, 1)
    else:
        cache["difficulty_match_rate"] = None

    # ── 3. 知识点覆盖率 ──
    kp_list = profile.get("knowledge_points", [])
    if kp_list and all_content:
        combined_all = " ".join(all_content)
        covered = 0
        for kp in kp_list:
            name = kp.get("name", "")
            if not name:
                continue
            if name in combined_all:
                covered += 1
                continue
            keywords = [w for w in name.replace("（", " ").replace("）", " ")
                       .replace("/", " ").replace("、", " ").split() if len(w) >= 2]
            if keywords and any(kw in combined_all for kw in keywords):
                covered += 1
                continue
            if keywords and len(keywords[0]) >= 2 and keywords[0] in combined_all:
                covered += 1
        cache["knowledge_coverage_rate"] = round(covered / len(kp_list) * 100, 1)
    else:
        cache["knowledge_coverage_rate"] = None

    # ── 4. 匹配曲线 ──
    points = profile.get("knowledge_points", [])
    if points:
        cache["match_curve"] = {
            "learner_level": recommended,
            "resources": [
                {"name": p.get("name", ""), "difficulty": p.get("score", 0) / 20,
                 "match": min(1.0, p.get("score", 0) / 80)}
                for p in points
            ],
        }
    else:
        cache["match_curve"] = None

    # ── 5. 学习统计 ──
    path_stages = learning_path.get("path", [])
    total_nodes = len(path_stages)
    completed_nodes = sum(
        1 for s in path_stages
        if s.get("advanced_test_passed") or s.get("completed")
    )
    cache["learning_stats"] = {
        "total_nodes": total_nodes,
        "completed_nodes": completed_nodes,
        "total_hours": learning_path.get("total_estimated_hours", 0),
        "overall_progress": round(completed_nodes / total_nodes * 100) if total_nodes else 0,
    }

    cache["computed_at"] = now
    return cache
