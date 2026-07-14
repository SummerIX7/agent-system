from typing import Any
from contextvars import ContextVar
from datetime import datetime
import time

from langchain_core.language_models import BaseChatModel

from app.core.config import get_settings
from app.core.llm import get_llm

# 追踪埋点：用 ContextVar 隔离协程/请求，避免模块级 Agent 单例在并发工作流中互相覆盖 trace。
# ainvoke() 调用会在独立的 asyncio Task 上运行，每个 Task 有自己的 Context 副本，天然隔离。
_trace_calls_var: ContextVar[list | None] = ContextVar("agent_trace_calls", default=None)
_trace_agent_name_var: ContextVar[str] = ContextVar("agent_trace_agent_name", default="")

# LLM 缓存：label 包含以下关键词时自动启用（幂等场景：审核/断言检测等）
_CACHEABLE_LABEL_KEYWORDS = ("审核", "回归验证", "谬误检测", "断言提取", "事实核查")


def _should_use_llm_cache(label: str) -> bool:
    """根据 label 判断是否命中默认可缓存场景"""
    if not label:
        return False
    return any(kw in label for kw in _CACHEABLE_LABEL_KEYWORDS)


class BaseAgent:
    """Agent 基类，提供 LLM 调用、知识库检索、日志记录等基础能力"""

    def __init__(
        self,
        llm: BaseChatModel | None = None,
    ):
        self.llm = llm or get_llm()
        self._kb = None  # 延迟初始化，避免启动时阻塞

    # ── 追踪埋点：属性代理到 ContextVar，保持旧调用点（agent._trace_calls = []）不变 ──
    @property
    def _trace_calls(self) -> list:
        val = _trace_calls_var.get()
        if val is None:
            val = []
            _trace_calls_var.set(val)
        return val

    @_trace_calls.setter
    def _trace_calls(self, value: list | None) -> None:
        _trace_calls_var.set(list(value) if value is not None else [])

    @property
    def _trace_agent_name(self) -> str:
        return _trace_agent_name_var.get()

    @_trace_agent_name.setter
    def _trace_agent_name(self, value: str) -> None:
        _trace_agent_name_var.set(value or "")

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
        type_map = {"book": "", "paper": "", "standard": "", "website": "", "文档": ""}
        icon = type_map.get(source_type, "")

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
            parts.append(f" 链接：{url}")

        # 如果没有元数据，用文件路径
        if not parts:
            file_path = metadata.get("source", "未知来源")
            parts.append(f" 来源：{file_path}")

        return " | ".join(parts)

    async def call_llm(
        self,
        prompt: str,
        max_retries: int = 3,
        label: str = "",
        use_cache: bool | None = None,
    ) -> str:
        """调用 LLM 获取响应，带重试机制、追踪埋点与可选缓存

        参数:
            use_cache:
              - None（默认）：根据 label 自动判断（审核类命中缓存）
              - True：强制启用（同一模型 + 同一 prompt 缓存 1 小时）
              - False：强制禁用
        """
        import asyncio

        # Mock 模式：通过 contextvars 将 label 传递给 MockLLM.ainvoke()
        try:
            from app.mock.llm import _mock_label
            _mock_label.set(label)
        except ImportError:
            pass  # 非 mock 模式，正常跳过

        settings = get_settings()
        # 判定是否使用缓存：mock 模式禁用（会跳过外部调用，缓存无收益且可能污染）
        if use_cache is None:
            use_cache = _should_use_llm_cache(label)
        if use_cache and getattr(settings, "MOCK_MODE", False):
            use_cache = False

        # 拿到模型标识，作为缓存 topic，避免模型切换后错命中
        model_name = (
            getattr(self.llm, "model_name", "")
            or getattr(self.llm, "model", "")
            or ""
        )

        # ── 缓存读 ──
        if use_cache:
            try:
                from app.core.store import get_llm_cache
                cached = get_llm_cache(prompt, topic=str(model_name))
            except Exception as cache_err:
                cached = None
                print(f"[LLM缓存] 读取失败，退回真实调用: {cache_err}")
            if cached is not None:
                self._trace_calls.append({
                    "label": (label or "LLM调用") + " [cache-hit]",
                    "prompt": prompt,
                    "response": cached[:8000],
                    "elapsed_ms": 0,
                    "cache_hit": True,
                    "timestamp": datetime.now().isoformat(),
                })
                return cached

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
                    "cache_hit": False,
                    "timestamp": datetime.now().isoformat(),
                })

                # ── 缓存写 ──
                if use_cache:
                    try:
                        from app.core.store import set_llm_cache
                        set_llm_cache(prompt, response.content, topic=str(model_name))
                    except Exception as cache_err:
                        print(f"[LLM缓存] 写入失败: {cache_err}")

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
        _trace_calls_var.set([])
        return calls

    async def run(self, **kwargs) -> Any:
        """子类实现的主逻辑"""
        raise NotImplementedError
