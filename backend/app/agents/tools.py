"""Agent 可调用工具层（LLM tool-calling）。

只暴露只读 / 纯计算的本地工具，供 Generation / Review / QuestionGenerator 按需调用：
- retrieve_knowledge：知识生成时补充检索（查询改写 / 多跳）。
- fact_check_lookup：审核时核查具体断言。
- machining_calculator：切削参数换算（转速 / 切削速度 / 进给速度），纯函数。
- standard_lookup：国标 / 行业规范条款精确查询（standards 目录本地检索）。
- graph_query：知识图谱节点查询（按关键词返回知识点路径）。

工具内部复用知识库检索器与统一的来源引用格式化；知识库不可用或检索失败时返回提示串，
绝不抛异常打断主流程。
"""

from __future__ import annotations

import logging
import math
import re

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def _search(query: str, k: int) -> str:
    """内部检索：返回带来源引用的上下文文本，失败/为空时返回提示串。"""
    try:
        from app.core.config import get_settings
        if not getattr(get_settings(), "ENABLE_KNOWLEDGE_BASE", False):
            return "[知识库未启用，无法检索]"
        from app.knowledge.retriever import get_retriever
        from app.knowledge.formatting import format_docs
        docs = get_retriever().search(query, k=k)
        if not docs:
            return "[未检索到相关内容]"
        return format_docs(docs)
    except Exception as e:  # noqa: BLE001
        logger.warning("[工具检索] 失败: %s", e)
        return f"[检索失败: {e}]"


@tool
def retrieve_knowledge(query: str, k: int = 5) -> str:
    """检索领域知识库，返回与查询最相关的资料片段（含来源引用）。

    当你需要补充事实、术语定义、标准规程或操作细节时调用；
    可改写查询或分多次检索不同子主题以提升覆盖度。

    Args:
        query: 检索用的中文查询语句，尽量具体。
        k: 返回的资料片段数量，默认 5。
    """
    return _search(query, k)


@tool
def fact_check_lookup(claim: str, k: int = 4) -> str:
    """针对某条具体断言，从知识库检索用于核查的权威资料（含来源引用）。

    当你对待审内容中的某个事实、数值、步骤或概念定义存疑时调用，
    用返回资料判断该断言是否与知识库一致。

    Args:
        claim: 需要核查的单条断言（尽量原文摘录或精炼概括）。
        k: 返回的核查资料片段数量，默认 4。
    """
    return _search(claim, k)


@tool
def machining_calculator(
    operation: str,
    diameter_mm: float = 0,
    cutting_speed_m_min: float = 0,
    spindle_rpm: float = 0,
    feed_per_tooth_mm: float = 0,
    teeth: int = 0,
) -> str:
    """切削参数换算计算器（纯计算，结果精确，不涉及任何外部查询）。

    支持的 operation：
    - "spindle_speed"：由切削速度 vc (m/min) 和刀具直径 D (mm) 求主轴转速 n (r/min)，n = 1000·vc / (π·D)
    - "cutting_speed"：由主轴转速 n (r/min) 和刀具直径 D (mm) 求切削速度 vc (m/min)，vc = π·D·n / 1000
    - "feed_rate"：由每齿进给 fz (mm/z)、齿数 z、主轴转速 n 求进给速度 vf (mm/min)，vf = fz·z·n

    当生成内容或待审内容涉及具体切削参数数值时，调用本工具核实计算是否正确，不要口算。

    Args:
        operation: 计算类型，"spindle_speed" / "cutting_speed" / "feed_rate"。
        diameter_mm: 刀具或工件直径 D，单位 mm。
        cutting_speed_m_min: 切削速度 vc，单位 m/min。
        spindle_rpm: 主轴转速 n，单位 r/min。
        feed_per_tooth_mm: 每齿进给量 fz，单位 mm/z。
        teeth: 刀具齿数 z。
    """
    if operation == "spindle_speed":
        if diameter_mm <= 0 or cutting_speed_m_min <= 0:
            return "[参数错误] spindle_speed 需要 diameter_mm > 0 且 cutting_speed_m_min > 0"
        n = 1000 * cutting_speed_m_min / (math.pi * diameter_mm)
        return (f"n = 1000·vc / (π·D) = 1000×{cutting_speed_m_min} / (π×{diameter_mm}) "
                f"≈ {n:.0f} r/min")
    if operation == "cutting_speed":
        if diameter_mm <= 0 or spindle_rpm <= 0:
            return "[参数错误] cutting_speed 需要 diameter_mm > 0 且 spindle_rpm > 0"
        vc = math.pi * diameter_mm * spindle_rpm / 1000
        return (f"vc = π·D·n / 1000 = π×{diameter_mm}×{spindle_rpm} / 1000 "
                f"≈ {vc:.1f} m/min")
    if operation == "feed_rate":
        if feed_per_tooth_mm <= 0 or teeth <= 0 or spindle_rpm <= 0:
            return "[参数错误] feed_rate 需要 feed_per_tooth_mm、teeth、spindle_rpm 均 > 0"
        vf = feed_per_tooth_mm * teeth * spindle_rpm
        return (f"vf = fz·z·n = {feed_per_tooth_mm}×{teeth}×{spindle_rpm:.0f} "
                f"= {vf:.0f} mm/min")
    return f"[不支持的计算类型: {operation}]，可选：spindle_speed / cutting_speed / feed_rate"


