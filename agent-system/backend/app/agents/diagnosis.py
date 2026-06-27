import json
from typing import Dict, List

from app.agents.base import BaseAgent
from app.core.domains import get_domain_from_input, build_domain_prompt


class DiagnosisAgent(BaseAgent):
    """学情诊断 Agent：构建学习者画像，定位知识盲区，匹配难度"""

    async def build_profile(self, input_data: dict) -> dict:
        """根据输入数据构建学习者画像"""
        # 从输入数据推断领域配置
        domain = get_domain_from_input(input_data)

        context = self.retrieve_context(
            f"{domain.name} 学习者画像 {input_data.get('major', '')} {input_data.get('education_background', '')}"
        )

        # 构建领域上下文 prompt
        domain_prompt = build_domain_prompt(domain)

        prompt = f"""你是一位{domain.name}领域的教育诊断专家。请根据以下学习者信息，构建详细的学习者画像。

{domain_prompt}

[学习者输入信息]
- 学历背景: {input_data.get('education_background', '未知')}
- 专业方向: {input_data.get('major', '未知')}
- 工作经验: {input_data.get('work_experience_years', 0)} 年
- 技能自评: {json.dumps(input_data.get('self_assessment', {}), ensure_ascii=False)}
- 学习风格: {input_data.get('learning_style', '未知')}
- 学习目标: {json.dumps(input_data.get('goals', []), ensure_ascii=False)}

[知识库参考]
{context}

[难度判定标准]
- beginner：零基础，非相关专业背景，从未接触过该领域
- intermediate：有相关基础（如相关专业背景或工作经验），但该领域经验较少
- advanced：有丰富的领域经验（3年以上），能独立完成复杂任务
- expert：领域专家，5年以上经验，精通高级技术和优化

注意：如果学习者有相关领域基础，即使当前领域技能较弱，也应判定为 intermediate，因为相关基础意味着更容易理解核心概念。

请输出 JSON 格式的画像，包含以下字段：
{{
    "knowledge_points": [
        {{"name": "知识点名称", "level": "beginner/intermediate/advanced/expert", "score": 0-100, "confidence": 0-1}}
    ],
    "blind_spots": ["知识盲区1", "知识盲区2"],
    "overall_level": "beginner/intermediate/advanced/expert",
    "learning_style_analysis": "学习风格分析",
    "recommended_difficulty": "beginner/intermediate/advanced/expert",
    "domain": "{domain.code}"
}}

只输出 JSON，不要其他文字。"""

        response = await self.call_llm(prompt)
        try:
            profile = json.loads(response.strip().strip("```json").strip("```"))
            # 确保 domain 字段被设置
            profile["domain"] = profile.get("domain", domain.code)
        except json.JSONDecodeError:
            profile = {
                "knowledge_points": [],
                "blind_spots": [],
                "overall_level": "beginner",
                "learning_style_analysis": "暂无分析",
                "recommended_difficulty": "beginner",
                "domain": domain.code,
            }
        return profile

    async def locate_blind_spots(self, profile: dict, knowledge_map: List[str]) -> List[str]:
        """定位知识盲区"""
        prompt = f"""根据以下学习者画像和知识点列表，找出学习者的知识盲区。

[学习者画像]
{json.dumps(profile, ensure_ascii=False, indent=2)}

[知识点列表]
{json.dumps(knowledge_map, ensure_ascii=False)}

请输出一个 JSON 数组，列出学习者可能存在的知识盲区。
只输出 JSON 数组，不要其他文字。"""

        response = await self.call_llm(prompt)
        try:
            blind_spots = json.loads(response.strip().strip("```json").strip("```"))
        except json.JSONDecodeError:
            blind_spots = []
        return blind_spots

    async def match_difficulty(self, profile: dict) -> str:
        """匹配适当的资源难度等级"""
        level = profile.get("recommended_difficulty", profile.get("overall_level", "beginner"))
        return level

    async def run(self, input_data: dict) -> dict:
        """执行完整诊断流程"""
        profile = await self.build_profile(input_data)
        difficulty = await self.match_difficulty(profile)
        return {
            "profile": profile,
            "difficulty": difficulty,
        }
