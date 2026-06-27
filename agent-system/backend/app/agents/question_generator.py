import json

from app.agents.base import BaseAgent
from app.core.domains import get_domain_from_input, build_domain_prompt


class QuestionGeneratorAgent(BaseAgent):
    """试题生成 Agent：生成选择题、判断题、实操题"""

    async def generate_questions(self, topic: str, difficulty: str, profile: dict = None, count: int = 6) -> dict:
        """生成三种题型的试题"""
        # 从 profile 推断领域配置
        domain = get_domain_from_input(profile or {})

        # 使用领域关键词检索，避免泛化 topic 导致检索偏移
        context = self.retrieve_context(f"{domain.name} {topic}")

        # 构建领域上下文 prompt
        domain_prompt = build_domain_prompt(domain)

        prompt = f"""你是一位{domain.name}领域的出题专家。请根据以下信息生成 {count} 道试题。

{domain_prompt}

[主题] {topic}
[难度] {difficulty}
[知识库参考] {context}

[要求]
生成以下三种题型，每种至少 2 道：
1. 选择题（multiple_choice）：4 选 1，考察领域知识点
2. 判断题（true_false）：对/错，考察领域概念辨析
3. 实操题（practical）：描述领域操作步骤或编程思路

输出 JSON 格式：
{{
    "topic": "{topic}",
    "difficulty": "{difficulty}",
    "domain": "{domain.code}",
    "questions": [
        {{
            "question": "题目内容",
            "question_type": "multiple_choice",
            "options": ["A. 选项1", "B. 选项2", "C. 选项3", "D. 选项4"],
            "correct_answer": "A",
            "explanation": "解析说明"
        }},
        {{
            "question": "判断题内容",
            "question_type": "true_false",
            "options": ["正确", "错误"],
            "correct_answer": "正确",
            "explanation": "解析说明"
        }},
        {{
            "question": "实操题内容",
            "question_type": "practical",
            "options": [],
            "correct_answer": "参考操作步骤",
            "explanation": "评分标准和要点"
        }}
    ]
}}

只输出 JSON，不要其他文字。"""

        response = await self.call_llm(prompt)
        try:
            result = json.loads(response.strip().strip("```json").strip("```"))
            result["domain"] = result.get("domain", domain.code)
        except json.JSONDecodeError:
            result = {"topic": topic, "difficulty": difficulty, "domain": domain.code, "questions": []}
        return result

    async def run(self, topic: str = "", difficulty: str = "beginner", profile: dict = None, **kwargs) -> dict:
        return await self.generate_questions(topic, difficulty, profile)
