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
        """双角色辩论式验证（创新点）—— 对照知识库核查，区分问题严重度"""
        # 检索知识库获取参考答案
        context = self.retrieve_context(topic, k=8)

        # 学术审查者视角
        prompt_a = f"""你是一位严格的学术审查者。请**对照参考资料**，审查以下内容的学术准确性。

[参考资料]
{context if context else "（无可用参考资料，请基于常识判断）"}

[待审核内容]
{content}

请逐条核实：概念定义是否正确、理论推导是否严谨、引用来源是否可靠。
仅当你确认某条陈述与参考资料明确矛盾时才标记为问题。不确定或参考资料未覆盖的事项不要列为问题。

输出 JSON 数组，每个问题标注严重度：
[
  {{"issue": "问题描述", "severity": "critical"}},
  {{"issue": "问题描述", "severity": "minor"}},
  {{"issue": "问题描述", "severity": "suggestion"}}
]

severity 取值：
- "critical": 事实性错误、概念定义错误、编造不存在的内容/API/函数
- "minor": 表述不精确、推理不严谨、缺乏引用来源
- "suggestion": 优化建议、风格改进、补充说明建议

如无任何问题，输出空数组 []。"""

        # 工业实践者视角
        prompt_b = f"""你是一位有10年行业经验的实践专家。请**对照参考资料**，审查以下内容的实操可行性。

[参考资料]
{context if context else "（无可用参考资料，请基于常识判断）"}

[待审核内容]
{content}

请逐条核实：操作步骤是否可复现、代码是否可运行、是否符合行业规范。
仅当你确认某条陈述与参考资料明确矛盾或存在实际执行障碍时才标记为问题。不确定的事项不要列为问题。

输出 JSON 数组，每个问题标注严重度：
[
  {{"issue": "问题描述", "severity": "critical"}},
  {{"issue": "问题描述", "severity": "minor"}},
  {{"issue": "问题描述", "severity": "suggestion"}}
]

severity 取值同上。
如无任何问题，输出空数组 []。"""

        # 并行调用两个视角
        response_a = await self.call_llm(prompt_a)
        response_b = await self.call_llm(prompt_b)

        # 增强的 JSON 解析
        issues_a = self._parse_issues(response_a)
        issues_b = self._parse_issues(response_b)

        # 合并并去重，保留最高严重度
        all_issues = self._merge_issues(issues_a, issues_b)

        # 按严重度加权评分
        score = self._severity_weighted_score(all_issues)

        return ReviewResult(
            passed=score >= 0.75,
            score=score,
            issues=[i["issue"] for i in all_issues],
            suggestions=[f"修复({i['severity']}): {i['issue']}" for i in all_issues],
        )

    def _parse_issues(self, response: str) -> list:
        """解析 LLM 返回的问题列表，兼容新旧格式"""
        import re
        cleaned = response.strip()
        # 去除 markdown 代码块
        for prefix in ["```json", "```"]:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

        try:
            result = json.loads(cleaned)
        except json.JSONDecodeError:
            # 尝试正则提取 JSON 数组
            match = re.search(r'\[.*\]', cleaned, re.DOTALL)
            if match:
                try:
                    result = json.loads(match.group(0))
                except json.JSONDecodeError:
                    return []
            else:
                return []

        # 统一格式：兼容旧格式（纯字符串列表）和新格式（对象列表）
        parsed = []
        for item in (result if isinstance(result, list) else []):
            if isinstance(item, str):
                parsed.append({"issue": item, "severity": "minor"})
            elif isinstance(item, dict):
                parsed.append({
                    "issue": item.get("issue", str(item)),
                    "severity": item.get("severity", "minor"),
                })
        return parsed

    def _merge_issues(self, issues_a: list, issues_b: list) -> list:
        """合并两个视角的问题，按内容去重，保留最高严重度"""
        severity_rank = {"critical": 3, "minor": 2, "suggestion": 1}
        merged = {}
        for item in issues_a + issues_b:
            key = item["issue"][:80]  # 用前80字符作为去重键
            if key not in merged or severity_rank.get(item["severity"], 1) > severity_rank.get(merged[key]["severity"], 0):
                merged[key] = item
        return list(merged.values())

    def _severity_weighted_score(self, issues: list) -> float:
        """按问题严重度加权计算评分"""
        if not issues:
            return 1.0
        score = 1.0
        for item in issues:
            sev = item.get("severity", "minor")
            if sev == "critical":
                score -= 0.15
            elif sev == "minor":
                score -= 0.05
            else:  # suggestion
                score -= 0.02
        return max(0, score)

    async def run(self, content: str, topic: str, use_debate: bool = False) -> ReviewResult:
        """执行审核"""
        if use_debate:
            return await self.debate_verify(content, topic)
        return await self.verify(content, topic)
