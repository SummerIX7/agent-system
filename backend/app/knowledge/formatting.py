"""知识库检索结果的来源引用格式化。

抽取自 BaseAgent，供 Agent 检索与工具层（tools.py）共用，避免重复实现来源引用逻辑。
"""

from __future__ import annotations


def build_source_info(metadata: dict) -> str:
    """从 metadata 构建来源描述字符串"""
    metadata = metadata or {}
    parts = []
    source_name = metadata.get("source_name", "")
    author = metadata.get("author", "")
    publisher = metadata.get("publisher", "")
    year = metadata.get("year", "")
    chapter = metadata.get("chapter", "")
    url = metadata.get("url", "")

    if source_name:
        parts.append(f"来源：《{source_name}》")
    if author:
        parts.append(f"作者：{author}")
    if publisher:
        parts.append(f"出版社：{publisher}")
    if year:
        parts.append(f"年份：{year}")
    if chapter:
        parts.append(f"章节：{chapter}")
    if url:
        parts.append(f"链接：{url}")

    # 如果没有元数据，用文件路径
    if not parts:
        file_path = metadata.get("source", "未知来源")
        parts.append(f"来源：{file_path}")

    return " | ".join(parts)


def format_docs(docs: list) -> str:
    """把检索到的 Document 列表格式化为带来源引用的上下文文本"""
    context_parts = []
    for i, doc in enumerate(docs, 1):
        source_info = build_source_info(getattr(doc, "metadata", {}) or {})
        context_parts.append(
            f"[知识库第{i}条]\n"
            f"{source_info}\n"
            f"内容:\n{doc.page_content}"
        )
    return "\n\n".join(context_parts)
