"""Mock LLM：替换 ChatOpenAI，根据 prompt 内容返回预设响应，不调用外部 API。"""

import contextvars
from typing import Any

from app.mock.responses import MOCK_RESPONSES_BY_LABEL, match_response_by_prompt

# contextvars 用于在 BaseAgent.call_llm() 中传输 label 到 MockLLM.ainvoke()
_mock_label: contextvars.ContextVar[str] = contextvars.ContextVar("_mock_label", default="")


class MockLLMResponse:
    """模拟 langchain_core.messages.AIMessage，提供 .content 属性"""

    def __init__(self, content: str):
        self.content = content

    def __repr__(self):
        preview = self.content[:60].replace("\n", " ")
        return f"MockLLMResponse({preview}...)"


class MockLLM:
    """替代 ChatOpenAI 的 Mock LLM。所有调用返回本地预设数据，零网络开销。"""

    def __init__(self, **kwargs):
        # 接受但忽略所有参数（兼容 ChatOpenAI 构造函数签名）
        pass

    async def ainvoke(self, prompt: str, **kwargs) -> MockLLMResponse:
        """异步调用入口：所有 LLM 调用最终经过此方法"""
        label = _mock_label.get()
        content = self._resolve(prompt, label)
        return MockLLMResponse(content)

    def invoke(self, prompt: str, **kwargs) -> MockLLMResponse:
        """同步调用入口（兼容性）"""
        label = _mock_label.get()
        content = self._resolve(prompt, label)
        return MockLLMResponse(content)

    def _resolve(self, prompt: str, label: str) -> str:
        """按优先级解析响应：
        1. label 匹配（9 个标记调用）
        2. prompt 子串匹配（14 个未标记调用）
        3. 兜底 JSON
        """
        # Priority 1: label-keyed dispatch
        if label and label in MOCK_RESPONSES_BY_LABEL:
            return MOCK_RESPONSES_BY_LABEL[label]

        # Priority 2: prompt pattern matching
        return match_response_by_prompt(prompt)

    # 兼容 langchain 的内部属性访问
    def __getattr__(self, name: str) -> Any:
        if name in ("_identifying_params", "_llm_type", "model_name"):
            return "mock"
        raise AttributeError(f"MockLLM has no attribute '{name}'")