def _search_standards(query: str, max_hits: int = 5, excerpt_chars: int = 220) -> str:
    """在知识库 standards 目录内做本地条款检索（关键词匹配，不走向量）。"""
    try:
        from app.services.kg_tree import KNOWLEDGE_BASE_DIR
        standards_dir = KNOWLEDGE_BASE_DIR / "standards"
        if not standards_dir.exists():
            return "[标准规范目录不存在]"
        tokens = [t for t in re.split(r"[\s,，、/]+", query.strip()) if len(t) >= 2]
        if not tokens:
            return "[查询关键词过短，请提供更具体的条款关键词]"
        hits: list[str] = []
        for md in sorted(standards_dir.glob("*.md")):
            try:
                text = md.read_text(encoding="utf-8")
            except Exception:  # noqa: BLE001
                continue
            for para in re.split(r"\n\s*\n", text):
                if any(tok in para for tok in tokens):
                    excerpt = re.sub(r"\s+", " ", para).strip()[:excerpt_chars]
                    hits.append(f"来源：《{md.stem}》\n{excerpt}")
                    break  # 每个文件取首条命中，保证覆盖面
            if len(hits) >= max_hits:
                break
        if not hits:
            return "[未在标准规范库中检索到相关条款]"
        return "\n\n".join(hits)
    except Exception as e:  # noqa: BLE001
        logger.warning("[标准查询] 失败: %s", e)
        return f"[标准查询失败: {e}]"


@tool
def standard_lookup(query: str) -> str:
    """查询国标 / ISO / 行业规范的具体条款（如 G 代码标准、安全规程、检验规范）。

    当内容涉及"标准规定""规范要求""国标 GB""ISO"等表述时调用，
    用返回的条款原文核实引用是否准确，禁止凭印象引用标准条款。

    Args:
        query: 条款关键词（如 "G43 刀具长度补偿"、"开机安全检查"）。
    """
    return _search_standards(query)


def _walk_tree(node: dict, path: list[str], keyword: str, out: list[str], limit: int) -> None:
    name = str(node.get("name", ""))
    cur = path + ([name] if name else [])
    if keyword and keyword in name and len(out) < limit:
        out.append(" > ".join(cur))
    for child in node.get("children", []) or []:
        if len(out) >= limit:
            return
        _walk_tree(child, cur, keyword, out, limit)


@tool
def graph_query(keyword: str) -> str:
    """查询领域知识图谱：按关键词查找知识点在体系中的位置（分类 > 子类 > 知识点路径）。

    当你需要确认某知识点与其他知识点的层级关系、或查找相关知识主题时调用。

    Args:
        keyword: 知识点关键词（如 "圆弧插补"、"刀具补偿"）。
    """
    try:
        from app.services.kg_tree import build_tree, init_category_labels, CATEGORY_LABELS
        if not CATEGORY_LABELS:
            init_category_labels()
        tree = build_tree()
        matches: list[str] = []
        _walk_tree(tree, [], keyword.strip(), matches, limit=8)
        if not matches:
            return f"[知识图谱中未找到与「{keyword}」相关的节点]"
        return "知识图谱匹配节点：\n" + "\n".join(f"- {m}" for m in matches)
    except Exception as e:  # noqa: BLE001
        logger.warning("[图谱查询] 失败: %s", e)
        return f"[图谱查询失败: {e}]"


# 各 Agent 的工具集合
GENERATION_TOOLS = [retrieve_knowledge, machining_calculator, standard_lookup, graph_query]
REVIEW_TOOLS = [fact_check_lookup, standard_lookup, machining_calculator]
QUESTION_TOOLS = [fact_check_lookup, machining_calculator, standard_lookup]
