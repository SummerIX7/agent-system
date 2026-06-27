import json

from app.agents.base import BaseAgent


class QuestionGeneratorAgent(BaseAgent):
    """试题生成 Agent：生成选择题、判断题、实操题"""

    async def generate_questions(self, topic: str, difficulty: str, profile: dict = None, count: int = 6) -> dict:
        """生成三种题型的试题"""
        # 强制使用 CNC 领域关键词检索，避免泛化 topic 导致检索偏移
        context = self.retrieve_context(f"数控编程 CNC 数控加工 {topic}")

        prompt = f"""你是一位数控加工（CNC）领域的出题专家。请根据以下信息生成 {count} 道试题。

【重要】所有题目必须严格围绕"数控加工（CNC）"领域，包括但不限于：
- 数控编程（G 代码、M 代码、坐标系、刀具补偿等）
- 数控车床 / 铣床 / 加工中心的操作与编程
- 切削参数选择（切削速度、进给量、切削深度）
- 刀具选择与工装夹具
- 加工工艺规划与质量控制
- 数控机床安全操作规程
- 材料科学与切削原理

【禁止】不得生成任何与编程语言（Python、Java、C++ 等）、数据分析、机器学习、软件开发相关的题目。

[主题] {topic}
[难度] {difficulty}
[知识库参考] {context}

[要求]
生成以下三种题型，每种至少 2 道：
1. 选择题（multiple_choice）：4 选 1，考察数控知识点
2. 判断题（true_false）：对/错，考察数控概念辨析
3. 实操题（practical）：描述数控加工操作步骤或编程思路（如编写 G 代码片段、描述加工工艺流程等）

输出 JSON 格式：
{{
    "topic": "{topic}",
    "difficulty": "{difficulty}",
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
            "correct_answer": "参考操作步骤或 G 代码",
            "explanation": "评分标准和要点"
        }}
    ]
}}

只输出 JSON，不要其他文字。"""

        response = await self.call_llm(prompt)
        try:
            result = json.loads(response.strip().strip("```json").strip("```"))
        except json.JSONDecodeError:
            result = {"topic": topic, "difficulty": difficulty, "questions": []}
        return result

    async def run(self, topic: str = "", difficulty: str = "beginner", profile: dict = None, **kwargs) -> dict:
        return await self.generate_questions(topic, difficulty, profile)
