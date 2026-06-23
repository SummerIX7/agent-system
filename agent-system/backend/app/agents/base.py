from typing import Any

from langchain_core.language_models import BaseChatModel

from app.core.config import get_settings
from app.core.llm import get_llm


class BaseAgent:
    """Agent 基类，提供 LLM 调用、知识库检索、日志记录等基础能力"""

    def __init__(
        self,
        llm: BaseChatModel | None = None,
    ):
        self.llm = llm or get_llm()
        self._kb = None  # 延迟初始化，避免启动时阻塞

    @property
    def kb(self):
        """延迟加载知识库检索器（需要 ENABLE_KNOWLEDGE_BASE=True）"""
        settings = get_settings()
        if not getattr(settings, 'ENABLE_KNOWLEDGE_BASE', False):
            return False  # 知识库未启用
        if self._kb is None:
            try:
                from app.knowledge.retriever import get_retriever
                self._kb = get_retriever()
            except Exception as e:
                print(f"[警告] 知识库不可用: {e}")
                self._kb = False
        return self._kb

    def retrieve_context(self, query: str, k: int = 5) -> str:
        """从知识库检索相关文档，不可用时返回空字符串"""
        if self.kb is False:
            return ""
        try:
            docs = self.kb.search(query, k=k)
            context_parts = []
            for i, doc in enumerate(docs, 1):
                source = doc.metadata.get("source", "未知来源")
                context_parts.append(f"[知识库第{i}条] 来源: {source}\n{doc.page_content}")
            return "\n\n".join(context_parts)
        except Exception as e:
            print(f"[警告] 知识库检索失败: {e}")
            return ""

    async def call_llm(self, prompt: str) -> str:
        """调用 LLM 获取响应"""
        response = await self.llm.ainvoke(prompt)
        return response.content

    async def run(self, **kwargs) -> Any:
        """子类实现的主逻辑"""
        raise NotImplementedError
