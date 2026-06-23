import json
from dataclasses import dataclass, field

from app.agents.base import BaseAgent


@dataclass
class ReviewResult:
    """审核结果"""
    passed: bool = False
    score: float = 0.0
    issues: list = field(default_factory=list)
    suggestions: list = field(default_factory=list)


class ReviewAgent(BaseAgent):
    """内容审核纠偏 Agent：交叉验证生成内容的专业准确性"""

    async def verify(self, content: str, topic: str) -> ReviewResult:
        """交叉验证生成内容的专业准确性"""
        ground_truth = self.retrieve_context(topic, k=10)

        prompt = f"""你是一位严格的内容审核专家。请审查以下生成内容的专业准确性。

[主题]
{topic}

[待审核内容]
{content}

[知识库参考（作为事实依据）]
{ground_truth}

[审核要求]
1. 逐条核验事实准确性
2. 检查是否有编造的 API、函数或概念
3. 检查代码示例是否可运行
4. 检查是否符合行业规范

请输出 JSON 格式的审核结果：
{{
    "score": 0-1（准确度评分）,
    "issues": ["问题1", "问题2"],
    "suggestions": ["建议1", "建议2"]
}}

只输出 JSON，不要其他文字。"""

        response = await self.call_llm(prompt)
        try:
            result = json.loads(response.strip().strip("```json").strip("```"))
        except json.JSONDecodeError:
            result = {"score": 0.5, "issues": ["审核解析失败"], "suggestions": ["建议人工审核"]}

        return ReviewResult(
            passed=result.get("score", 0) >= 0.85,
            score=result.get("score", 0),
            issues=result.get("issues", []),
            suggestions=result.get("suggestions", []),
        )

    async def debate_verify(self, content: str, topic: str) -> ReviewResult:
        """双角色辩论式验证（创新点）"""
        # 学术审查者视角
        prompt_a = f"""你是一位严格的学术审查者。请审查以下内容的学术准确性：
1. 概念定义是否正确
2. 理论推导是否严谨
3. 引用来源是否可靠

[待审核内容]
{content}

发现任何问题请列出，用 JSON 数组格式输出。如无问题输出空数组 []。"""

        # 工业实践者视角
        prompt_b = f"""你是一位有10年行业经验的实践专家。请审查以下内容的实操可行性：
1. 操作步骤是否可以在真实环境中复现
2. 代码是否可运行
3. 是否符合行业规范

[待审核内容]
{content}

发现任何问题请列出，用 JSON 数组格式输出。如无问题输出空数组 []。"""

        # 并行调用两个视角
        response_a = await self.call_llm(prompt_a)
        response_b = await self.call_llm(prompt_b)

        try:
            issues_a = json.loads(response_a.strip().strip("```json").strip("```"))
        except json.JSONDecodeError:
            issues_a = ["学术审查解析失败"]

        try:
            issues_b = json.loads(response_b.strip().strip("```json").strip("```"))
        except json.JSONDecodeError:
            issues_b = ["实践审查解析失败"]

        # 取并集
        all_issues = list(set(issues_a + issues_b))
        score = max(0, 1 - len(all_issues) * 0.1)

        return ReviewResult(
            passed=score >= 0.85,
            score=score,
            issues=all_issues,
            suggestions=[f"修复: {issue}" for issue in all_issues],
        )

    async def run(self, content: str, topic: str, use_debate: bool = False) -> ReviewResult:
        """执行审核"""
        if use_debate:
            return await self.debate_verify(content, topic)
        return await self.verify(content, topic)
