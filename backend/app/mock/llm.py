"""Mock LLM：替换 ChatOpenAI，根据 prompt 内容返回预设响应，不调用外部 API。"""

import asyncio
import contextvars
from typing import Any, AsyncIterator

from app.mock.responses import MOCK_RESPONSES_BY_LABEL, match_response_by_prompt

# contextvars 用于在 BaseAgent.call_llm() 中传输 label 到 MockLLM.ainvoke()
_mock_label: contextvars.ContextVar[str] = contextvars.ContextVar("_mock_label", default="")


class MockLLMResponse:
    """模拟 langchain_core.messages.AIMessage，提供 .content / .tool_calls 属性"""

    def __init__(self, content: str, tool_calls: list | None = None):
        self.content = content
        self.tool_calls = tool_calls or []

    def __repr__(self):
        preview = self.content[:60].replace("\n", " ")
        return f"MockLLMResponse({preview}...)"


def _default_tool_args(tool_obj, prompt: str) -> dict:
    """为预设 tool_call 推导一组合理参数（按工具 schema 的字段名分派）。"""
    schema = getattr(tool_obj, "args", None) or {}
    snippet = prompt[:30].replace("\n", " ").strip() or "数控加工"
    if "claim" in schema:
        return {"claim": snippet}
    if "query" in schema:
        return {"query": snippet}
    if "keyword" in schema:
        return {"keyword": snippet[:10]}
    if "operation" in schema:
        return {"operation": "cutting_speed", "diameter_mm": 50, "spindle_rpm": 1000}
    return {}


class _MockBoundLLM:
    """MockLLM.bind_tools() 的返回物：第一轮固定请求一个预设 tool_call，
    工具结果回传后（消息列表中出现 ToolMessage）返回最终文本。

    使 MOCK_MODE 下也能完整演示 tool-calling 轨迹（工具在本地真实执行）。
    """

    def __init__(self, mock: "MockLLM", tools: list):
        self._mock = mock
        self._tools = list(tools)

    async def ainvoke(self, messages, **kwargs) -> MockLLMResponse:
        from langchain_core.messages import ToolMessage

        prompt = ""
        if messages:
            first = messages[0]
            prompt = getattr(first, "content", first) or ""
            if not isinstance(prompt, str):
                prompt = str(prompt)

        # 工具已执行 → 给终答（与真实模型行为一致）
        if any(isinstance(m, ToolMessage) for m in messages):
            return MockLLMResponse(self._mock._resolve(prompt, _mock_label.get()))

        # 第一轮：请求第一个可用工具的预设调用
        if not self._tools:
            return MockLLMResponse(self._mock._resolve(prompt, _mock_label.get()))
        tool_obj = self._tools[0]
        tool_call = {
            "name": getattr(tool_obj, "name", "unknown_tool"),
            "args": _default_tool_args(tool_obj, prompt),
            "id": "mock_call_1",
        }
        return MockLLMResponse("", tool_calls=[tool_call])


class MockLLM:
    """替代 ChatOpenAI 的 Mock LLM。所有调用返回本地预设数据，零网络开销。"""

    def __init__(self, **kwargs):
        # 接受但忽略所有参数（兼容 ChatOpenAI 构造函数签名）
        pass

    async def ainvoke(self, prompt: str, **kwargs) -> MockLLMResponse:
        """异步调用入口：所有 LLM 调用最终经过此方法"""
        label = _mock_label.get()
        content = self._resolve(self._prompt_text(prompt), label)
        return MockLLMResponse(content)

    def invoke(self, prompt: str, **kwargs) -> MockLLMResponse:
        """同步调用入口（兼容性）"""
        label = _mock_label.get()
        content = self._resolve(self._prompt_text(prompt), label)
        return MockLLMResponse(content)

    def bind_tools(self, tools: list, **kwargs) -> _MockBoundLLM:
        """返回预设 tool_call 的绑定 LLM（Mock 下也可演示 tool-calling 轨迹）。"""
        return _MockBoundLLM(self, tools)

    @staticmethod
    def _prompt_text(prompt) -> str:
        """兼容传入消息列表的调用（取首条消息内容）。"""
        if isinstance(prompt, str):
            return prompt
        if isinstance(prompt, (list, tuple)) and prompt:
            return str(getattr(prompt[0], "content", prompt[0]) or "")
        return str(prompt or "")

    async def astream(self, prompt: str, **kwargs) -> AsyncIterator[MockLLMResponse]:
        """流式入口：把预设响应切片 yield，模拟打字机效果（供 call_llm_stream 演示）。"""
        label = _mock_label.get()
        content = self._resolve(prompt, label)
        chunk_size = 24
        for i in range(0, len(content), chunk_size):
            await asyncio.sleep(0.01)
            yield MockLLMResponse(content[i:i + chunk_size])

    def _resolve(self, prompt: str, label: str) -> str:
        """按优先级解析响应：
        1. label 匹配（静态响应直接用，可调用项以 prompt 求值）
        2. prompt 子串匹配（未标记调用）
        3. 兜底 JSON
        """
        # Priority 1: label-keyed dispatch
        if label and label in MOCK_RESPONSES_BY_LABEL:
            entry = MOCK_RESPONSES_BY_LABEL[label]
            # 需要读取输入的响应（如随画像分化的 build_profile）注册为 callable
            return entry(prompt) if callable(entry) else entry

        # Priority 2: prompt pattern matching
        return match_response_by_prompt(prompt)

    # 兼容 langchain 的内部属性访问
    def __getattr__(self, name: str) -> Any:
        if name in ("_identifying_params", "_llm_type", "model_name"):
            return "mock"
        raise AttributeError(f"MockLLM has no attribute '{name}'")
