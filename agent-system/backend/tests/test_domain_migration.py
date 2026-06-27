"""
领域迁移性测试
验证系统在不同领域（CNC、Python 数据分析）下的表现
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from app.core.domains import (
    get_domain, get_default_domain, get_domain_from_input,
    build_domain_prompt, DOMAINS
)
from app.agents.diagnosis import DiagnosisAgent
from app.agents.question_generator import QuestionGeneratorAgent


class TestDomainConfig:
    """领域配置测试"""

    def test_get_domain_cnc(self):
        """测试获取 CNC 领域配置"""
        domain = get_domain("cnc")
        assert domain is not None
        assert domain.name == "CNC 数控加工"
        assert domain.code == "cnc"
        assert "数控编程" in domain.core_topics
        assert "Python" in domain.excluded_topics

    def test_get_domain_python_data_analysis(self):
        """测试获取 Python 数据分析领域配置"""
        domain = get_domain("python_data_analysis")
        assert domain is not None
        assert domain.name == "Python 数据分析"
        assert domain.code == "python_data_analysis"
        assert "NumPy" in domain.core_topics
        assert "数控" in domain.excluded_topics

    def test_get_domain_not_exist(self):
        """测试获取不存在的领域"""
        domain = get_domain("nonexistent")
        assert domain is None

    def test_get_default_domain(self):
        """测试获取默认领域"""
        domain = get_default_domain()
        assert domain.code == "cnc"

    def test_get_domain_from_input_explicit(self):
        """测试从输入中显式指定领域"""
        input_data = {"domain": "python_data_analysis"}
        domain = get_domain_from_input(input_data)
        assert domain.code == "python_data_analysis"

    def test_get_domain_from_input_goals(self):
        """测试从 goals 推断领域"""
        input_data = {"goals": ["学习NumPy数组操作", "掌握Pandas数据处理"]}
        domain = get_domain_from_input(input_data)
        assert domain.code == "python_data_analysis"

    def test_get_domain_from_input_default(self):
        """测试默认领域推断"""
        input_data = {"goals": ["学习新知识"]}
        domain = get_domain_from_input(input_data)
        assert domain.code == "cnc"  # 默认领域

    def test_build_domain_prompt_cnc(self):
        """测试构建 CNC 领域 prompt"""
        domain = get_domain("cnc")
        prompt = build_domain_prompt(domain)
        assert "CNC" in prompt
        assert "数控编程" in prompt
        assert "Python" in prompt  # 排除的主题

    def test_build_domain_prompt_python(self):
        """测试构建 Python 数据分析领域 prompt"""
        domain = get_domain("python_data_analysis")
        prompt = build_domain_prompt(domain)
        assert "Python" in prompt
        assert "NumPy" in prompt
        assert "数控" in prompt  # 排除的主题


class TestDomainMigrationDiagnosis:
    """领域迁移性测试 - 学情诊断 Agent"""

    @pytest.fixture
    def agent(self):
        """创建 DiagnosisAgent 实例，mock LLM 调用"""
        agent = DiagnosisAgent()
        agent.llm = MagicMock()
        return agent

    @pytest.mark.asyncio
    async def test_cnc_domain_diagnosis(self, agent):
        """测试 CNC 领域的学情诊断"""
        mock_response = json.dumps({
            "knowledge_points": [
                {"name": "数控编程基础", "level": "beginner", "score": 10, "confidence": 0.3},
                {"name": "G代码", "level": "beginner", "score": 5, "confidence": 0.2}
            ],
            "blind_spots": ["数控编程基础", "G代码"],
            "overall_level": "beginner",
            "learning_style_analysis": "零基础学习者",
            "recommended_difficulty": "beginner",
            "domain": "cnc"
        })
        agent.llm.ainvoke = AsyncMock(return_value=MagicMock(content=mock_response))

        input_data = {
            "domain": "cnc",
            "education_background": "高中",
            "major": "非工科",
            "work_experience_years": 0,
            "self_assessment": {"数控编程": "不了解"},
            "goals": ["学习数控编程基础"]
        }

        result = await agent.build_profile(input_data)

        assert result["domain"] == "cnc"
        assert result["overall_level"] == "beginner"
        # 应该包含 CNC 相关的知识点
        assert any("数控" in kp.get("name", "") for kp in result["knowledge_points"])

    @pytest.mark.asyncio
    async def test_python_data_analysis_domain_diagnosis(self, agent):
        """测试 Python 数据分析领域的学情诊断"""
        mock_response = json.dumps({
            "knowledge_points": [
                {"name": "Python基础", "level": "beginner", "score": 15, "confidence": 0.4},
                {"name": "NumPy", "level": "beginner", "score": 5, "confidence": 0.2},
                {"name": "Pandas", "level": "beginner", "score": 5, "confidence": 0.2}
            ],
            "blind_spots": ["NumPy", "Pandas", "数据可视化"],
            "overall_level": "beginner",
            "learning_style_analysis": "零基础学习者",
            "recommended_difficulty": "beginner",
            "domain": "python_data_analysis"
        })
        agent.llm.ainvoke = AsyncMock(return_value=MagicMock(content=mock_response))

        input_data = {
            "domain": "python_data_analysis",
            "education_background": "本科",
            "major": "市场营销",
            "work_experience_years": 0,
            "self_assessment": {"Python": "不了解"},
            "goals": ["学习Python数据分析"]
        }

        result = await agent.build_profile(input_data)

        assert result["domain"] == "python_data_analysis"
        assert result["overall_level"] == "beginner"
        # 应该包含 Python 数据分析相关的知识点
        assert any("Python" in kp.get("name", "") or "NumPy" in kp.get("name", "")
                    for kp in result["knowledge_points"])


class TestDomainMigrationQuestionGenerator:
    """领域迁移性测试 - 试题生成 Agent"""

    @pytest.fixture
    def agent(self):
        """创建 QuestionGeneratorAgent 实例，mock LLM 调用"""
        agent = QuestionGeneratorAgent()
        agent.llm = MagicMock()
        return agent

    @pytest.mark.asyncio
    async def test_cnc_domain_questions(self, agent):
        """测试 CNC 领域的试题生成"""
        mock_response = json.dumps({
            "topic": "G代码基础",
            "difficulty": "beginner",
            "domain": "cnc",
            "questions": [
                {
                    "question": "G00是什么指令？",
                    "question_type": "multiple_choice",
                    "options": ["A. 快速定位", "B. 直线插补", "C. 圆弧插补", "D. 暂停"],
                    "correct_answer": "A",
                    "explanation": "G00是快速定位指令"
                }
            ]
        })
        agent.llm.ainvoke = AsyncMock(return_value=MagicMock(content=mock_response))

        profile = {"domain": "cnc"}
        result = await agent.generate_questions("G代码基础", "beginner", profile)

        assert result["domain"] == "cnc"
        assert len(result["questions"]) > 0
        # 应该包含 CNC 相关的题目
        assert any("G00" in q.get("question", "") for q in result["questions"])

    @pytest.mark.asyncio
    async def test_python_data_analysis_domain_questions(self, agent):
        """测试 Python 数据分析领域的试题生成"""
        mock_response = json.dumps({
            "topic": "NumPy基础",
            "difficulty": "beginner",
            "domain": "python_data_analysis",
            "questions": [
                {
                    "question": "NumPy中创建数组的函数是什么？",
                    "question_type": "multiple_choice",
                    "options": ["A. array()", "B. list()", "C. dict()", "D. set()"],
                    "correct_answer": "A",
                    "explanation": "NumPy使用array()函数创建数组"
                }
            ]
        })
        agent.llm.ainvoke = AsyncMock(return_value=MagicMock(content=mock_response))

        profile = {"domain": "python_data_analysis"}
        result = await agent.generate_questions("NumPy基础", "beginner", profile)

        assert result["domain"] == "python_data_analysis"
        assert len(result["questions"]) > 0
        # 应该包含 Python 数据分析相关的题目
        assert any("NumPy" in q.get("question", "") for q in result["questions"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
