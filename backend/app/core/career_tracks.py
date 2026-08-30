"""
CNC 职业方向配置模块
定义 CNC 数控加工领域的 3 个层级递进职业方向：操机工 → 调机工 → 编程师
每个方向有独立的技能自评项、核心知识点和难度等级
"""

from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_KB_BASE = _PROJECT_ROOT / "knowledge-base"


@dataclass
class CareerTrackConfig:
    """CNC 职业方向配置"""
    name: str                           # 职业中文名称
    code: str                           # 职业代码
    order: int                          # 职业层级序号（1=操机工, 2=调机工, 3=编程师）
    description: str                    # 职业描述
    knowledge_base_dir: str             # 知识库目录
    core_topics: List[str]              # 核心主题列表
    prompt_context: str                 # 注入 prompt 的职业上下文
    difficulty_levels: List[str] = field(default_factory=lambda: ["beginner", "intermediate", "advanced", "expert"])
    self_assessment_skills: List[str] = field(default_factory=list)  # 技能自评项
    prerequisite_knowledge: str = ""    # 前置知识要求（层级递进关系）


# ── 职业方向注册表 ──

CAREER_TRACKS: Dict[str, CareerTrackConfig] = {
    "operator": CareerTrackConfig(
        name="操机工",
        code="operator",
        order=1,
        description="数控机床操作人员，负责机床日常操作、工件装卸、简单检测和安全规范",
        knowledge_base_dir=str(_KB_BASE / "cnc_domain"),
        core_topics=[
            "机床启停与急停", "工件装夹与校正", "简单尺寸检测",
            "G代码基础识读", "刀具更换流程", "切削液配比与管理",
            "常见加工缺陷识别", "设备日常点检", "5S现场管理",
            "安全操作规范", "量具使用", "加工流程认知",
        ],
        prompt_context=(
            "CNC 数控加工领域 — 操机工方向。"
            "操机工是数控加工的入门岗位，负责数控机床的日常操作，"
            "包括工件装卸、机床启停、简单尺寸检测、刀具更换、安全操作等。"
            "操机工需要掌握 G 代码的基本识读能力但不要求独立编程。"
        ),
        self_assessment_skills=[
            "机床操作面板使用", "工件装夹与找正", "量具使用(卡尺/千分尺)",
            "G代码阅读能力", "刀具装卸操作", "切削液管理",
            "加工异常识别", "安全操作规范执行",
        ],
        prerequisite_knowledge="无前置要求，零基础可学。",
    ),
    "setup_tech": CareerTrackConfig(
        name="调机工",
        code="setup_tech",
        order=2,
        description="数控机床调试与设置人员，负责对刀、参数调整、首件检测和故障排查",
        knowledge_base_dir=str(_KB_BASE / "cnc_domain"),
        core_topics=[
            "多种对刀方法", "刀具补偿设置(G41/G42/G43)",
            "夹具定位与夹紧", "切削参数优化", "首件检验流程",
            "程序空运行与单段执行", "尺寸超差分析与调整",
            "常见报警处理", "换型调试流程", "加工精度控制",
        ],
        prompt_context=(
            "CNC 数控加工领域 — 调机工方向。"
            "调机工是数控加工的中级岗位，负责数控机床的调试与设置，"
            "包括对刀、刀具补偿设置、夹具安装调试、切削参数调整、首件检测等。"
            "调机工需要具备操机工的全部技能基础，能够独立完成机床调试工作。"
        ),
        self_assessment_skills=[
            "对刀操作", "刀具偏置设置", "夹具安装与调试",
            "切削参数调整", "首件试切与检测", "程序试运行",
            "加工精度调整", "设备故障排查",
        ],
        prerequisite_knowledge="需具备操机工的全部技能基础（机床操作、工件装夹、量具使用、安全规范等）。",
    ),
    "programmer": CareerTrackConfig(
        name="编程师",
        code="programmer",
        order=3,
        description="数控编程与工艺规划人员，负责程序编写、CAM编程、工艺设计和优化",
        knowledge_base_dir=str(_KB_BASE / "cnc_domain"),
        core_topics=[
            "G代码/M代码编程", "CAD/CAM软件应用(UG/Mastercam)",
            "加工工艺规程设计", "刀具路径优化策略",
            "B类宏程序编程", "四轴/五轴编程", "后处理定制",
            "加工仿真与碰撞检查", "工艺标准化与文档",
        ],
        prompt_context=(
            "CNC 数控加工领域 — 编程师方向。"
            "编程师是数控加工的高级岗位，负责数控加工程序的编写与优化，"
            "包括手工 G 代码编程、CAM 软件编程、工艺规划、宏程序编写、多轴编程等。"
            "编程师需要理解操机工和调机工的全部工作内容，"
            "能够编写高效、安全、可维护的数控加工程序。"
        ),
        self_assessment_skills=[
            "手工G代码编程", "CAM软件编程(UG/Mastercam)", "工艺路线设计",
            "刀具路径优化", "宏程序编写", "多轴编程",
            "加工仿真验证", "工艺文件编制",
        ],
        prerequisite_knowledge="需具备操机工和调机工的全部技能基础（机床操作、对刀调试、参数调整、首件检测等）。",
    ),
}

