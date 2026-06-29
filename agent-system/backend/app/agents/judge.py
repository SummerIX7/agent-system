import json
import logging
import re

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class JudgeAgent(BaseAgent):
    """独立裁判 Agent：不参与辩论，只根据双方论据做最终判决"""

    def _robust_json_parse(self, response: str, default: dict) -> dict:
        """增强的 JSON 解析：正则提取 + 文本推断降级"""
        cleaned = response.strip()

        # 1. 去除 markdown 代码块
        for prefix in ["```json", "```"]:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

        # 2. 尝试直接解析
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # 3. 正则提取第一个完整 JSON 对象
        json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # 4. 降级：从文本推断
        logger.warning(f"JSON 解析失败，尝试文本推断。原始响应前300字: {response[:300]}")
        text_lower = response.lower()
        if "passed" in text_lower:
            if '"passed": true' in text_lower or '"passed":true' in text_lower or \
               "'passed': true" in text_lower or "'passed':true" in text_lower:
                default["passed"] = True
        if "通过" in response and "未通过" not in response:
            default["passed"] = True

        return default

    async def judge(self, original_content: str, topic: str, content_type: str,
                    challenge_issues: list, defend_responses: list, revised_content: str) -> dict:
        """综合辩论双方的论据，做出最终判决"""

        prompt = f"""你是一位中立、公正的裁判。以下是关于一份学习内容的辩论记录，请做出最终判决。

[主题] {topic}
[内容类型] {content_type}

[原始内容]
{original_content}

[审核方（质疑方）提出的问题]
{json.dumps(challenge_issues, ensure_ascii=False)}

[生成方（辩护方）的回应]
{json.dumps(defend_responses, ensure_ascii=False)}

[修正后的内容]
{revised_content}

注：如内容较长，请聚焦核心概念准确性、逻辑自洽性和实践可行性，无需逐字审查。

[判决要求]
1. 逐一评估审核方提出的每个问题是否有效
   - 问题是否有知识库/事实依据？
   - 问题是否是实质性错误（而非风格偏好）？
2. 评估辩护方的每个回应是否有力
   - 回应是否有理有据？
   - 修正是否解决了问题？
3. 综合判断最终内容是否准确可用

[重要原则]
- 如果审核方的问题是主观偏好而非事实错误，应判为无效
- 如果辩护方引用了知识库依据进行反驳，应认可其合理性
- 只有实质性错误（概念错误、代码不可运行、编造API）才应导致不通过

输出 JSON 格式：
{{
    "passed": true/false,
    "adopted_side": "defender"/"challenger",
    "reason": "详细判决理由",
    "quality_score": 0-1,
    "effective_issues": ["审核方提出的有效问题列表"],
    "overruled_issues": ["被驳回的无效问题列表"]
}}

只输出 JSON，不要其他文字。"""

        response = await self.call_llm(prompt)
        result = self._robust_json_parse(response, {
            "passed": False,
            "adopted_side": "challenger",
            "reason": "裁判响应无法解析，且无法从文本推断结果",
            "quality_score": 0,
            "effective_issues": challenge_issues,
            "overruled_issues": [],
        })
        # 确保必要字段存在
        result.setdefault("effective_issues", challenge_issues)
        result.setdefault("overruled_issues", [])

        # P1-2: 回归验证 — 判决通过且有修正时，验证修正是否真正解决了问题
        if result.get("passed") and revised_content != original_content:
            try:
                regress_result = await self._regression_check(
                    revised_content,
                    result.get("effective_issues", []),
                    topic
                )
                if not regress_result.get("verified", False):
                    result["passed"] = False
                    result["reason"] += f"\n修正回归验证未通过：{regress_result.get('reason', '未知原因')}"
                    result["regression_failure"] = regress_result
                    logger.info(f"裁判回归验证未通过: {regress_result.get('reason')}")
            except Exception as e:
                logger.warning(f"回归验证过程出错: {e}")
                # 回归验证出错不影响原判决

        return result

    async def _regression_check(self, content: str, fixed_issues: list, topic: str) -> dict:
        """
        验证修正是否真正解决了问题。
        对每个 effective_issue 对应的内容段落进行 RAG 检索比对。

        Args:
            content: 修正后的内容
            fixed_issues: 声称已修复的问题列表
            topic: 内容主题

        Returns:
            verified: bool 是否验证通过
            checks: list 每个问题的验证详情
            reason: str 验证失败原因
        """
        if not fixed_issues:
            return {"verified": True, "checks": [], "reason": "无需验证的问题"}

        context = self.retrieve_context(topic, k=5)

        prompt = f"""以下是修正后的内容。请验证之前发现的问题是否已被正确修复。

[修正后的内容]
{content[:2000]}

[之前发现并声称已修复的问题]
{json.dumps(fixed_issues, ensure_ascii=False)}

[知识库参考]
{context[:1500]}

[验证要求]
1. 逐条判断每个问题是否确实被修复
2. 对照知识库验证修正后的内容是否准确
3. 如果某个问题未被修复或修复后引入新错误，标记为 verified=False

以 JSON 返回：
{{
    "verified": true/false,
    "checks": [
        {{"issue": "问题描述", "fixed": true/false, "reason": "判定理由"}}
    ],
    "reason": "整体验证结论"
}}

只输出 JSON，不要其他文字。"""

        response = await self.call_llm(prompt)

        result = self._robust_json_parse(response, {
            "verified": False,
            "checks": [],
            "reason": "回归验证响应解析失败",
        })
        return {
            "verified": result.get("verified", False),
            "checks": result.get("checks", []),
            "reason": result.get("reason", "回归验证响应解析失败"),
        }

    async def run(self, original_content: str = "", topic: str = "", content_type: str = "",
                  challenge_issues: list = None, defend_responses: list = None,
                  revised_content: str = "", **kwargs) -> dict:
        return await self.judge(
            original_content, topic, content_type,
            challenge_issues or [], defend_responses or [], revised_content
        )
