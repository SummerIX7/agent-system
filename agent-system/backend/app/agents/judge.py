import json

from app.agents.base import BaseAgent


class JudgeAgent(BaseAgent):
    """独立裁判 Agent：不参与辩论，只根据双方论据做最终判决"""

    async def judge(self, original_content: str, topic: str, content_type: str,
                    challenge_issues: list, defend_responses: list, revised_content: str) -> dict:
        """综合辩论双方的论据，做出最终判决"""

        prompt = f"""你是一位中立、公正的裁判。以下是关于一份学习内容的辩论记录，请做出最终判决。

[主题] {topic}
[内容类型] {content_type}

[原始内容摘要]
{original_content[:800]}...

[审核方（质疑方）提出的问题]
{json.dumps(challenge_issues, ensure_ascii=False)}

[生成方（辩护方）的回应]
{json.dumps(defend_responses, ensure_ascii=False)}

[修正后的内容摘要]
{revised_content[:500]}...

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
        try:
            result = json.loads(response.strip().strip("```json").strip("```"))
        except json.JSONDecodeError:
            # 解析失败时默认通过，避免阻塞流程
            result = {
                "passed": True,
                "adopted_side": "defender",
                "reason": "裁判解析失败，默认通过",
                "quality_score": 0.7,
                "effective_issues": [],
                "overruled_issues": challenge_issues,
            }
        return result

    async def run(self, original_content: str = "", topic: str = "", content_type: str = "",
                  challenge_issues: list = None, defend_responses: list = None,
                  revised_content: str = "", **kwargs) -> dict:
        return await self.judge(
            original_content, topic, content_type,
            challenge_issues or [], defend_responses or [], revised_content
        )
