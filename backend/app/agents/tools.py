"""Agent 可调用工具层（LLM tool-calling）。

只暴露只读、本地的知识库检索工具，供 Generation / Review 两个 Agent 按需调用：
- retrieve_knowledge：知识生成时补充检索（查询改写 / 多跳）。
- fact_check_lookup：审核时核查具体断言。

工具内部复用知识库检索器与统一的来源引用格式化；知识库不可用或检索失败时返回提示串，
绝不抛异常打断主流程。
"""

from __future__ import annotations

import logging

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


# 各 Agent 的工具集合
GENERATION_TOOLS = [retrieve_knowledge]
REVIEW_TOOLS = [fact_check_lookup]
