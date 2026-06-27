"""
核心 Agent 单元测试
覆盖：DiagnosisAgent、JudgeAgent、DecisionOrchestrator
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.diagnosis import DiagnosisAgent
from app.agents.judge import JudgeAgent
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


class TestJudgeAgent:
    """裁判 Agent 测试"""

    @pytest.fixture
    def agent(self):
        """创建 JudgeAgent 实例，mock LLM 调用"""
        agent = JudgeAgent()
        agent.llm = MagicMock()
        return agent

    @pytest.mark.asyncio
    async def test_judge_passed_defender(self, agent):
        """测试裁判通过辩护方的案例"""
        mock_response = json.dumps({
            "passed": True,
            "adopted_side": "defender",
            "reason": "辩护方的回应有理有据，修正后的内容准确",
            "quality_score": 0.9,
            "effective_issues": [],
            "overruled_issues": ["问题1", "问题2"]
        })
        agent.llm.ainvoke = AsyncMock(return_value=MagicMock(content=mock_response))

        result = await agent.judge(
            original_content="G00是快速定位指令",
            topic="G代码基础",
            content_type="lecture",
            challenge_issues=["问题1", "问题2"],
            defend_responses=["回应1：G00确实是快速定位指令", "回应2：有知识库依据"],
            revised_content="G00是快速定位指令（修正后）"
        )

        assert result["passed"] is True
        assert result["adopted_side"] == "defender"
        assert result["quality_score"] >= 0.8

    @pytest.mark.asyncio
    async def test_judge_passed_challenger(self, agent):
        """测试裁判支持审核方的案例"""
        mock_response = json.dumps({
            "passed": False,
            "adopted_side": "challenger",
            "reason": "辩护方未能有效回应实质性问题",
            "quality_score": 0.3,
            "effective_issues": ["G01是直线插补不是圆弧插补"],
            "overruled_issues": []
        })
        agent.llm.ainvoke = AsyncMock(return_value=MagicMock(content=mock_response))

        result = await agent.judge(
            original_content="G01是圆弧插补指令",
            topic="G代码基础",
            content_type="lecture",
            challenge_issues=["G01是直线插补不是圆弧插补"],
            defend_responses=["我认为G01是圆弧插补"],
            revised_content="G01是圆弧插补指令"
        )

        assert result["passed"] is False
        assert result["adopted_side"] == "challenger"
        assert len(result["effective_issues"]) > 0

    @pytest.mark.asyncio
    async def test_judge_json_parse_failure_defaults_to_not_passed(self, agent):
        """测试 JSON 解析失败时默认不通过"""
        # Mock LLM 返回无效 JSON
        agent.llm.ainvoke = AsyncMock(return_value=MagicMock(content="这不是有效的JSON响应"))

        result = await agent.judge(
            original_content="测试内容",
            topic="测试主题",
            content_type="lecture",
            challenge_issues=["问题1"],
            defend_responses=["回应1"],
            revised_content="修正后内容"
        )

        # 根据 C-5 修复，解析失败应默认不通过
        assert result["passed"] is False
        assert result["adopted_side"] == "challenger"
        assert "解析失败" in result["reason"]
        assert result["quality_score"] == 0
        assert "raw_response" in result

    @pytest.mark.asyncio
    async def test_judge_regression_check_passes(self, agent):
        """测试 P1-2: 回归验证通过的情况"""
        # 第一次 LLM 调用：裁判判决通过
        judge_response = json.dumps({
            "passed": True,
            "adopted_side": "defender",
            "reason": "辩护方的回应有理有据，修正后的内容准确",
            "quality_score": 0.9,
            "effective_issues": ["问题1：G01是直线插补不是圆弧插补"],
            "overruled_issues": []
        })

        # 第二次 LLM 调用：回归验证通过
        regression_response = json.dumps({
            "verified": True,
            "checks": [
                {"issue": "问题1：G01是直线插补不是圆弧插补", "fixed": True, "reason": "修正后内容正确描述了G01是直线插补"}
            ],
            "reason": "所有问题已正确修复"
        })

        agent.llm.ainvoke = AsyncMock(side_effect=[
            MagicMock(content=judge_response),
            MagicMock(content=regression_response)
        ])

        result = await agent.judge(
            original_content="G01是圆弧插补指令",
            topic="G代码基础",
            content_type="lecture",
            challenge_issues=["问题1：G01是直线插补不是圆弧插补"],
            defend_responses=["回应1：你说得对，G01确实是直线插补"],
            revised_content="G01是直线插补指令（已修正）"
        )

        assert result["passed"] is True
        assert result["adopted_side"] == "defender"
        assert "regression_failure" not in result

    @pytest.mark.asyncio
    async def test_judge_regression_check_fails(self, agent):
        """测试 P1-2: 回归验证失败的情况"""
        # 第一次 LLM 调用：裁判判决通过
        judge_response = json.dumps({
            "passed": True,
            "adopted_side": "defender",
            "reason": "辩护方的回应有理有据，修正后的内容准确",
            "quality_score": 0.9,
            "effective_issues": ["问题1：G01是直线插补不是圆弧插补"],
            "overruled_issues": []
        })

        # 第二次 LLM 调用：回归验证失败（修正后仍有错误）
        regression_response = json.dumps({
            "verified": False,
            "checks": [
                {"issue": "问题1：G01是直线插补不是圆弧插补", "fixed": False, "reason": "修正后内容仍错误描述G01为圆弧插补"}
            ],
            "reason": "修正未解决问题，仍有事实错误"
        })

        agent.llm.ainvoke = AsyncMock(side_effect=[
            MagicMock(content=judge_response),
            MagicMock(content=regression_response)
        ])

        result = await agent.judge(
            original_content="G01是圆弧插补指令",
            topic="G代码基础",
            content_type="lecture",
            challenge_issues=["问题1：G01是直线插补不是圆弧插补"],
            defend_responses=["回应1：我修正了"],
            revised_content="G01是圆弧插补指令（修正版）"  # 修正后仍有错误
        )

        # 回归验证失败后，判决应改为不通过
        assert result["passed"] is False
        assert "regression_failure" in result
        assert "修正回归验证未通过" in result["reason"]


class TestDecisionOrchestrator:
    """决策调度 Agent 测试"""

    @pytest.fixture
    def orchestrator(self):
        """创建 DecisionOrchestrator 实例"""
        return DecisionOrchestrator()

    @pytest.mark.asyncio
    async def test_decide_next_all_passed(self, orchestrator):
        """测试所有资源辩论通过"""
        state = {
            "debate_results": {
                "lecture": {"passed": True, "quality_score": 0.9},
                "guide": {"passed": True, "quality_score": 0.85}
            },
            "retry_count": 0,
            "decision_log": []
        }

        result = await orchestrator.decide_next(state)

        assert result == "complete"
        assert "通过" in state["decision_log"][-1]

    @pytest.mark.asyncio
    async def test_decide_next_not_passed_retry(self, orchestrator):
        """测试辩论未通过，重试次数未达上限"""
        state = {
            "debate_results": {
                "lecture": {"passed": False, "quality_score": 0.5},
                "guide": {"passed": True, "quality_score": 0.85}
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
            "debate_results": {
                "lecture": {"passed": False, "quality_score": 0.4, "degraded": True},
                "guide": {"passed": False, "quality_score": 0.3, "degraded": True}
            },
            "retry_count": 3,
            "decision_log": []
        }

        result = await orchestrator.decide_next(state)

        # 根据 P0-4 修复，应走降级完成路径
        assert result == "complete"
        assert "降级" in state["decision_log"][-1] or "最大重试次数" in state["decision_log"][-1]

    @pytest.mark.asyncio
    async def test_handle_feedback_low_correctness(self, orchestrator):
        """测试低正确率触发降维解释"""
        state = {
            "difficulty": "intermediate",
            "topic": "G代码基础",
            "decision_log": []
        }
        user_answer = {
            "correctness": 0.4,
            "topic": "G代码基础"
        }

        result = await orchestrator.handle_feedback(state, user_answer)

        assert "降维解释" in result["decision_log"][-1]
        assert result["difficulty"] == "beginner"  # 降级到更低难度

    @pytest.mark.asyncio
    async def test_handle_feedback_high_correctness(self, orchestrator):
        """测试高正确率触发进阶挑战"""
        state = {
            "difficulty": "intermediate",
            "topic": "G代码基础",
            "decision_log": []
        }
        user_answer = {
            "correctness": 0.95,
            "topic": "G代码基础"
        }

        result = await orchestrator.handle_feedback(state, user_answer)

        assert "进阶挑战" in result["decision_log"][-1]
        assert result["difficulty"] == "advanced"  # 升级到更高难度


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
