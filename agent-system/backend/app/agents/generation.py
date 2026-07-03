import json
from typing import List, Optional

from app.agents.base import BaseAgent
from app.core.career_tracks import CareerTrackConfig, build_career_prompt, get_default_career_track


class GenerationAgent(BaseAgent):
    """知识生成 Agent：生成讲义、实验指导、项目案例（含知识溯源）"""

    def _source_citation_rules(self) -> str:
        """来源引用规则"""
        return """
[来源引用规则 — 必须遵守]
1. 每个知识点必须标注来源，格式如下：

   [知识点：XXX]
    来源：《书名》(作者, 年份) 章节
    链接：URL（如有）
   权威度：

2. 来源信息从知识库参考内容中提取，不要编造
3. 如果知识库中没有相关信息，标注"[需人工确认来源]"
4. 禁止编造不存在的书名、论文或 URL
5. 多个知识点可引用同一来源，但每个知识点必须单独标注"""

    async def generate_lecture_notes(self, topic: str, profile: dict,
                                     track: Optional[CareerTrackConfig] = None,
                                     retry_context: str = "") -> str:
        """生成定制化讲义（含知识溯源）"""
        track = track or get_default_career_track()
        context = self.retrieve_context(f"{track.name} {topic}")
        difficulty = profile.get("recommended_difficulty", "beginner")
        track_prompt = build_career_prompt(track)

        # 重试上下文：注入上一轮审核未通过的问题
        retry_section = ""
        if retry_context:
            retry_section = f"""
[上一轮审核未通过，请针对以下问题改进]
{retry_context}

请特别注意修正上述问题，确保本轮内容不再出现同样错误。
"""

        prompt = f"""你是一位资深的教育专家，专精于{track.name}领域。请根据以下学习者画像和知识库内容，为该学习者生成一份个性化的学习讲义。
{retry_section}

{track_prompt}

[学习者画像]
- 当前水平: {json.dumps(profile.get('knowledge_points', []), ensure_ascii=False)}
- 知识盲区: {json.dumps(profile.get('blind_spots', []), ensure_ascii=False)}
- 学习风格: {profile.get('learning_style_analysis', '未知')}
- 推荐难度: {difficulty}

[主题]
{topic}

[知识库参考内容]
{context}

{self._source_citation_rules()}

[生成要求]
1. 难度适配学习者当前水平（{difficulty}）
2. 重点覆盖学习者的知识盲区
3. 包含完整的代码/操作示例（用对应的代码块包裹）和操作步骤说明
4. 使用 Markdown 格式，结构清晰
5. 内容不少于 800 字，确保知识点讲解充分

[输出结构]
# {topic}

## 概述
（简要介绍本节内容和学习目标）

## 核心知识点
（逐一讲解，每个知识点附来源引用）

## 代码/操作示例
（完整的示例和操作步骤说明）

## 常见问题
（初学者容易犯的错误和解决方法）

## 总结
（关键要点回顾）

请开始生成讲义："""

        return await self.call_llm(prompt, label="生成讲义")

    async def generate_practical_guide(self, topic: str, profile: dict,
                                       track: Optional[CareerTrackConfig] = None,
                                       retry_context: str = "") -> str:
        """生成实验指导（含知识溯源）"""
        track = track or get_default_career_track()
        context = self.retrieve_context(f"{track.name} {topic} 实践操作")
        track_prompt = build_career_prompt(track)

        retry_section = ""
        if retry_context:
            retry_section = f"""
[上一轮审核未通过，请针对以下问题改进]
{retry_context}

请特别注意修正上述问题，确保本轮内容不再出现同样错误。
"""

        prompt = f"""你是一位资深的实验指导专家，专精于{track.name}领域。请根据以下主题和知识库内容，生成一份实验指导手册。
{retry_section}
{track_prompt}

[主题]
{topic}

[学习者水平]
{profile.get('recommended_difficulty', 'beginner')}

[知识库参考]
{context}

{self._source_citation_rules()}

[要求]
1. 包含实验目标和前置知识
2. 步骤清晰，每步都有操作说明和代码/命令示例（用对应的代码块包裹）
3. 标注常见错误和排查方法
4. 使用 Markdown 格式
5. 内容不少于 600 字

[输出结构]
# {topic} 实验指导

## 实验目标
## 前置知识
## 操作步骤
（每步带代码/命令示例和说明）
## 常见错误与排查
## 思考题

请开始生成实验指导："""

        return await self.call_llm(prompt, label="生成实验指导")

    async def generate_project_case(self, topic: str, profile: dict,
                                    track: Optional[CareerTrackConfig] = None,
                                    retry_context: str = "") -> str:
        """生成项目案例（含知识溯源）"""
        track = track or get_default_career_track()
        context = self.retrieve_context(f"{track.name} {topic} 项目案例 实战")
        track_prompt = build_career_prompt(track)

        retry_section = ""
        if retry_context:
            retry_section = f"""
[上一轮审核未通过，请针对以下问题改进]
{retry_context}

请特别注意修正上述问题，确保本轮内容不再出现同样错误。
"""

        prompt = f"""你是一位资深的项目实战导师，专精于{track.name}领域。请根据以下主题，生成一个端到端的项目案例。
{retry_section}

{track_prompt}

[主题]
{topic}

[学习者水平]
{profile.get('recommended_difficulty', 'beginner')}

[知识库参考]
{context}

{self._source_citation_rules()}

[要求]
1. 项目背景和需求说明
2. 需求分析与方案设计
3. 完整的实现流程和代码/操作示例（带注释，用对应的代码块包裹）
4. 关键步骤的原理和注意事项
5. 结果分析和质量验证要求
6. 使用 Markdown 格式
7. 内容不少于 1000 字

[输出结构]
# {topic} 项目案例

## 项目背景
## 需求分析与方案设计
## 实现步骤
（完整代码/操作示例，每步带说明）
## 质量验证
## 总结与扩展

请开始生成项目案例："""

        return await self.call_llm(prompt, label="生成项目案例")

    async def run(self, topic: str = "", profile: dict = None,
                  resource_types: List[str] = None,
                  track: Optional[CareerTrackConfig] = None,
                  retry_context: str = "", **kwargs) -> dict:
        """执行资源生成（讲义 + 实验指导 + 项目案例）"""
        profile = profile or {}
        resource_types = resource_types or ["lecture", "guide", "project"]
        track = track or get_default_career_track()
        results = {}

        if "lecture" in resource_types:
            results["lecture"] = await self.generate_lecture_notes(topic, profile, track, retry_context)

        if "guide" in resource_types:
            results["guide"] = await self.generate_practical_guide(topic, profile, track, retry_context)

        if "project" in resource_types:
            results["project"] = await self.generate_project_case(topic, profile, track, retry_context)

        return results
