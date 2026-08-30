"""试题生成 Agent。

具体的场景数据、Prompt 模板、Fallback 与规范化逻辑分别位于：
- ``app.agents.question_data``（场景 / 蓝图 / Fallback / 规范化）
- ``app.agents.prompts``（Prompt 模板）

本文件只负责编排：装配 Prompt → 调 LLM → 交给规范化。
"""
from __future__ import annotations

from app.agents.base import BaseAgent
from app.agents.prompts import (
    build_basic_prompt,
    build_comprehensive_prompt,
    build_node_practice_prompt,
)
from app.agents.question_data import (
    COMPREHENSIVE_FORMAT_VERSION,
    NODE_PRACTICE_DISTRIBUTION,
    build_comprehensive_blueprint,
    build_scene,
    fallback_comprehensive_case,
    format_avoid_questions,
    node_focus_rules,
    normalize_comprehensive_case,
    normalize_node_practice_questions,
    parse_json_result,
)
from app.core.career_tracks import build_career_prompt, get_career_track_from_input


class QuestionGeneratorAgent(BaseAgent):
    """试题生成 Agent：生成选择题、判断题、实操题"""

    # 保留旧的类属性引用，供外部代码/测试兼容
    COMPREHENSIVE_FORMAT_VERSION = COMPREHENSIVE_FORMAT_VERSION
    NODE_PRACTICE_DISTRIBUTION = NODE_PRACTICE_DISTRIBUTION

    async def generate_questions(
        self,
        topic: str,
        difficulty: str,
        profile: dict = None,
        count: int = 6,
        avoid_questions: list[str] | None = None,
    ) -> dict:
        """生成三种题型的试题（选择/判断/简答）。"""
        track = get_career_track_from_input(profile or {})
        # 领域关键词检索，避免泛化 topic 导致检索偏移
        context = self.retrieve_context(f"{track.name} {topic}")
        prompt = build_basic_prompt(
            track_name=track.name,
            track_code=track.code,
            track_prompt=build_career_prompt(track),
            topic=topic,
            difficulty=difficulty,
            context=context,
            scene=build_scene(),
            avoid_text=format_avoid_questions(avoid_questions),
            count=count,
        )
        response = await self.call_llm(prompt)
        result = parse_json_result(
            response,
            {"topic": topic, "difficulty": difficulty, "track": track.code, "questions": []},
        )
        result["track"] = result.get("track", track.code)
        return result

    async def generate_node_practice_questions(
        self,
        topic: str,
        difficulty: str,
        profile: dict = None,
        count: int = 9,
        avoid_questions: list[str] | None = None,
        node_title: str = "",
        node_topics: list[str] | None = None,
    ) -> dict:
        """生成单个学习节点练习：4 道选择题、3 道判断题、2 道简答题。"""
        track = get_career_track_from_input(profile or {})
        node_title = node_title or topic
        node_topics = [str(t) for t in (node_topics or []) if t]
        topic_text = f"{node_title}（{'、'.join(node_topics)}）" if node_topics else node_title
        context = self.retrieve_context(f"{track.name} {topic_text}", k=8)

        prompt = build_node_practice_prompt(
            track_name=track.name,
            track_code=track.code,
            track_prompt=build_career_prompt(track),
            node_title=node_title,
            topic_text=topic_text,
            difficulty=difficulty,
            context=context,
            scene=build_scene(),
            focus_rules=node_focus_rules(node_title, node_topics),
            avoid_text=format_avoid_questions(avoid_questions),
            count=count,
        )

        response = await self.call_llm(prompt)
        result = parse_json_result(
            response,
            {"topic": topic_text, "difficulty": difficulty, "track": track.code, "questions": []},
        )
        return normalize_node_practice_questions(
            result=result,
            topic=topic_text,
            difficulty=difficulty,
            track_code=track.code,
            node_title=node_title,
            node_topics=node_topics,
        )

    async def generate_comprehensive_questions(
        self,
        topics: list[str],
        difficulty: str,
        profile: dict = None,
        count: int = 5,  # noqa: ARG002 - 保留签名兼容
        avoid_questions: list[str] | None = None,
    ) -> dict:
        """生成最终综合练习：一个共享生产场景下的 2 道选择题和 3 道简答题。"""
        track = get_career_track_from_input(profile or {})
        topic_text = "、".join([t for t in topics if t]) or f"{track.name}综合实践"
        context = self.retrieve_context(f"{track.name} 综合实践 {topic_text}", k=8)

        prompt = build_comprehensive_prompt(
            track_name=track.name,
            track_code=track.code,
            track_prompt=build_career_prompt(track),
            topic_text=topic_text,
            difficulty=difficulty,
            context=context,
            blueprint=build_comprehensive_blueprint(),
            avoid_text=format_avoid_questions(avoid_questions),
        )

        response = await self.call_llm(prompt)
        fallback = fallback_comprehensive_case(difficulty, track.code)
        result = parse_json_result(response, fallback)
        return normalize_comprehensive_case(result, difficulty, track.code)

    async def run(
        self,
        topic: str = "",
        difficulty: str = "beginner",
        profile: dict = None,
        **kwargs,
    ) -> dict:
        return await self.generate_questions(topic, difficulty, profile, **kwargs)
