from typing import Any
from datetime import datetime
import time

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
        # 追踪埋点
        self._trace_calls: list = []
        self._trace_agent_name: str = ""

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
        """从知识库检索相关文档，返回带完整来源信息的上下文"""
        if self.kb is False:
            return ""
        try:
            docs = self.kb.search(query, k=k)
            context_parts = []
            for i, doc in enumerate(docs, 1):
                m = doc.metadata
                # 构建来源信息
                source_info = self._build_source_info(m)
                context_parts.append(
                    f"[知识库第{i}条]\n"
                    f"{source_info}\n"
                    f"内容:\n{doc.page_content}"
                )
            return "\n\n".join(context_parts)
        except Exception as e:
            print(f"[警告] 知识库检索失败: {e}")
            return ""

    def _build_source_info(self, metadata: dict) -> str:
        """从 metadata 构建来源描述字符串"""
        parts = []
        source_name = metadata.get("source_name", "")
        author = metadata.get("author", "")
        publisher = metadata.get("publisher", "")
        year = metadata.get("year", "")
        chapter = metadata.get("chapter", "")
        url = metadata.get("url", "")
        source_type = metadata.get("source_type", "文档")

        # 来源类型映射
        type_map = {"book": "📚", "paper": "📄", "standard": "📋", "website": "🔗", "文档": "📖"}
        icon = type_map.get(source_type, "📖")

        if source_name:
            parts.append(f"{icon} 来源：《{source_name}》")
        if author:
            parts.append(f"作者：{author}")
        if publisher:
            parts.append(f"出版社：{publisher}")
        if year:
            parts.append(f"年份：{year}")
        if chapter:
            parts.append(f"章节：{chapter}")
        if url:
            parts.append(f"🔗 链接：{url}")

        # 如果没有元数据，用文件路径
        if not parts:
            file_path = metadata.get("source", "未知来源")
            parts.append(f"📖 来源：{file_path}")

        return " | ".join(parts)

    async def call_llm(self, prompt: str, max_retries: int = 3, label: str = "") -> str:
        """调用 LLM 获取响应，带重试机制和追踪埋点"""
        import asyncio

        # Mock 模式：通过 contextvars 将 label 传递给 MockLLM.ainvoke()
        try:
            from app.mock.llm import _mock_label
            _mock_label.set(label)
        except ImportError:
            pass  # 非 mock 模式，正常跳过

        last_error = None
        start = time.time()
        for attempt in range(max_retries):
            try:
                response = await self.llm.ainvoke(prompt)
                elapsed_ms = round((time.time() - start) * 1000)

                # 追踪埋点：记录 prompt/response/耗时
                self._trace_calls.append({
                    "label": label or f"LLM调用#{attempt+1}",
                    "prompt": prompt,
                    "response": response.content[:8000],
                    "elapsed_ms": elapsed_ms,
                    "timestamp": datetime.now().isoformat(),
                })
                return response.content
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    print(f"[重试] LLM 调用失败 (第{attempt+1}次)，{wait_time}秒后重试: {e}")
                    await asyncio.sleep(wait_time)
        raise RuntimeError(f"LLM 调用失败（已重试{max_retries}次）: {last_error}")

    def collect_trace(self) -> list:
        """收集并清空当前 Agent 的 LLM 调用追踪记录"""
        calls = list(self._trace_calls)
        self._trace_calls = []
        return calls

    async def run(self, **kwargs) -> Any:
        """子类实现的主逻辑"""
        raise NotImplementedError
