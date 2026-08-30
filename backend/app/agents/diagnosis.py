import json
from typing import Dict, List

from app.agents.base import BaseAgent
from app.core.career_tracks import get_career_track_from_input, build_career_prompt


def _align_kps_to_skills(kps: list, required_skills: List[str]) -> list:
    """
    将 LLM 输出的 knowledge_points 强制对齐到 required_skills 列表。

    - 维度名必须且只能取自 required_skills
    - 命中的项保留其 score/level/confidence；缺失的项补零分占位
    - 顺序按 required_skills 排列，保证雷达图维度稳定
    """
    if not required_skills:
        return list(kps or [])

    # 归一化 key 用于模糊匹配（去空格、转小写、统一括号）
    def _norm(s: str) -> str:
        return (s or "").lower().replace(" ", "").replace("（", "(").replace("）", ")")

    norm_required = [_norm(s) for s in required_skills]

    # 构建 name -> kp 索引（用归一化 key）
    kp_by_norm = {}
    for kp in (kps or []):
        if not isinstance(kp, dict):
            continue
        name = kp.get("name", "")
        kp_by_norm[_norm(name)] = kp

    aligned = []
    for raw_skill, norm_skill in zip(required_skills, norm_required):
        # 精确归一化匹配，或子串包含
        matched_kp = kp_by_norm.get(norm_skill)
        if matched_kp is None:
            # 退而求其次：子串包含匹配
            for nk, kp in kp_by_norm.items():
                if norm_skill and (norm_skill in nk or nk in norm_skill):
                    matched_kp = kp
                    break
        if matched_kp is not None:
            aligned.append({
                "name": raw_skill,  # 统一用 required_skills 中的标准名
                "level": matched_kp.get("level", "beginner"),
                "score": float(matched_kp.get("score", 0) or 0),
                "confidence": float(matched_kp.get("confidence", 0.5) or 0.5),
            })
        else:
            aligned.append({
                "name": raw_skill,
                "level": "beginner",
                "score": 0.0,
                "confidence": 0.3,
            })
    return aligned


def _merge_kps(llm_kps: list, existing_kps: list) -> list:
    """
    用 LLM 重新评估的 score/level/confidence 更新 existing_kps，name 保持不变。

    - name 命中的项：用 LLM 的 score/level/confidence（反映学习成长）
    - name 未命中的项：保留原值（不会因 LLM 漏掉而归零）
    - 顺序按 existing_kps 排列，保证雷达图维度稳定
    """
    if not existing_kps:
        return list(llm_kps or [])

    def _norm(s: str) -> str:
        return (s or "").lower().replace(" ", "").replace("（", "(").replace("）", ")")

    # 建立 LLM name → kp 索引
    llm_by_norm = {}
    for kp in (llm_kps or []):
        if isinstance(kp, dict):
            llm_by_norm[_norm(kp.get("name", ""))] = kp

    merged = []
    for kp in existing_kps:
        name = kp.get("name", "")
        norm_name = _norm(name)
        # 精确匹配
        llm_kp = llm_by_norm.get(norm_name)
        if llm_kp is None:
            # 模糊匹配
            for nk, lkp in llm_by_norm.items():
                if norm_name and (norm_name in nk or nk in norm_name):
                    llm_kp = lkp
                    break
        if llm_kp is not None:
            # LLM 有对应项：用 LLM 的 score/level/confidence
            score = llm_kp.get("score", 0)
            try:
                score = max(0.0, min(100.0, float(score)))
            except (TypeError, ValueError):
                score = 0.0
            merged.append({
                "name": name,  # 保持原名
                "score": score,
                "level": llm_kp.get("level", kp.get("level", "beginner")),
                "confidence": max(0.0, min(1.0, float(llm_kp.get("confidence", 0.5) or 0.5))),
            })
        else:
            # LLM 没有对应项：保留原值
            merged.append(dict(kp))
    return merged


