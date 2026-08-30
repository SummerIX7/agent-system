"""Agent tool-calling 单元测试

覆盖：
- 工具可调用性（retrieve_knowledge / fact_check_lookup 返回格式化文本）
- 开关关闭时 call_llm_with_tools 回落纯 prompt（不绑定工具、只调一次底层 LLM）
- 开启时的受限 tool-calling 循环（执行工具 → 回传 → 返回终答）
"""
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.base import BaseAgent
from app.agents import tools as agent_tools


def _fake_doc(content: str, metadata: dict):
    doc = MagicMock()
    doc.page_content = content
    doc.metadata = metadata
    return doc


def _settings(use_tools: bool, mock_mode: bool = False, max_rounds: int = 3):
    return types.SimpleNamespace(
        USE_AGENT_TOOLS=use_tools,
        MOCK_MODE=mock_mode,
        AGENT_TOOL_MAX_ROUNDS=max_rounds,
        ENABLE_KNOWLEDGE_BASE=True,
    )


class TestKnowledgeTools:
    """工具本身的可调用性"""

    def test_retrieve_knowledge_formats_docs(self):
        fake_retriever = MagicMock()
        fake_retriever.search.return_value = [
            _fake_doc("G00 是快速定位指令", {"source_name": "数控编程手册", "author": "张三"}),
        ]
        with patch("app.knowledge.retriever.get_retriever", return_value=fake_retriever), \
             patch("app.core.config.get_settings", return_value=_settings(True)):
            result = agent_tools.retrieve_knowledge.invoke({"query": "G00", "k": 3})

        assert "G00 是快速定位指令" in result
        assert "数控编程手册" in result
        fake_retriever.search.assert_called_once_with("G00", k=3)

    def test_fact_check_lookup_uses_claim_as_query(self):
        fake_retriever = MagicMock()
        fake_retriever.search.return_value = [
            _fake_doc("G01 是直线插补", {"source": "standards/g_code.md"}),
        ]
        with patch("app.knowledge.retriever.get_retriever", return_value=fake_retriever), \
             patch("app.core.config.get_settings", return_value=_settings(True)):
            result = agent_tools.fact_check_lookup.invoke({"claim": "G01 是圆弧插补"})

        assert "G01 是直线插补" in result
        fake_retriever.search.assert_called_once_with("G01 是圆弧插补", k=4)

    def test_search_never_raises_on_failure(self):
        fake_retriever = MagicMock()
        fake_retriever.search.side_effect = RuntimeError("索引未构建")
        with patch("app.knowledge.retriever.get_retriever", return_value=fake_retriever), \
             patch("app.core.config.get_settings", return_value=_settings(True)):
            result = agent_tools.retrieve_knowledge.invoke({"query": "x"})

        assert "检索失败" in result


class TestCallLLMWithToolsFallback:
    """开关关闭 / MOCK 模式下回落纯 prompt"""

    @pytest.mark.asyncio
    async def test_fallback_when_tools_disabled(self):
        agent = BaseAgent()
        agent.llm = MagicMock()
        agent.llm.ainvoke = AsyncMock(return_value=MagicMock(content="纯prompt答案"))

        tool = MagicMock()
        tool.name = "retrieve_knowledge"

        with patch("app.agents.base.get_settings", return_value=_settings(use_tools=False)):
            result = await agent.call_llm_with_tools("讲讲 G 代码", [tool], label="生成讲义")

        assert result == "纯prompt答案"
        # 未启用工具：不应绑定工具，只走一次底层 LLM
        agent.llm.bind_tools.assert_not_called()
        agent.llm.ainvoke.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_fallback_when_mock_mode(self):
        agent = BaseAgent()
        agent.llm = MagicMock()
        agent.llm.ainvoke = AsyncMock(return_value=MagicMock(content="mock答案"))
        tool = MagicMock()
        tool.name = "retrieve_knowledge"

        with patch("app.agents.base.get_settings",
                   return_value=_settings(use_tools=True, mock_mode=True)):
            result = await agent.call_llm_with_tools("q", [tool])

        assert result == "mock答案"
        agent.llm.bind_tools.assert_not_called()


class TestCallLLMWithToolsLoop:
    """开启后的受限 tool-calling 循环"""

    @pytest.mark.asyncio
    async def test_tool_loop_executes_and_returns_final(self):
        # 桩工具：被模型请求后返回一段检索结果
        tool = MagicMock()
        tool.name = "retrieve_knowledge"
        tool.invoke.return_value = "工具检索结果"

        # 桩绑定后 LLM：第一轮请求工具，第二轮给出终答
        class FakeBound:
            def __init__(self):
                self.calls = 0

            async def ainvoke(self, messages):
                self.calls += 1
                if self.calls == 1:
                    return MagicMock(
                        content="",
                        tool_calls=[{"name": "retrieve_knowledge",
                                     "args": {"query": "G00"}, "id": "call_1"}],
                    )
                return MagicMock(content="最终答案", tool_calls=[])

        bound = FakeBound()
        agent = BaseAgent()
        agent.llm = MagicMock()
        agent.llm.bind_tools = MagicMock(return_value=bound)

        with patch("app.agents.base.get_settings", return_value=_settings(use_tools=True)):
            result = await agent.call_llm_with_tools("生成讲义", [tool], label="生成讲义")

        assert result == "最终答案"
        agent.llm.bind_tools.assert_called_once()
        tool.invoke.assert_called_once_with({"query": "G00"})
        assert bound.calls == 2
        # trace 应记录两轮，且第一轮含 tool_calls
        trace = agent.collect_trace()
        assert len(trace) == 2
        assert trace[0]["tool_calls"][0]["name"] == "retrieve_knowledge"

    @pytest.mark.asyncio
    async def test_bind_tools_failure_falls_back(self):
        agent = BaseAgent()
        agent.llm = MagicMock()
        agent.llm.bind_tools = MagicMock(side_effect=RuntimeError("模型不支持工具"))
        agent.llm.ainvoke = AsyncMock(return_value=MagicMock(content="回落答案"))
        tool = MagicMock()
        tool.name = "retrieve_knowledge"

        with patch("app.agents.base.get_settings", return_value=_settings(use_tools=True)):
            result = await agent.call_llm_with_tools("q", [tool])

        assert result == "回落答案"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
