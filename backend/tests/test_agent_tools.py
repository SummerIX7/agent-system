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


class TestMachiningCalculator:
    """切削参数计算器（纯函数）"""

    def test_spindle_speed(self):
        # vc=100 m/min, D=20 mm → n = 1000*100/(π*20) ≈ 1592 r/min
        result = agent_tools.machining_calculator.invoke(
            {"operation": "spindle_speed", "cutting_speed_m_min": 100, "diameter_mm": 20})
        assert "1592" in result
        assert "r/min" in result

    def test_cutting_speed(self):
        # D=50 mm, n=1000 → vc = π*50*1000/1000 ≈ 157.1 m/min
        result = agent_tools.machining_calculator.invoke(
            {"operation": "cutting_speed", "diameter_mm": 50, "spindle_rpm": 1000})
        assert "157.1" in result

    def test_feed_rate(self):
        # fz=0.1, z=4, n=2000 → vf = 800 mm/min
        result = agent_tools.machining_calculator.invoke(
            {"operation": "feed_rate", "feed_per_tooth_mm": 0.1, "teeth": 4, "spindle_rpm": 2000})
        assert "800 mm/min" in result

    def test_invalid_params_return_error_text(self):
        result = agent_tools.machining_calculator.invoke(
            {"operation": "spindle_speed", "cutting_speed_m_min": 100, "diameter_mm": 0})
        assert "参数错误" in result
        result = agent_tools.machining_calculator.invoke({"operation": "unknown_op"})
        assert "不支持" in result


class TestStandardLookup:
    """标准条款本地检索"""

    def test_finds_matching_clause(self, tmp_path):
        standards = tmp_path / "standards"
        standards.mkdir()
        (standards / "gb_standards.md").write_text(
            "# 国标\n\nG43 为刀具长度正补偿，建立后 Z 轴移动量叠加补偿值。\n\n其他段落。",
            encoding="utf-8",
        )
        fake_dir = MagicMock()
        fake_dir.__truediv__ = lambda self, part: tmp_path / part
        with patch("app.services.kg_tree.KNOWLEDGE_BASE_DIR", tmp_path):
            result = agent_tools.standard_lookup.invoke({"query": "G43 刀具长度补偿"})
        assert "G43" in result
        assert "gb_standards" in result

    def test_no_match_returns_hint(self, tmp_path):
        (tmp_path / "standards").mkdir()
        with patch("app.services.kg_tree.KNOWLEDGE_BASE_DIR", tmp_path):
            result = agent_tools.standard_lookup.invoke({"query": "不存在的条款xyz"})
        assert "未" in result

    def test_short_query_rejected(self):
        result = agent_tools.standard_lookup.invoke({"query": "G"})
        assert "过短" in result


class TestGraphQuery:
    """知识图谱节点查询"""

    def test_returns_matching_paths(self):
        tree = {
            "name": "数控加工知识体系",
            "children": [
                {"name": "理论基础", "children": [{"name": "圆弧插补", "children": []}]},
                {"name": "实践技能", "children": [{"name": "刀具补偿", "children": []}]},
            ],
        }
        with patch("app.services.kg_tree.build_tree", return_value=tree):
            result = agent_tools.graph_query.invoke({"keyword": "圆弧插补"})
        assert "理论基础" in result
        assert "圆弧插补" in result

    def test_no_match(self):
        with patch("app.services.kg_tree.build_tree", return_value={"name": "根", "children": []}):
            result = agent_tools.graph_query.invoke({"keyword": "不存在xyz"})
        assert "未找到" in result


class TestCallLLMWithToolsFallback:
    """开关关闭时回落纯 prompt"""

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
    async def test_mock_mode_runs_preset_tool_loop(self):
        """MOCK_MODE 下同样走工具循环：MockLLM 预设 tool_call，工具在本地真实执行"""
        from app.mock.llm import MockLLM
        agent = BaseAgent()
        agent.llm = MockLLM()

        tool = MagicMock()
        tool.name = "retrieve_knowledge"
        tool.args = {"query": {"title": "query", "type": "string"}}
        tool.invoke.return_value = "本地工具执行结果"

        with patch("app.agents.base.get_settings",
                   return_value=_settings(use_tools=True, mock_mode=True)):
            result = await agent.call_llm_with_tools("讲讲 G 代码", [tool], label="生成讲义")

        # 预设 tool_call 触发了一次真实工具执行，终答来自 Mock 预设响应
        tool.invoke.assert_called_once()
        assert result  # label="生成讲义" 命中 MOCK_RESPONSES_BY_LABEL
        trace = agent.collect_trace()
        assert any(t.get("tool_calls") for t in trace)


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
