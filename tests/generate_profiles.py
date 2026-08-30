"""
批量生成 50+ 组差异化学习者画像（用于竞赛测试数据提交）。

生成策略：
- 3 个 CNC 职业方向 × 4 个难度 × 多种学历 × 多种专业 = 50+ 组合
- 职业方向：操机工(operator) → 调机工(setup_tech) → 编程师(programmer)
- 每个画像包含完整的输入输出字段
- 输出到 tests/learner_profiles_bulk/ 目录
"""

import json
import random
import os
from pathlib import Path

# 输出目录
OUTPUT_DIR = Path(__file__).parent / "learner_profiles_bulk"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── 参数池 ──

CAREER_TRACKS = [
    {
        "code": "operator",
        "name": "操机工",
        "description": "数控机床操作人员",
        "skills": [
            "机床操作面板使用", "工件装夹与找正", "量具使用(卡尺/千分尺)",
            "G代码阅读能力", "刀具装卸操作", "切削液管理",
            "加工异常识别", "安全操作规范执行",
        ],
    },
    {
        "code": "setup_tech",
        "name": "调机工",
        "description": "数控机床调试与设置人员",
        "skills": [
            "对刀操作", "刀具偏置设置", "夹具安装与调试",
            "切削参数调整", "首件试切与检测", "程序试运行",
            "加工精度调整", "设备故障排查",
        ],
    },
    {
        "code": "programmer",
        "name": "编程师",
        "description": "数控编程与工艺规划人员",
        "skills": [
            "手工G代码编程", "CAM软件编程(UG/Mastercam)", "工艺路线设计",
            "刀具路径优化", "宏程序编写", "多轴编程",
            "加工仿真验证", "工艺文件编制",
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

RELATED_MAJORS = [
    "机械工程", "机械设计制造及其自动化", "材料成型及控制工程",
    "车辆工程", "机电一体化", "模具设计与制造", "数控技术",
    "智能制造工程", "工业工程", "自动化",
]

UNRELATED_MAJORS = [
    "英语", "会计学", "市场营销", "人力资源管理", "法学",
    "汉语言文学", "历史学", "行政管理", "旅游管理", "艺术设计",
    "社会工作", "新闻学", "哲学", "国际经济与贸易",
]

EXPERIENCE_YEARS = [0, 0.5, 1, 2, 3, 5, 8, 10, 15]
LEARNING_STYLES = ["practice", "theory", "visual"]
GOAL_TEMPLATES = {
    "beginner": [
        "了解{track_name}基础概念",
        "掌握{track_name}入门知识",
        "学习{track_name}基本操作",
    ],
    "intermediate": [
        "提升{track_name}实践技能",
        "系统学习{track_name}核心内容",
        "掌握{track_name}常用技术",
    ],
    "advanced": [
        "精通{track_name}高级技术",
        "学习{track_name}优化方法",
        "掌握{track_name}复杂场景应用",
    ],
    "expert": [
        "研究{track_name}前沿技术",
        "掌握{track_name}系统级优化",
        "成为{track_name}领域专家",
    ],
}

SELF_ASSESSMENT_LEVELS = ["不了解", "了解基础", "熟练", "精通"]


def generate_profile(profile_id: int, track: dict, difficulty: str,
                     education: dict, major: str, is_related: bool,
                     experience: float, learning_style: str) -> dict:
    """生成单个学习者画像"""

    # 根据难度级别设置技能自评
    if difficulty == "beginner":
        skill_weights = [0.80, 0.15, 0.04, 0.01]
    elif difficulty == "intermediate":
        skill_weights = [0.30, 0.50, 0.15, 0.05]
    elif difficulty == "advanced":
        skill_weights = [0.05, 0.15, 0.60, 0.20]
    else:  # expert
        skill_weights = [0.01, 0.04, 0.35, 0.60]

    self_assessment = {}
    for skill in track["skills"]:
        level = random.choices(SELF_ASSESSMENT_LEVELS, weights=skill_weights, k=1)[0]
        self_assessment[skill] = level

    # 生成学习目标
    goal_template = random.choice(GOAL_TEMPLATES[difficulty])
    goals = [goal_template.format(track_name=track["name"])]
    if random.random() > 0.5:
        extra = random.choice(GOAL_TEMPLATES[difficulty])
        if extra != goal_template:
            goals.append(extra.format(track_name=track["name"]))

    profile_name = (
        f"{track['name']}-"
        f"{'相关' if is_related else '非相关'}专业-"
        f"{education['bg']}-"
        f"{difficulty}-"
        f"#{profile_id:03d}"
    )

    return {
        "profile_name": profile_name,
        "career_track": track["code"],
        "career_track_name": track["name"],
        "education_background": education["bg"],
        "education_label": education["label"],
        "major": major,
        "major_related": is_related,
        "work_experience_years": experience,
        "learning_style": learning_style,
        "self_assessment": self_assessment,
        "goals": goals,
        "expected_difficulty": difficulty,
        "profile_id": profile_id,
    }


def main():
    random.seed(42)
    profiles = []
    profile_id = 0

    for track in CAREER_TRACKS:
        for difficulty in ["beginner", "intermediate", "advanced", "expert"]:
            count_per_difficulty = {
                "beginner": 5,
                "intermediate": 4,
                "advanced": 3,
                "expert": 2,
            }[difficulty]

            for i in range(count_per_difficulty):
                if i % 2 == 0 or difficulty in ("advanced", "expert"):
                    major = random.choice(RELATED_MAJORS)
                    is_related = True
                else:
                    major = random.choice(UNRELATED_MAJORS)
                    is_related = False

                education = random.choice(EDUCATION_LEVELS)
                experience = random.choice(EXPERIENCE_YEARS)

                if difficulty == "advanced" and experience < 2:
                    experience = random.choice([3, 5, 8])
                elif difficulty == "expert" and experience < 5:
                    experience = random.choice([8, 10, 15])

                learning_style = random.choice(LEARNING_STYLES)

                profile_id += 1
                profiles.append(generate_profile(
                    profile_id, track, difficulty, education,
                    major, is_related, experience, learning_style,
                ))

    # 额外生成
    for _ in range(22):
        track = random.choice(CAREER_TRACKS)
        difficulty = random.choice(["beginner", "intermediate", "advanced", "expert"])
        major = random.choice(RELATED_MAJORS if random.random() > 0.3 else UNRELATED_MAJORS)
        is_related = major in RELATED_MAJORS
        education = random.choice(EDUCATION_LEVELS)
        experience = random.choice(EXPERIENCE_YEARS)
        learning_style = random.choice(LEARNING_STYLES)

        profile_id += 1
        profiles.append(generate_profile(
            profile_id, track, difficulty, education,
            major, is_related, experience, learning_style,
        ))

    # 输出
    print(f"共生成 {len(profiles)} 组学习者画像")

    # 统计
    by_track = {}
    by_difficulty = {}
    for p in profiles:
        t = p["career_track"]
        by_track[t] = by_track.get(t, 0) + 1
        diff = p["expected_difficulty"]
        by_difficulty[diff] = by_difficulty.get(diff, 0) + 1

    print(f"职业分布: {by_track}")
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
        print(f"  {p['profile_name']} | {p['career_track']} | {p['education_background']} | {p['major']}")


if __name__ == "__main__":
    main()
