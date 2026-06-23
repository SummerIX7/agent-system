import json
from typing import List

from app.agents.base import BaseAgent


class GenerationAgent(BaseAgent):
    """知识生成 Agent：生成讲义、实验指导、项目案例（含知识溯源）"""

    def _source_citation_rules(self) -> str:
        """来源引用规则"""
        return """
[来源引用规则 — 必须遵守]
1. 每个知识点必须标注来源，格式如下：

   [知识点：XXX]
   📚 来源：《书名》(作者, 年份) 章节
   🔗 链接：URL（如有）
   权威度：★★★★★

2. 来源信息从知识库参考内容中提取，不要编造
3. 如果知识库中没有相关信息，标注"[需人工确认来源]"
4. 禁止编造不存在的书名、论文或 URL
5. 多个知识点可引用同一来源，但每个知识点必须单独标注"""

    async def generate_lecture_notes(self, topic: str, profile: dict) -> str:
        """生成定制化讲义（含知识溯源）"""
        context = self.retrieve_context(topic)
        difficulty = profile.get("recommended_difficulty", "beginner")

        prompt = f"""你是一位资深的教育专家。请根据以下学习者画像和知识库内容，为该学习者生成一份个性化的学习讲义。

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
3. 包含实际可运行的代码示例
4. 使用 Markdown 格式

请开始生成讲义："""

        return await self.call_llm(prompt)

    async def generate_practical_guide(self, topic: str, profile: dict) -> str:
        """生成实验指导（含知识溯源）"""
        context = self.retrieve_context(f"{topic} 实践操作")

        prompt = f"""你是一位资深的实验指导专家。请根据以下主题和知识库内容，生成一份实验指导手册。

[主题]
{topic}

[学习者水平]
{profile.get('recommended_difficulty', 'beginner')}

[知识库参考]
{context}

{self._source_citation_rules()}

[要求]
1. 包含实验目标和前置知识
2. 步骤清晰，每步都有代码示例
3. 标注常见错误和排查方法
4. 使用 Markdown 格式

请开始生成实验指导："""

        return await self.call_llm(prompt)

    async def generate_project_case(self, topic: str, profile: dict) -> str:
        """生成项目案例（含知识溯源）"""
        context = self.retrieve_context(f"{topic} 项目案例 实战")

        prompt = f"""你是一位资深的项目实战导师。请根据以下主题，生成一个端到端的项目案例。

[主题]
{topic}

[学习者水平]
{profile.get('recommended_difficulty', 'beginner')}

[知识库参考]
{context}

{self._source_citation_rules()}

[要求]
1. 项目背景和需求说明
2. 数据来源和准备
3. 完整的实现代码（带注释）
4. 关键步骤的原理解释
5. 结果分析和可视化
6. 使用 Markdown 格式

请开始生成项目案例："""

        return await self.call_llm(prompt)

    async def run(self, topic: str = "", profile: dict = None, resource_types: List[str] = None, **kwargs) -> dict:
        """执行资源生成（讲义 + 实验指导 + 项目案例）"""
        profile = profile or {}
        resource_types = resource_types or ["lecture", "guide", "project"]
        results = {}

        if "lecture" in resource_types:
            results["lecture"] = await self.generate_lecture_notes(topic, profile)

        if "guide" in resource_types:
            results["guide"] = await self.generate_practical_guide(topic, profile)

        if "project" in resource_types:
            results["project"] = await self.generate_project_case(topic, profile)

        return results