DEFAULT_CAREER_TRACK = "operator"


# ── 查询函数 ──

def get_career_track(code: str) -> Optional[CareerTrackConfig]:
    """获取指定职业方向的配置"""
    return CAREER_TRACKS.get(code)


def get_default_career_track() -> CareerTrackConfig:
    """获取默认职业方向配置（操机工）"""
    return CAREER_TRACKS[DEFAULT_CAREER_TRACK]


def get_all_career_tracks() -> List[CareerTrackConfig]:
    """获取所有职业方向配置（按层级排序）"""
    return sorted(CAREER_TRACKS.values(), key=lambda t: t.order)


def get_career_track_codes() -> List[str]:
    """获取所有职业方向代码列表"""
    return [t.code for t in get_all_career_tracks()]


def get_career_track_from_input(learner_input: dict) -> CareerTrackConfig:
    """
    从学习者输入中提取职业方向配置

    优先级：
    1. learner_input["career_track"] 字段
    2. 默认职业方向（操机工）

    Args:
        learner_input: 学习者输入数据

    Returns:
        CareerTrackConfig 职业方向配置
    """
    # 显式指定职业方向
    track_code = learner_input.get("career_track", "")
    if track_code and track_code in CAREER_TRACKS:
        return CAREER_TRACKS[track_code]

    # 返回默认职业方向
    return get_default_career_track()


def build_career_prompt(track: CareerTrackConfig) -> str:
    """
    构建职业方向上下文 prompt

    Args:
        track: 职业方向配置

    Returns:
        职业上下文字符串
    """
    lines = [
        f"【职业方向】{track.name}（{track.description}）",
        f"【前置知识】{track.prerequisite_knowledge}",
        f"【核心主题】{', '.join(track.core_topics[:10])}",
        f"【难度等级】{' → '.join(track.difficulty_levels)}",
        "",
        track.prompt_context,
    ]
    return "\n".join(lines)


# ── 兼容性别名（供尚未完全迁移的代码使用）──

def get_domain_from_input(learner_input: dict) -> CareerTrackConfig:
    """兼容别名：从 learner_input 获取职业方向配置"""
    return get_career_track_from_input(learner_input)


def build_domain_prompt(track: CareerTrackConfig, extra_context: str = "") -> str:
    """兼容别名：构建职业方向上下文 prompt"""
    return build_career_prompt(track)


def get_default_domain() -> CareerTrackConfig:
    """兼容别名：获取默认职业方向"""
    return get_default_career_track()


def get_all_domains() -> List[CareerTrackConfig]:
    """兼容别名：获取所有职业方向"""
    return get_all_career_tracks()


def get_domain_names() -> List[str]:
    """兼容别名：获取所有职业方向代码"""
    return get_career_track_codes()
