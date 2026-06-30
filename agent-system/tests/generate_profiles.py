"""
批量生成 50+ 组差异化学习者画像（用于竞赛测试数据提交）。

生成策略：
- 2 个领域 × 4 个难度 × 多种学历 × 多种专业 = 50+ 组合
- 每个画像包含完整的输入输出字段
- 输出到 tests/test_data/learner_profiles_bulk/ 目录
"""

import json
import random
import os
from pathlib import Path

# 输出目录
OUTPUT_DIR = Path(__file__).parent / "learner_profiles_bulk"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── 参数池 ──

DOMAINS = [
    {
        "code": "cnc",
        "name": "CNC 数控加工",
        "core_topics": ["数控编程", "G代码", "切削参数", "刀具管理", "加工工艺"],
        "skills": [
            "机械制图基础", "G 代码编程", "数控车床操作",
            "数控铣床操作", "CAM 软件应用", "刀具选择与管理",
            "切削参数优化", "测量与检测",
        ],
    },
    {
        "code": "python_data_analysis",
        "name": "Python 数据分析",
        "core_topics": ["Python基础", "NumPy", "Pandas", "数据可视化", "数据清洗"],
        "skills": [
            "Python基础语法", "NumPy数组操作", "Pandas数据处理",
            "Matplotlib绘图", "Seaborn可视化", "数据清洗与预处理",
            "统计分析基础", "Jupyter Notebook使用",
        ],
    },
]

EDUCATION_LEVELS = [
    {"bg": "高中", "label": "high_school"},
    {"bg": "大专", "label": "associate"},
    {"bg": "本科", "label": "bachelor"},
    {"bg": "硕士", "label": "master"},
    {"bg": "博士", "label": "doctor"},
]

# 与领域相关的专业
RELATED_MAJORS_BY_DOMAIN = {
    "cnc": [
        "机械工程", "机械设计制造及其自动化", "材料成型及控制工程",
        "车辆工程", "机电一体化", "模具设计与制造", "数控技术",
        "智能制造工程", "工业工程", "自动化",
    ],
    "python_data_analysis": [
        "计算机科学与技术", "软件工程", "数据科学", "统计学",
        "信息管理与信息系统", "数学与应用数学", "金融工程",
        "人工智能", "电子信息工程", "电子商务",
    ],
}

# 与领域无关的专业
UNRELATED_MAJORS = [
    "英语", "会计学", "市场营销", "人力资源管理", "法学",
    "汉语言文学", "历史学", "行政管理", "旅游管理", "艺术设计",
    "社会工作", "新闻学", "哲学", "国际经济与贸易",
]

EXPERIENCE_YEARS = [0, 0.5, 1, 2, 3, 5, 8, 10, 15]
LEARNING_STYLES = ["practice", "theory", "visual"]
GOAL_TEMPLATES = {
    "beginner": [
        "了解{domain_name}基础概念",
        "掌握{domain_name}入门知识",
        "学习{domain_name}基本操作",
    ],
    "intermediate": [
        "提升{domain_name}实践技能",
        "系统学习{domain_name}核心内容",
        "掌握{domain_name}常用技术",
    ],
    "advanced": [
        "精通{domain_name}高级技术",
        "学习{domain_name}优化方法",
        "掌握{domain_name}复杂场景应用",
    ],
    "expert": [
        "研究{domain_name}前沿技术",
        "掌握{domain_name}系统级优化",
        "成为{domain_name}领域专家",
    ],
}

SELF_ASSESSMENT_LEVELS = ["不了解", "了解基础", "熟练", "精通"]


def generate_profile(profile_id: int, domain: dict, difficulty: str,
                     education: dict, major: str, is_related: bool,
                     experience: float, learning_style: str) -> dict:
    """生成单个学习者画像"""

    # 根据难度级别设置技能自评
    if difficulty == "beginner":
        skill_weights = [0.80, 0.15, 0.04, 0.01]  # 大部分"不了解"
    elif difficulty == "intermediate":
        skill_weights = [0.30, 0.50, 0.15, 0.05]
    elif difficulty == "advanced":
        skill_weights = [0.05, 0.15, 0.60, 0.20]
    else:  # expert
        skill_weights = [0.01, 0.04, 0.35, 0.60]

    self_assessment = {}
    for skill in domain["skills"]:
        level = random.choices(SELF_ASSESSMENT_LEVELS, weights=skill_weights, k=1)[0]
        self_assessment[skill] = level

    # 生成学习目标
    goal_template = random.choice(GOAL_TEMPLATES[difficulty])
    goals = [goal_template.format(domain_name=domain["name"])]
    # 50% 概率添加第二个目标
    if random.random() > 0.5:
        extra = random.choice(GOAL_TEMPLATES[difficulty])
        if extra != goal_template:
            goals.append(extra.format(domain_name=domain["name"]))

    profile_name = (
        f"{'相关' if is_related else '非相关'}专业-"
        f"{education['bg']}-"
        f"{difficulty}-"
        f"#{profile_id:03d}"
    )

    return {
        "profile_name": profile_name,
        "domain": domain["code"],
        "domain_name": domain["name"],
        "education_background": education["bg"],
        "education_label": education["label"],
        "major": major,
        "major_related": is_related,
        "work_experience_years": experience,
        "learning_style": learning_style,
        "self_assessment": self_assessment,
        "goals": goals,
        "expected_difficulty": difficulty,
        "expected_level": difficulty,
        "expected_knowledge_score_range": {
            "beginner": [5, 30],
            "intermediate": [30, 60],
            "advanced": [60, 85],
            "expert": [85, 100],
        }[difficulty],
        "profile_id": profile_id,
    }