class DiagnosisAgent(BaseAgent):
    """学情诊断 Agent：构建学习者画像，定位知识盲区，匹配难度"""

    async def build_profile(self, input_data: dict) -> dict:
        """根据输入数据构建学习者画像"""
        # 从输入数据推断职业方向配置
        track = get_career_track_from_input(input_data)

        context = self.retrieve_context(
            f"{track.name} {input_data.get('major', '')} {input_data.get('education_background', '')}"
        )

        # 构建职业方向上下文 prompt
        track_prompt = build_career_prompt(track)

        # 雷达图维度锚点：必须且只能输出这些知识点 name（取自所选职业方向的技能自评项）
        required_skills = list(track.self_assessment_skills)
        required_skills_json = json.dumps(required_skills, ensure_ascii=False)

        # 构建 learning_context 段落（仅 reassess 时提供，首次诊断无）
        learning_context = input_data.get("learning_context") or {}
        learning_context_str = ""
        if learning_context:
            completed = learning_context.get("completed_nodes", [])
            practice = learning_context.get("practice_summary", [])
            kg_pct = learning_context.get("kg_mastery_percentage", 0)
            current_kps = learning_context.get("updated_knowledge_points", [])
            learning_context_str = f"""
[学习数据]（重新评估时提供，基于客观学习数据更新评分）
- 已完成节点: {', '.join(completed) if completed else '无'}
- 总节点数: {learning_context.get('total_nodes', 0)}
- 练习成绩汇总: {json.dumps(practice, ensure_ascii=False)}
- 知识图谱掌握度: {kg_pct}%
- 当前知识点评分: {json.dumps(current_kps, ensure_ascii=False)}

重要：以上学习数据反映了学习者的实际学习成果。请基于这些数据重新评估各知识点的 score/level/confidence，反映学习者的成长。完成学习并练习达标的技能应提升 score，未涉及或未练习的技能保留原水平。score 应基于客观数据而非主观猜测。
"""

        prompt = f"""你是一位 CNC 数控加工领域的教育诊断专家，专精于 {track.name} 方向。请根据以下学习者信息，构建详细的学习者画像。

{track_prompt}

[学习者输入信息]
- 学历背景: {input_data.get('education_background', '未知')}
- 专业方向: {input_data.get('major', '未知')}
- 工作经验: {input_data.get('work_experience_years', 0)} 年
- 职业方向: {track.name}（{track.description}）
- 用户自评当前水平: {input_data.get('current_level', '未提供')}
- 技能自评: {json.dumps(input_data.get('self_assessment', {}), ensure_ascii=False)}
- 学习风格: {input_data.get('learning_style', '未知')}
- 学习目标: {json.dumps(input_data.get('goals', []), ensure_ascii=False)}
{learning_context_str}
[前置知识要求]
{track.prerequisite_knowledge}

[知识库参考]
{context}

[难度判定标准]
- beginner：零基础，无相关专业背景，从未接触过 {track.name} 相关技能
- intermediate：有相关基础（如相关专业背景或简单操作经验），但 {track.name} 核心技能较弱
- advanced：有丰富的 {track.name} 经验（3年以上），能独立完成核心工作
- expert：{track.name} 领域专家，5年以上经验，精通所有技能并能指导他人

注意：如果学习者有相关职业经验或来自更低层级职业方向，应据此提高判定等级。例如调机工需要操机工基础，编程师需要调机工基础。

[知识点维度硬约束 - 必须严格遵守]
knowledge_points 数组的 name 字段必须且只能从以下列表中取值，顺序可任意，但数量必须等于列表长度（{len(required_skills)} 项），不得增删、不得改名、不得合并或拆分：
{required_skills_json}

请输出 JSON 格式的画像，包含以下字段：
{{
    "knowledge_points": [
        {{"name": "<必须等于上述列表中的某一项>", "level": "beginner/intermediate/advanced/expert", "score": 0-100, "confidence": 0-1}}
    ],
    "blind_spots": ["知识盲区1", "知识盲区2"],
    "overall_level": "beginner/intermediate/advanced/expert",
    "learning_style_analysis": "学习风格分析",
    "recommended_difficulty": "beginner/intermediate/advanced/expert",
    "career_track": "{track.code}",
    "career_track_name": "{track.name}"
}}

只输出 JSON，不要其他文字。"""

        response = await self.call_llm(prompt)
        try:
            profile = json.loads(response.strip().strip("```json").strip("```"))
            # 确保必要字段被设置
            profile["career_track"] = profile.get("career_track", track.code)
            profile["career_track_name"] = profile.get("career_track_name", track.name)
            # 维度兜底对齐：即使 LLM 没遵守硬约束，也强制 knowledge_points 维度 = 所选方向技能列表
            profile["knowledge_points"] = _align_kps_to_skills(
                profile.get("knowledge_points", []), required_skills
            )
        except json.JSONDecodeError:
            profile = {
                # 解析失败时直接用方向技能列表生成零分占位，保证雷达图维度正确
                "knowledge_points": [
                    {"name": s, "level": "beginner", "score": 0, "confidence": 0.3}
                    for s in required_skills
                ],
                "blind_spots": [],
                "overall_level": "beginner",
                "learning_style_analysis": "暂无分析",
                "recommended_difficulty": "beginner",
                "career_track": track.code,
                "career_track_name": track.name,
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
