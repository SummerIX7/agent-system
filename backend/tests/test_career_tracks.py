"""
职业方向配置测试
覆盖：CareerTrackConfig、3 个职业方向、诊断/出题的职业感知
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from app.core.career_tracks import (
    get_career_track, get_default_career_track, get_all_career_tracks,
    get_career_track_from_input, build_career_prompt,
    CAREER_TRACKS,
)


class TestCareerTrackConfig:
    """职业方向配置测试"""

    def test_get_career_track_operator(self):
        track = get_career_track("operator")
        assert track is not None
        assert track.code == "operator"
        assert track.name == "操机工"
        assert track.order == 1
        assert len(track.self_assessment_skills) == 8
        assert len(track.core_topics) >= 8

    def test_get_career_track_setup_tech(self):
        track = get_career_track("setup_tech")
        assert track is not None
        assert track.code == "setup_tech"
        assert track.name == "调机工"
        assert track.order == 2
        assert "对刀操作" in track.self_assessment_skills

    def test_get_career_track_programmer(self):
        track = get_career_track("programmer")
        assert track is not None
        assert track.code == "programmer"
        assert track.name == "编程师"
        assert track.order == 3
        assert "手工G代码编程" in track.self_assessment_skills

    def test_get_career_track_nonexistent(self):
        assert get_career_track("nonexistent") is None

    def test_get_default_career_track(self):
        track = get_default_career_track()
        assert track.code == "operator"

    def test_get_all_career_tracks(self):
        tracks = get_all_career_tracks()
        assert len(tracks) == 3
        assert tracks[0].order <= tracks[1].order <= tracks[2].order

    # ── get_career_track_from_input ──

    def test_explicit_track_code(self):
        assert get_career_track_from_input({"career_track": "operator"}).code == "operator"
        assert get_career_track_from_input({"career_track": "setup_tech"}).code == "setup_tech"
        assert get_career_track_from_input({"career_track": "programmer"}).code == "programmer"

    def test_default_when_no_input(self):
        assert get_career_track_from_input({}).code == "operator"

    def test_default_when_unknown_code(self):
        assert get_career_track_from_input({"career_track": "unknown"}).code == "operator"

    # ── build_career_prompt ──

    def test_build_prompt_operator(self):
        track = get_career_track("operator")
        prompt = build_career_prompt(track)
        assert "操机工" in prompt
        assert "工件装夹" in prompt or "机床操作" in prompt

    def test_build_prompt_programmer(self):
        track = get_career_track("programmer")
        prompt = build_career_prompt(track)
        assert "编程师" in prompt
        assert "G代码" in prompt or "CAM" in prompt

    # ── 层级关系验证 ──

    def test_prerequisite_chain(self):
        """验证前置知识链条：编程师需要调机工基础，调机工需要操机工基础"""
        operator = CAREER_TRACKS["operator"]
        setup_tech = CAREER_TRACKS["setup_tech"]
        programmer = CAREER_TRACKS["programmer"]

        assert operator.prerequisite_knowledge == "无前置要求，零基础可学。"
        assert "操机工" in setup_tech.prerequisite_knowledge
        assert "操机工" in programmer.prerequisite_knowledge
        assert "调机工" in programmer.prerequisite_knowledge


class TestCareerTrackAwareDiagnosis:
    """职业方向感知的诊断测试"""

    @pytest.fixture
    def agent(self):
        from app.agents.diagnosis import DiagnosisAgent
        agent = DiagnosisAgent()
        agent.llm = MagicMock()
        return agent

    @pytest.mark.asyncio
    async def test_operator_diagnosis(self, agent):
        mock_profile = json.dumps({
            "knowledge_points": [
                {"name": "机床操作面板", "level": "beginner", "score": 20, "confidence": 0.6},
                {"name": "工件装夹", "level": "beginner", "score": 15, "confidence": 0.5},
            ],
            "blind_spots": ["G代码阅读", "刀具装卸"],
            "overall_level": "beginner",
            "learning_style_analysis": "零基础，从操作开始",
            "recommended_difficulty": "beginner",
            "career_track": "operator",
            "career_track_name": "操机工",
        })
        agent.llm.ainvoke = AsyncMock(return_value=MagicMock(content=mock_profile))

        input_data = {
            "career_track": "operator",
            "education_background": "高中",
            "major": "非工科",
            "work_experience_years": 0,
            "self_assessment": {"机床操作面板使用": "不了解"},
            "goals": ["学习机床操作"],
        }

        result = await agent.build_profile(input_data)
        assert result["career_track"] == "operator"
        assert result["career_track_name"] == "操机工"
        assert result["overall_level"] == "beginner"

    @pytest.mark.asyncio
    async def test_programmer_diagnosis(self, agent):
        mock_profile = json.dumps({
            "knowledge_points": [
                {"name": "G代码编程", "level": "intermediate", "score": 60, "confidence": 0.7},
                {"name": "CAM软件", "level": "intermediate", "score": 55, "confidence": 0.65},
            ],
            "blind_spots": ["多轴编程", "宏程序编写"],
            "overall_level": "intermediate",
            "learning_style_analysis": "有操机和调机基础，编程方向需要系统学习",
            "recommended_difficulty": "intermediate",
            "career_track": "programmer",
            "career_track_name": "编程师",
        })
        agent.llm.ainvoke = AsyncMock(return_value=MagicMock(content=mock_profile))

        input_data = {
            "career_track": "programmer",
            "education_background": "本科",
            "major": "机械工程",
            "work_experience_years": 3,
            "self_assessment": {"手工G代码编程": "了解基础", "CAM软件编程(UG/Mastercam)": "不了解"},
            "goals": ["学习数控编程"],
        }

        result = await agent.build_profile(input_data)
        assert result["career_track"] == "programmer"
        assert result["career_track_name"] == "编程师"


class TestCareerTrackAwareQuestions:
    """职业方向感知的试题生成测试"""

    @pytest.fixture
    def agent(self):
        from app.agents.question_generator import QuestionGeneratorAgent
        agent = QuestionGeneratorAgent()
        agent.llm = MagicMock()
        return agent

    @pytest.mark.asyncio
    async def test_operator_questions(self, agent):
        mock_questions = json.dumps({
            "topic": "机床操作",
            "difficulty": "beginner",
            "career_track": "operator",
            "questions": [
                {"question": "紧急停止按钮是什么颜色？", "question_type": "multiple_choice",
                 "options": ["A. 绿色", "B. 红色", "C. 黄色", "D. 蓝色"],
                 "correct_answer": "B", "explanation": "急停按钮为红色"},
                {"question": "卡尺可以测量外径", "question_type": "true_false",
                 "options": ["正确", "错误"], "correct_answer": "正确",
                 "explanation": "游标卡尺可测量外径、内径和深度"},
                {"question": "简述工件装夹的步骤", "question_type": "practical",
                 "options": [], "correct_answer": "1.清洁工作台 2.放置工件 3.初步紧固 4.找正 5.最终紧固",
                 "explanation": "按步骤评分"},
            ],
        })
        agent.llm.ainvoke = AsyncMock(return_value=MagicMock(content=mock_questions))

        result = await agent.generate_questions("机床操作", "beginner", {"career_track": "operator"})
        assert result["career_track"] == "operator"
        assert len(result["questions"]) == 3

    @pytest.mark.asyncio
    async def test_programmer_questions(self, agent):
        mock_questions = json.dumps({
            "topic": "G代码编程",
            "difficulty": "intermediate",
            "career_track": "programmer",
            "questions": [
                {"question": "G02是什么指令？", "question_type": "multiple_choice",
                 "options": ["A. 直线插补", "B. 顺时针圆弧插补", "C. 逆时针圆弧插补", "D. 快速定位"],
                 "correct_answer": "B", "explanation": "G02=顺时针圆弧"},
                {"question": "G41是刀具半径左补偿", "question_type": "true_false",
                 "options": ["正确", "错误"], "correct_answer": "正确",
                 "explanation": "G41=左补偿，G42=右补偿"},
            ],
        })
        agent.llm.ainvoke = AsyncMock(return_value=MagicMock(content=mock_questions))

        result = await agent.generate_questions("G代码编程", "intermediate", {"career_track": "programmer"})
        assert result["career_track"] == "programmer"
        assert len(result["questions"]) == 2