def main():
    random.seed(42)  # 确定性生成，便于复现
    profiles = []
    profile_id = 0

    for domain in DOMAINS:
        related_majors = RELATED_MAJORS_BY_DOMAIN[domain["code"]]

        for difficulty in ["beginner", "intermediate", "advanced", "expert"]:
            # 为每个 领域×难度 组合生成多个画像
            count_per_difficulty = {
                "beginner": 5,
                "intermediate": 4,
                "advanced": 3,
                "expert": 2,
            }[difficulty]

            for i in range(count_per_difficulty):
                # 交替相关专业和非相关专业
                if i % 2 == 0 or difficulty in ("advanced", "expert"):
                    major = random.choice(related_majors)
                    is_related = True
                else:
                    major = random.choice(UNRELATED_MAJORS)
                    is_related = False

                education = random.choice(EDUCATION_LEVELS)
                experience = random.choice(EXPERIENCE_YEARS)

                # 高级/专家级应有更多经验
                if difficulty == "advanced" and experience < 2:
                    experience = random.choice([3, 5, 8])
                elif difficulty == "expert" and experience < 5:
                    experience = random.choice([8, 10, 15])

                learning_style = random.choice(LEARNING_STYLES)

                profile_id += 1
                profile = generate_profile(
                    profile_id, domain, difficulty, education,
                    major, is_related, experience, learning_style,
                )
                profiles.append(profile)

    # 额外生成一批：更多变体覆盖边缘情况
    for _ in range(22):  # 确保总数 >= 50
        domain = random.choice(DOMAINS)
        difficulty = random.choice(["beginner", "intermediate", "advanced", "expert"])
        major = random.choice(
            RELATED_MAJORS_BY_DOMAIN[domain["code"]]
            if random.random() > 0.3
            else UNRELATED_MAJORS
        )
        is_related = major in RELATED_MAJORS_BY_DOMAIN[domain["code"]]
        education = random.choice(EDUCATION_LEVELS)
        experience = random.choice(EXPERIENCE_YEARS)
        learning_style = random.choice(LEARNING_STYLES)

        profile_id += 1
        profile = generate_profile(
            profile_id, domain, difficulty, education,
            major, is_related, experience, learning_style,
        )
        profiles.append(profile)

    # 输出
    print(f"共生成 {len(profiles)} 组学习者画像")

    # 统计
    by_domain = {}
    by_difficulty = {}
    for p in profiles:
        d = p["domain"]
        by_domain[d] = by_domain.get(d, 0) + 1
        diff = p["expected_difficulty"]
        by_difficulty[diff] = by_difficulty.get(diff, 0) + 1

    print(f"领域分布: {by_domain}")
    print(f"难度分布: {by_difficulty}")

    # 写入 JSON 文件
    for p in profiles:
        filename = f"profile_{p['profile_id']:04d}.json"
        with open(OUTPUT_DIR / filename, "w", encoding="utf-8") as f:
            json.dump(p, f, ensure_ascii=False, indent=2)

    # 同时写入一个汇总文件
    summary_path = OUTPUT_DIR / "_all_profiles.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)

    print(f"已输出到: {OUTPUT_DIR}")
    print(f"汇总文件: {summary_path}")
    print(f"文件数量: {len(list(OUTPUT_DIR.glob('profile_*.json')))}")

    # 打印前 5 个画像作为预览
    print("\n━━━ 前 5 个画像预览 ━━━")
    for p in profiles[:5]:
        print(f"  {p['profile_name']} | {p['domain']} | {p['education_background']} | {p['major']}")


if __name__ == "__main__":
    main()
