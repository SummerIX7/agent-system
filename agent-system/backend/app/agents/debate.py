import json
from dataclasses import dataclass, field

from app.agents.base import BaseAgent


@dataclass
class DebateResult:
    """辩论结果（不含裁判判决，裁判由独立 Agent 处理）"""
    content_type: str = ""
    original_content: str = ""
    challenge_issues: list = field(default_factory=list)
    challenge_confidence: float = 0
    defend_responses: list = field(default_factory=list)
    revised_content: str = ""
    has_revision: bool = False


class DebateManager(BaseAgent):
    """辩论管理器：管理审核 Agent 与知识生成 Agent 的两轮辩论（不含裁判）"""

    async def challenge(self, content: str, topic: str, content_type: str) -> dict:
        """第1轮：审核 Agent 审查内容，列出问题"""
        context = self.retrieve_context(topic, k=5)

        prompt = f"""你是一位严格的内容审核专家。请审查以下生成内容的专业准确性。

[主题] {topic}
[内容类型] {content_type}
[待审核内容]
{content}

[知识库参考]
{context}

[审核要求]
1. 检查概念定义是否准确
2. 检查代码示例是否可运行
3. 检查是否有编造的 API 或函数
4. 检查是否符合行业规范
5. 【重要】检查来源引用是否真实存在
   - 引用的书名、作者是否真实
   - 引用的 URL 是否有效
   - 引用的章节/页码是否合理
   - 如果发现编造的来源，标记为严重问题

输出 JSON 格式：
{{
    "issues": ["问题1", "问题2"],
    "confidence": 0.85
}}

只输出 JSON，不要其他文字。"""

        response = await self.call_llm(prompt)
        try:
            result = json.loads(response.strip().strip("```json").strip("```"))
        except json.JSONDecodeError:
            result = {"issues": [], "confidence": 0.5}
        return result

    async def defend(self, content: str, topic: str, issues: list) -> dict:
        """第2轮：知识生成 Agent 针对问题反驳或修正（含知识库参照）"""
        # 检索知识库作为辩护依据
        context = self.retrieve_context(topic, k=8)

        prompt = f"""你是一位知识内容生成专家。审核专家对你的内容提出了以下质疑，请逐一反驳或修正。

[主题] {topic}

[参考资料（作为辩护和修正的依据）]
{context if context else "（无可用参考资料，请基于专业知识回应）"}

[原始内容]
{content}

[审核专家的质疑]
{json.dumps(issues, ensure_ascii=False)}

[要求]
1. 对每条质疑，对照参考资料判断其是否成立
2. 质疑不成立：引用参考资料中的证据进行反驳，说明为什么质疑方理解有误
3. 质疑成立：给出修正后的内容，说明修正依据
4. 保持专业性和准确性

输出 JSON 格式：
{{
    "responses": ["对质疑1的回应", "对质疑2的回应"],
    "revised_content": "修正后的完整内容（如有修正）",
    "has_revision": true/false
}}

只输出 JSON，不要其他文字。"""

        response = await self.call_llm(prompt)
        try:
            result = json.loads(response.strip().strip("```json").strip("```"))
        except json.JSONDecodeError:
            result = {"responses": [], "revised_content": content, "has_revision": False}
        return result

    async def run_debate(self, content: str, topic: str, content_type: str) -> DebateResult:
        """执行辩论流程（两轮，不含裁判）"""
        # 第1轮：审核质疑
        challenge_result = await self.challenge(content, topic, content_type)

        # 第2轮：反驳修正
        defend_result = await self.defend(content, topic, challenge_result.get("issues", []))

        # 如果有修正，用修正后的内容
        revised = defend_result.get("revised_content", content) if defend_result.get("has_revision") else content

        return DebateResult(
            content_type=content_type,
            original_content=content,
            challenge_issues=challenge_result.get("issues", []),
            challenge_confidence=challenge_result.get("confidence", 0),
            defend_responses=defend_result.get("responses", []),
            revised_content=revised,
            has_revision=defend_result.get("has_revision", False),
        )

    async def run(self, content: str = "", topic: str = "", content_type: str = "lecture", **kwargs) -> DebateResult:
        return await self.run_debate(content, topic, content_type)
