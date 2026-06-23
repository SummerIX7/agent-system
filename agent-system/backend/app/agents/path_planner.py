import json

from app.agents.base import BaseAgent


class PathPlannerAgent(BaseAgent):
    """路径规划 Agent：根据学情分析生成个性化学习路径"""

    async def plan_path(self, profile: dict, topic: str) -> dict:
        """生成学习路径"""
        prompt = f"""你是一位教育路径规划专家。根据以下学习者画像，为其制定个性化的学习路径。

[学习者画像]
- 专业方向: {profile.get('major', '未知')}
- 当前水平: {profile.get('overall_level', 'beginner')}
- 知识点评分: {json.dumps(profile.get('knowledge_points', []), ensure_ascii=False)}
- 知识盲区: {json.dumps(profile.get('blind_spots', []), ensure_ascii=False)}
- 学习目标: {json.dumps(profile.get('goals', []), ensure_ascii=False)}
- 学习风格: {profile.get('learning_style', 'practice')}

[当前主题]
{topic}

请生成学习路径，输出 JSON 格式：
{{
    "path": [
        {{
            "stage": 1,
            "title": "阶段名称",
            "topics": ["知识点1", "知识点2"],
            "estimated_hours": 8,
            "difficulty": "beginner",
            "prerequisites": [],
            "resources_type": ["lecture", "guide", "project"]
        }}
    ],
    "total_estimated_hours": 40,
    "current_stage": 1,
    "recommended_order": "按阶段顺序学习"
}}

要求：
1. 根据知识盲区优先安排薄弱环节
2. 阶段之间有明确的依赖关系
3. 每个阶段估算学习时长
4. 推荐适合的资源类型

只输出 JSON，不要其他文字。"""

        response = await self.call_llm(prompt)
        try:
            path = json.loads(response.strip().strip("```json").strip("```"))
        except json.JSONDecodeError:
            path = {
                "path": [{"stage": 1, "title": topic, "topics": [topic], "estimated_hours": 4, "difficulty": "beginner", "prerequisites": [], "resources_type": ["lecture", "guide"]}],
                "total_estimated_hours": 4,
                "current_stage": 1,
            }
        return path

    async def adjust_path(self, path: dict, feedback: dict) -> dict:
        """根据用户反馈调整学习路径"""
        correctness = feedback.get("correctness", 0)
        current_stage = path.get("current_stage", 1)

        if correctness < 0.6:
            # 降低难度，补充基础
            prompt = f"""学习者在阶段 {correctness:.0%} 正确率较低，请调整学习路径：
1. 在当前阶段前插入基础知识补充阶段
2. 降低当前阶段难度

当前路径：{json.dumps(path, ensure_ascii=False)}

输出调整后的 JSON 路径。只输出 JSON。"""
        elif correctness > 0.9:
            # 跳过已掌握内容
            prompt = f"""学习者正确率 {correctness:.0%}，掌握良好，请调整学习路径：
1. 当前阶段标记为已完成
2. 跳过基础内容，直接进入进阶

当前路径：{json.dumps(path, ensure_ascii=False)}

输出调整后的 JSON 路径。只输出 JSON。"""
        else:
            return path  # 无需调整

        response = await self.call_llm(prompt)
        try:
            adjusted = json.loads(response.strip().strip("```json").strip("```"))
        except json.JSONDecodeError:
            adjusted = path
        return adjusted

    async def run(self, profile: dict = None, topic: str = "", path: dict = None, feedback: dict = None, **kwargs) -> dict:
        if path and feedback:
            return await self.adjust_path(path, feedback)
        return await self.plan_path(profile or {}, topic)
