"""
核心 Agent 单元测试
覆盖：DiagnosisAgent、ReviewAgent（corrective_review 主审核路径）、DecisionOrchestrator
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.diagnosis import DiagnosisAgent
from app.agents.review import ReviewAgent
from app.agents.orchestrator import DecisionOrchestrator


class TestDiagnosisAgent:
    """学情诊断 Agent 测试"""

    @pytest.fixture
    def agent(self):
        """创建 DiagnosisAgent 实例，mock LLM 调用"""
        agent = DiagnosisAgent()
        agent.llm = MagicMock()
        return agent

    @pytest.mark.asyncio
    async def test_build_profile_zero_experience(self, agent):
        """测试零基础学习者画像构建"""
        # Mock LLM 返回
        mock_response = json.dumps({
            "knowledge_points": [
                {"name": "数控编程基础", "level": "beginner", "score": 10, "confidence": 0.3},
                {"name": "G代码", "level": "beginner", "score": 5, "confidence": 0.2}
            ],
            "blind_spots": ["数控编程基础", "G代码", "切削参数"],
            "overall_level": "beginner",
            "learning_style_analysis": "零基础学习者，需要从最基础的概念开始",
            "recommended_difficulty": "beginner"
        })
        agent.llm.ainvoke = AsyncMock(return_value=MagicMock(content=mock_response))

        input_data = {
            "education_background": "高中",
            "major": "非工科",
            "work_experience_years": 0,
            "self_assessment": {"数控编程": "不了解", "G代码": "不了解"},
            "learning_style": "practice",
            "goals": ["学习数控编程基础"]
        }

        result = await agent.build_profile(input_data)

        assert result["overall_level"] == "beginner"
        assert result["recommended_difficulty"] == "beginner"
        assert len(result["blind_spots"]) > 0
        assert "数控编程基础" in result["blind_spots"]

    @pytest.mark.asyncio
    async def test_build_profile_mechanical_background(self, agent):
        """测试有机械基础的学习者画像构建"""
        mock_response = json.dumps({
            "knowledge_points": [
                {"name": "数控编程基础", "level": "intermediate", "score": 60, "confidence": 0.7},
                {"name": "G代码", "level": "intermediate", "score": 55, "confidence": 0.6}
            ],
            "blind_spots": ["高级G代码功能", "多轴加工"],
            "overall_level": "intermediate",
            "learning_style_analysis": "有机械基础，数控知识需要系统学习",
            "recommended_difficulty": "intermediate"
        })
        agent.llm.ainvoke = AsyncMock(return_value=MagicMock(content=mock_response))

        input_data = {
            "education_background": "本科",
            "major": "机械工程",
            "work_experience_years": 2,
            "self_assessment": {"机械制图": "熟练", "普通机床": "了解", "数控编程": "不了解"},
            "learning_style": "practice",
            "goals": ["学习数控车床编程"]
        }

        result = await agent.build_profile(input_data)

        assert result["overall_level"] == "intermediate"
        assert result["recommended_difficulty"] == "intermediate"
        # 有机械基础的应该有更高的起点
        assert any(kp["score"] >= 50 for kp in result["knowledge_points"])

    @pytest.mark.asyncio
    async def test_build_profile_advanced_user(self, agent):
        """测试有数控经验的学习者画像构建"""
        mock_response = json.dumps({
            "knowledge_points": [
                {"name": "数控编程基础", "level": "advanced", "score": 85, "confidence": 0.9},
                {"name": "G代码", "level": "advanced", "score": 80, "confidence": 0.85}
            ],
            "blind_spots": ["五轴加工", "CAM编程"],
            "overall_level": "advanced",
            "learning_style_analysis": "有丰富数控经验，需要高级内容",
            "recommended_difficulty": "advanced"
        })
        agent.llm.ainvoke = AsyncMock(return_value=MagicMock(content=mock_response))

        input_data = {
            "education_background": "本科",
            "major": "机械工程",
            "work_experience_years": 5,
            "self_assessment": {"数控编程": "熟练", "G代码": "熟练", "刀具选择": "了解"},
            "learning_style": "practice",
            "goals": ["学习五轴加工技术"]
        }

        result = await agent.build_profile(input_data)

        assert result["overall_level"] == "advanced"
        assert result["recommended_difficulty"] == "advanced"
        assert "五轴加工" in result["blind_spots"]


class TestReviewAgent:
    """审核纠偏 Agent 测试（corrective_review —— 主工作流现用审核路径）"""

    @pytest.fixture
    def agent(self, monkeypatch):
        """创建 ReviewAgent 实例，mock LLM 与知识库检索

        强制关闭 tool-calling，使 corrective_review 走纯 prompt 路径，
        与本地 .env 中 USE_AGENT_TOOLS 的取值无关。
        """
        from app.core.config import get_settings
        monkeypatch.setattr(get_settings(), "USE_AGENT_TOOLS", False, raising=False)
        agent = ReviewAgent()
        agent.llm = MagicMock()
        agent.retrieve_context = MagicMock(return_value="参考资料：G00 是快速定位，G01 是直线插补。")
        return agent

    @staticmethod
    def _issues(*severities):
        return [{"issue": f"问题-{sev}-{i}", "severity": sev}
                for i, sev in enumerate(severities)]

    @pytest.mark.asyncio
    async def test_corrective_review_passes_without_issues(self, agent):
        """双视角均无问题 → 直接通过，不触发修正"""
        agent.llm.ainvoke = AsyncMock(side_effect=[
            MagicMock(content="[]"),   # 学术审查
            MagicMock(content="[]"),   # 工业审查
        ])

        content = "G00 是快速定位指令。"
        result = await agent.corrective_review(content, "G 代码基础")

        assert result["passed"] is True
        assert result["score"] == 1.0
        assert result["correction_applied"] is False
        assert result["final_content"] == content
        # 无修正路径只调用两次 LLM（双视角）
        assert agent.llm.ainvoke.await_count == 2

    @pytest.mark.asyncio
    async def test_corrective_review_correction_verified(self, agent):
        """评分低于阈值 → 触发修正，回归验证 resolved → 采纳修正内容"""
        # 3 个 critical：评分 1.0 - 0.45 = 0.55 < 0.70
        agent.llm.ainvoke = AsyncMock(side_effect=[
            MagicMock(content=json.dumps(self._issues("critical", "critical", "critical"))),  # 学术审查
            MagicMock(content="[]"),                                                          # 工业审查
            MagicMock(content="G01 是直线插补指令（已修正）"),                                    # 修正生成
            MagicMock(content=json.dumps({"verdict": "resolved", "reason": "已逐条修复"})),      # 修正验证
        ])

        original = "G01 是圆弧插补指令"
        result = await agent.corrective_review(original, "G 代码基础")

        assert result["correction_applied"] is True
        assert result["passed"] is True
        assert result["final_content"] == "G01 是直线插补指令（已修正）"
        assert result["original_score"] == pytest.approx(0.55)
        assert len(result["issues"]) == 3

    @pytest.mark.asyncio
    async def test_corrective_review_fix_rejected_falls_back(self, agent):
        """修正后回归验证 unresolved → 不通过，final_content 回退为原始内容"""
        agent.llm.ainvoke = AsyncMock(side_effect=[
            MagicMock(content=json.dumps(self._issues("critical", "critical", "critical"))),
            MagicMock(content="[]"),
            MagicMock(content="表面修改后的内容"),
            MagicMock(content=json.dumps({"verdict": "unresolved", "reason": "核心问题仍在"})),
        ])

        original = "G01 是圆弧插补指令"
        result = await agent.corrective_review(original, "G 代码基础")

        assert result["passed"] is False
        assert result["correction_applied"] is True
        assert result["final_content"] == original
        assert any("修正验证未通过" in issue for issue in result["issues"])

    def test_severity_weighted_score_boundaries(self, agent):
        """严重度加权评分：阈值边界（2 critical = 0.70 恰好通过，3 critical 不通过）"""
        score = agent._severity_weighted_score
        assert score([]) == 1.0
        assert score([{"severity": "critical"}]) == pytest.approx(0.85)
        assert score([{"severity": "critical"}] * 2) == pytest.approx(0.70)
        assert score([{"severity": "critical"}] * 3) == pytest.approx(0.55)
        assert score([{"severity": "suggestion"}] * 10) == pytest.approx(0.80)
        # 下限钳制为 0
        assert score([{"severity": "critical"}] * 10) == 0.0

    def test_parse_issues_formats(self, agent):
        """问题解析：标准/包裹/旧格式/无 JSON/正则提取"""
        parse = agent._parse_issues
        # 标准 JSON 数组
        assert parse('[{"issue": "a", "severity": "critical"}]') == [
            {"issue": "a", "severity": "critical"}]
        # markdown 代码块包裹
        assert parse('```json\n[{"issue": "b", "severity": "minor"}]\n```')[0]["issue"] == "b"
        # 旧格式：纯字符串 → 降级为 minor
        assert parse('["旧格式问题"]') == [{"issue": "旧格式问题", "severity": "minor"}]
        # 前后有说明文字时正则提取
        assert parse('审查结果如下：[{"issue": "c", "severity": "suggestion"}] 请参考')[0]["issue"] == "c"
        # 完全无 JSON → 空列表（安全默认）
        assert parse("这不是 JSON") == []

    def test_merge_issues_dedup_keeps_highest_severity(self, agent):
        """合并去重：同一问题保留最高严重度"""
        long_issue = "同" * 200  # 前 200 字符作为去重键
        merged = agent._merge_issues(
            [{"issue": long_issue, "severity": "minor"}],
            [{"issue": long_issue + "（差异后缀不计入键）", "severity": "critical"}],
        )
        assert len(merged) == 1
        assert merged[0]["severity"] == "critical"


class TestDecisionOrchestrator:
    """决策调度 Agent 测试"""

    @pytest.fixture
    def orchestrator(self):
        """创建 DecisionOrchestrator 实例"""
        return DecisionOrchestrator()

    @pytest.mark.asyncio
    async def test_decide_next_all_passed(self, orchestrator):
        """测试所有资源审核通过"""
        state = {
            "review_results": {
                "lecture": {"passed": True, "score": 0.9},
                "guide": {"passed": True, "score": 0.85}
            },
            "retry_count": 0,
            "decision_log": []
        }

        result = await orchestrator.decide_next(state)

        assert result == "complete"
        assert "通过" in state["decision_log"][-1]

    @pytest.mark.asyncio
    async def test_decide_next_not_passed_retry(self, orchestrator):
        """测试审核未通过，重试次数未达上限"""
        state = {
            "review_results": {
                "lecture": {"passed": False, "score": 0.5},
                "guide": {"passed": True, "score": 0.85}
            },
            "retry_count": 1,
            "decision_log": []
        }

        result = await orchestrator.decide_next(state)

        assert result == "retry"
        assert state["retry_count"] == 2
        assert "打回重新生成" in state["decision_log"][-1]

    @pytest.mark.asyncio
    async def test_decide_next_max_retries_degraded(self, orchestrator):
        """测试超过最大重试次数，走降级流程"""
        state = {
            "review_results": {
                "lecture": {"passed": False, "score": 0.4, "degraded": True},
                "guide": {"passed": False, "score": 0.3, "degraded": True}
            },
            "retry_count": 3,
            "decision_log": []
        }

        result = await orchestrator.decide_next(state)

        # 应走降级完成路径
        assert result == "complete"
        assert "降级" in state["decision_log"][-1] or "最大重试次数" in state["decision_log"][-1]

    @pytest.mark.asyncio
    async def test_adjust_learning_path_low_correctness(self, orchestrator):
        """测试近期正确率 < 60% 时触发难度降级"""
        path = {
            "current_stage": 1,
            "total_estimated_hours": 10,
            "path": [
                {"stage": 1, "title": "G代码基础", "difficulty": "intermediate",
                 "topics": ["G代码"], "estimated_hours": 5,
                 "prerequisites": [], "resources_type": ["lecture"], "completed": False},
            ]
        }
        # 最近 5 题正确率 = (0+0+1+1+0)/5 = 0.4 < 0.6，应触发降级
        feedback_history = [
            {"correctness": 0.0, "topic": "a"},
            {"correctness": 0.0, "topic": "b"},
            {"correctness": 1.0, "topic": "c"},
            {"correctness": 1.0, "topic": "d"},
            {"correctness": 0.0, "topic": "e"},
        ]

        result = await orchestrator.adjust_learning_path(path, feedback_history)

        stage = result["path"][0]
        assert stage["difficulty"] == "beginner"
        assert "基础巩固" in stage["title"]

    @pytest.mark.asyncio
    async def test_adjust_learning_path_high_correctness(self, orchestrator):
        """测试近期正确率 > 90% 时触发阶段进阶"""
        path = {
            "current_stage": 1,
            "total_estimated_hours": 10,
            "path": [
                {"stage": 1, "title": "G代码基础", "difficulty": "intermediate",
                 "topics": ["G代码"], "estimated_hours": 5,
                 "prerequisites": [], "resources_type": ["lecture"], "completed": False},
            ]
        }
        # 最近 5 题正确率 = (1+1+1+1+0.95)/5 > 0.9，应标记完成并推进
        feedback_history = [
            {"correctness": 1.0, "topic": "a"},
            {"correctness": 1.0, "topic": "b"},
            {"correctness": 1.0, "topic": "c"},
            {"correctness": 1.0, "topic": "d"},
            {"correctness": 0.95, "topic": "e"},
        ]

        result = await orchestrator.adjust_learning_path(path, feedback_history)

        assert result["path"][0]["completed"] is True
        assert result["current_stage"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
