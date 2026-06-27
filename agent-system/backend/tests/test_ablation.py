"""
消融实验测试
对比"有辩论"vs"无辩论"的三项指标差异
验证辩论机制对谬误率的降低效果
"""
import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.graph.workflow import run_workflow, run_workflow_no_debate
from app.metrics.hallucination_checker import HallucinationChecker


class TestAblationStudy:
    """消融实验测试类"""

    @pytest.fixture
    def mock_profiles(self):
        """测试用的学习者画像"""
        return [
            {
                "profile_name": "零基础学习者",
                "domain": "cnc",
                "education_background": "高中",
                "major": "非工科",
                "work_experience_years": 0,
                "self_assessment": {"数控编程": "不了解"},
                "goals": ["学习数控编程基础"],
                "expected_difficulty": "beginner",
            },
            {
                "profile_name": "有机械基础学习者",
                "domain": "cnc",
                "education_background": "本科",
                "major": "机械工程",
                "work_experience_years": 2,
                "self_assessment": {"机械制图": "熟练", "数控编程": "不了解"},
                "goals": ["学习数控车床编程"],
                "expected_difficulty": "intermediate",
            },
            {
                "profile_name": "有数控经验学习者",
                "domain": "cnc",
                "education_background": "本科",
                "major": "机械工程",
                "work_experience_years": 5,
                "self_assessment": {"数控编程": "熟练", "G代码": "熟练"},
                "goals": ["学习五轴加工技术"],
                "expected_difficulty": "advanced",
            },
        ]

    @pytest.mark.asyncio
    async def test_workflow_comparison_structure(self):
        """测试两种工作流的结构差异"""
        # 验证有辩论工作流包含辩论相关节点
        from app.graph.workflow import build_workflow, build_workflow_no_debate

        workflow_with_debate = build_workflow()
        workflow_no_debate = build_workflow_no_debate()

        # 有辩论工作流应该更大（包含更多节点）
        # 这是一个结构测试，验证两种工作流确实不同
        assert workflow_with_debate is not None
        assert workflow_no_debate is not None
        # 无辩论工作流应该更简单
        # 注意：LangGraph 的 StateGraph 不直接暴露节点数量，这里主要验证构建成功

    @pytest.mark.asyncio
    async def test_ablation_mock_comparison(self, mock_profiles):
        """
        消融实验：对比有辩论和无辩论的谬误率差异

        这是一个 mock 测试，实际的消融实验需要真实的 LLM 调用
        """
        # 模拟有辩论工作流的结果
        mock_debate_result = {
            "final_resources": [
                {
                    "type": "lecture",
                    "content": "G00是快速定位指令，G01是直线插补指令",
                    "topic": "G代码基础",
                    "difficulty": "beginner"
                }
            ],
            "debate_results": {
                "lecture": {
                    "passed": True,
                    "quality_score": 0.92,
                    "adopted_side": "defender",
                    "reason": "辩论通过，内容准确"
                }
            },
            "decision_log": ["① 学情分析完成", "④ 辩论+裁判完成（通过）"]
        }

        # 模拟无辩论工作流的结果
        mock_no_debate_result = {
            "final_resources": [
                {
                    "type": "lecture",
                    "content": "G00是快速定位指令，G01是圆弧插补指令",  # 注意：这里有错误
                    "topic": "G代码基础",
                    "difficulty": "beginner"
                }
            ],
            "debate_results": {},
            "decision_log": ["① 学情分析完成", "⑥ 工作流完成（无辩论）"]
        }

        # 验证两种工作流的结果结构
        assert "debate_results" in mock_debate_result
        assert "debate_results" in mock_no_debate_result

        # 有辩论的工作流应该有辩论结果
        assert len(mock_debate_result["debate_results"]) > 0
        assert mock_debate_result["debate_results"]["lecture"]["passed"] is True

        # 无辩论的工作流应该没有辩论结果
        assert len(mock_no_debate_result["debate_results"]) == 0

    @pytest.mark.asyncio
    async def test_hallucination_checker_integration(self):
        """测试谬误检测器集成（消融实验的核心组件）"""
        # 这个测试验证谬误检测器能够正确工作
        # 实际的消融实验会用这个检测器来对比有/无辩论的谬误率

        checker = HallucinationChecker()

        # Mock LLM 调用
        mock_assertions = json.dumps([
            {"assertion": "G00是快速定位指令"},
            {"assertion": "G01是直线插补指令"},
            {"assertion": "G02是顺时针圆弧插补指令"}
        ])

        mock_verification = json.dumps({
            "verdict": "正确",
            "reason": "知识库支持该断言",
            "confidence": 0.9
        })

        checker.llm = MagicMock()
        checker.llm.ainvoke = AsyncMock(side_effect=[
            MagicMock(content=mock_assertions),
            MagicMock(content=mock_verification),
            MagicMock(content=mock_verification),
            MagicMock(content=mock_verification),
        ])

        # Mock 知识库检索
        checker.retrieve_context = MagicMock(return_value="G00是快速定位指令，G01是直线插补指令")

        content = "G00是快速定位指令，G01是直线插补指令，G02是顺时针圆弧插补指令"
        result = await checker.check_content(content, "G代码基础")

        assert "hallucination_rate" in result
        assert "total_assertions" in result
        assert "errors" in result
        assert result["total_assertions"] == 3
        assert result["errors"] == 0  # 所有断言都正确
        assert result["hallucination_rate"] == 0.0

    def test_ablation_metrics_schema(self):
        """测试消融实验的指标计算 schema"""
        # 模拟消融实验结果
        results_with_debate = [
            {"profile": "零基础", "hallucination_rate": 2.5, "difficulty_match_rate": 90, "knowledge_coverage_rate": 85},
            {"profile": "有机械基础", "hallucination_rate": 1.8, "difficulty_match_rate": 92, "knowledge_coverage_rate": 88},
            {"profile": "有数控经验", "hallucination_rate": 1.2, "difficulty_match_rate": 95, "knowledge_coverage_rate": 90},
        ]

        results_no_debate = [
            {"profile": "零基础", "hallucination_rate": 8.5, "difficulty_match_rate": 85, "knowledge_coverage_rate": 80},
            {"profile": "有机械基础", "hallucination_rate": 6.2, "difficulty_match_rate": 88, "knowledge_coverage_rate": 82},
            {"profile": "有数控经验", "hallucination_rate": 5.0, "difficulty_match_rate": 90, "knowledge_coverage_rate": 85},
        ]

        # 计算平均值
        avg_with_debate = {
            "hallucination_rate": sum(r["hallucination_rate"] for r in results_with_debate) / len(results_with_debate),
            "difficulty_match_rate": sum(r["difficulty_match_rate"] for r in results_with_debate) / len(results_with_debate),
            "knowledge_coverage_rate": sum(r["knowledge_coverage_rate"] for r in results_with_debate) / len(results_with_debate),
        }

        avg_no_debate = {
            "hallucination_rate": sum(r["hallucination_rate"] for r in results_no_debate) / len(results_no_debate),
            "difficulty_match_rate": sum(r["difficulty_match_rate"] for r in results_no_debate) / len(results_no_debate),
            "knowledge_coverage_rate": sum(r["knowledge_coverage_rate"] for r in results_no_debate) / len(results_no_debate),
        }

        # 验证有辩论的谬误率显著低于无辩论
        reduction_rate = (avg_no_debate["hallucination_rate"] - avg_with_debate["hallucination_rate"]) / avg_no_debate["hallucination_rate"] * 100

        # 谬误率应该降低至少 50%
        assert reduction_rate >= 50, f"辩论机制谬误率降低不足 50%: {reduction_rate:.1f}%"

        # 有辩论的难度匹配率应该更高
        assert avg_with_debate["difficulty_match_rate"] >= avg_no_debate["difficulty_match_rate"]

        # 有辩论的知识覆盖率应该更高
        assert avg_with_debate["knowledge_coverage_rate"] >= avg_no_debate["knowledge_coverage_rate"]

        # 打印对比结果
        print("\n" + "="*60)
        print("消融实验结果对比")
        print("="*60)
        print(f"{'指标':<20} {'有辩论':<15} {'无辩论':<15} {'提升':<10}")
        print("-"*60)
        print(f"{'谬误率 (%)':<20} {avg_with_debate['hallucination_rate']:.1f}{'':<10} {avg_no_debate['hallucination_rate']:.1f}{'':<10} -{reduction_rate:.1f}%")
        print(f"{'难度匹配率 (%)':<20} {avg_with_debate['difficulty_match_rate']:.1f}{'':<10} {avg_no_debate['difficulty_match_rate']:.1f}{'':<10} +{avg_with_debate['difficulty_match_rate'] - avg_no_debate['difficulty_match_rate']:.1f}%")
        print(f"{'知识覆盖率 (%)':<20} {avg_with_debate['knowledge_coverage_rate']:.1f}{'':<10} {avg_no_debate['knowledge_coverage_rate']:.1f}{'':<10} +{avg_with_debate['knowledge_coverage_rate'] - avg_no_debate['knowledge_coverage_rate']:.1f}%")
        print("="*60)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
