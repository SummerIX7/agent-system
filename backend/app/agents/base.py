from typing import Any
from contextvars import ContextVar
from datetime import datetime
import logging
import time

from langchain_core.language_models import BaseChatModel

from app.core.config import get_settings
from app.core.llm import get_llm

logger = logging.getLogger(__name__)

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
                logger.warning("知识库不可用: %s", e)
                self._kb = False
        return self._kb

    def retrieve_context(self, query: str, k: int = 5) -> str:
        """从知识库检索相关文档，返回带完整来源信息的上下文"""
        if self.kb is False:
            return ""
        try:
            from app.knowledge.formatting import format_docs
            docs = self.kb.search(query, k=k)
            return format_docs(docs)
        except Exception as e:
            logger.warning("知识库检索失败: %s", e)
            return ""

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
                logger.warning("[LLM缓存] 读取失败，退回真实调用: %s", cache_err)
            if cached is not None:
                self._trace_calls.append({
                    "label": (label or "LLM调用") + " [cache-hit]",
                    "prompt": prompt,
                    "response": cached[:8000],
                    "elapsed_ms": 0,
                    "cache_hit": True,
                    "timestamp": datetime.now().isoformat(),
                })
                # 监控指标（失败不影响主流程）
                try:
                    from app.api.health import record_llm_call
                    record_llm_call(cache_hit=True)
                except Exception:  # noqa: BLE001
                    pass
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
                        logger.warning("[LLM缓存] 写入失败: %s", cache_err)

                # 监控指标（失败不影响主流程）
                try:
                    from app.api.health import record_llm_call
                    record_llm_call(cache_hit=False)
                except Exception:  # noqa: BLE001
                    pass

                return response.content
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    logger.warning(
                        "[重试] LLM 调用失败 (第%d次)，%d秒后重试: %s",
                        attempt + 1, wait_time, e,
                    )
                    await asyncio.sleep(wait_time)
        raise RuntimeError(f"LLM 调用失败（已重试{max_retries}次）: {last_error}")

    async def call_llm_with_tools(
        self,
        prompt: str,
        tools: list,
        label: str = "",
        max_rounds: int | None = None,
    ) -> str:
        """带工具调用（tool-calling）的 LLM 调用，返回最终文本。

        - MOCK_MODE 或 USE_AGENT_TOOLS 关闭时，直接回落到纯 prompt 的 call_llm（行为与现状一致）。
        - 否则绑定工具并跑受限循环：模型请求工具 → 本地执行 → 回传结果 → 直到模型给出终答或达轮数上限。
        - 每轮响应与工具执行写入 trace 埋点，便于观测。
        """
        settings = get_settings()
        use_tools = bool(tools) and getattr(settings, "USE_AGENT_TOOLS", False) \
            and not getattr(settings, "MOCK_MODE", False)

        # 回落：与纯 prompt 流程完全等价
        if not use_tools:
            return await self.call_llm(prompt, label=label)

        from langchain_core.messages import HumanMessage, ToolMessage

        if max_rounds is None:
            max_rounds = getattr(settings, "AGENT_TOOL_MAX_ROUNDS", 3)

        tool_map = {t.name: t for t in tools}
        try:
            llm_with_tools = self.llm.bind_tools(tools)
        except Exception as e:  # noqa: BLE001 — 绑定失败则退回纯 prompt，保证不打断主流程
            logger.warning("[工具调用] bind_tools 失败，回落纯 prompt: %s", e)
            return await self.call_llm(prompt, label=label)

        messages = [HumanMessage(content=prompt)]
        last_content = ""

        for round_idx in range(max_rounds + 1):
            start = time.time()
            response = await llm_with_tools.ainvoke(messages)
            elapsed_ms = round((time.time() - start) * 1000)
            messages.append(response)

            tool_calls = getattr(response, "tool_calls", None) or []
            self._trace_calls.append({
                "label": (label or "工具调用") + f"#{round_idx + 1}",
                "prompt": prompt if round_idx == 0 else "[后续工具轮]",
                "response": (response.content or "")[:8000],
                "tool_calls": [
                    {"name": tc.get("name"), "args": tc.get("args")} for tc in tool_calls
                ],
                "elapsed_ms": elapsed_ms,
                "cache_hit": False,
                "timestamp": datetime.now().isoformat(),
            })
            try:
                from app.api.health import record_llm_call
                record_llm_call(cache_hit=False)
            except Exception:  # noqa: BLE001
                pass

            last_content = response.content or last_content

            # 无工具请求 → 终答
            if not tool_calls:
                return response.content or ""

            # 达到轮数上限：不再执行工具，逼模型基于已有信息给结论
            if round_idx >= max_rounds:
                break

            # 执行工具并回传结果
            for tc in tool_calls:
                name = tc.get("name", "")
                args = tc.get("args", {}) or {}
                tool = tool_map.get(name)
                if tool is None:
                    result = f"[工具 {name} 不存在]"
                else:
                    try:
                        result = tool.invoke(args)
                    except Exception as e:  # noqa: BLE001
                        result = f"[工具 {name} 执行失败: {e}]"
                messages.append(ToolMessage(
                    content=str(result),
                    tool_call_id=tc.get("id", name),
                ))

        # 轮数耗尽仍未终答：再要一次纯文本结论
        try:
            final = await self.llm.ainvoke(messages)
            return final.content or last_content
        except Exception:  # noqa: BLE001
            return last_content

    def collect_trace(self) -> list:
        """收集并清空当前 Agent 的 LLM 调用追踪记录"""
        calls = list(self._trace_calls)
        _trace_calls_var.set([])
        return calls

    async def run(self, **kwargs) -> Any:
        """子类实现的主逻辑"""
        raise NotImplementedError
