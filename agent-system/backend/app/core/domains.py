"""
领域配置模块
支持多领域迁移，通过配置驱动而非硬编码
"""

from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

# 项目根目录（agent-system/）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_KB_BASE = _PROJECT_ROOT / "knowledge-base"


@dataclass
class DomainConfig:
    """领域配置"""
    name: str                           # 领域中文名称
    code: str                           # 领域代码（如 "cnc", "python_data_analysis"）
    description: str                    # 领域描述
    knowledge_base_dir: str             # 知识库目录路径（绝对路径）
    core_topics: List[str]              # 核心主题列表
    excluded_topics: List[str]          # 排除的主题（用于防止生成错误领域内容）
    prompt_context: str                 # 领域上下文描述（注入到 prompt 中）
    difficulty_levels: List[str]        # 难度等级定义
    self_assessment_skills: List[str] = field(default_factory=list)  # 前端技能自评项


# 领域注册表
DOMAINS: Dict[str, DomainConfig] = {
    "cnc": DomainConfig(
        name="CNC 数控加工",
        code="cnc",
        description="数控编程、G代码、切削参数、刀具管理、加工工艺等",
        knowledge_base_dir=str(_KB_BASE / "cnc_domain"),
        core_topics=[
            "数控编程", "G代码", "M代码", "坐标系", "刀具补偿",
            "切削参数", "进给量", "切削速度", "刀具选择",
            "数控车床", "数控铣床", "加工中心",
            "工艺规划", "质量控制", "安全操作"
        ],
        excluded_topics=[
            "Python", "Java", "C++", "JavaScript", "数据分析",
            "机器学习", "深度学习", "软件开发", "Web开发"
        ],
        prompt_context=(
            "数控加工（CNC）领域，包括数控编程、G代码、切削参数、刀具管理、"
            "加工工艺等内容。所有知识点必须严格围绕数控加工领域。"
        ),
        difficulty_levels=["beginner", "intermediate", "advanced", "expert"],
        self_assessment_skills=[
            "机械制图基础", "G 代码编程", "数控车床操作",
            "数控铣床操作", "CAM 软件应用", "刀具选择与管理",
            "切削参数优化", "测量与检测",
        ],
    ),
    "python_data_analysis": DomainConfig(
        name="Python 数据分析",
        code="python_data_analysis",
        description="Python编程、NumPy、Pandas、Matplotlib、数据清洗、数据可视化等",
        knowledge_base_dir=str(_KB_BASE / "demo_domain" / "python_data_analysis"),
        core_topics=[
            "Python基础", "NumPy", "Pandas", "Matplotlib", "Seaborn",
            "数据清洗", "数据可视化", "统计分析", "数据处理",
            "Jupyter Notebook", "数据导入导出", "数据转换"
        ],
        excluded_topics=[
            "数控", "G代码", "切削", "机床", "刀具", "机械加工"
        ],
        prompt_context=(
            "Python 数据分析领域，包括 Python 编程基础、NumPy 数组操作、"
            "Pandas 数据处理、Matplotlib/Seaborn 数据可视化等内容。"
            "所有知识点必须围绕 Python 数据分析技术栈。"
        ),
        difficulty_levels=["beginner", "intermediate", "advanced", "expert"],
        self_assessment_skills=[
            "Python基础语法", "NumPy数组操作", "Pandas数据处理",
            "Matplotlib绘图", "Seaborn可视化", "数据清洗与预处理",
            "统计分析基础", "Jupyter Notebook使用",
        ],
    ),
}

# 默认领域
DEFAULT_DOMAIN = "cnc"


def get_domain(domain_code: str) -> Optional[DomainConfig]:
    """
    获取指定领域的配置

    Args:
        domain_code: 领域代码

    Returns:
        DomainConfig 或 None（如果领域不存在）
    """
    return DOMAINS.get(domain_code)


def get_default_domain() -> DomainConfig:
    """获取默认领域配置"""
    return DOMAINS[DEFAULT_DOMAIN]


def get_all_domains() -> List[DomainConfig]:
    """获取所有可用领域配置"""
    return list(DOMAINS.values())


def get_domain_names() -> List[str]:
    """获取所有领域代码列表"""
    return list(DOMAINS.keys())


def get_domain_from_input(learner_input: dict) -> DomainConfig:
    """
    从学习者输入中提取领域配置

    优先级：
    1. learner_input["domain"] 字段
    2. 从 goals 中推断
    3. 默认领域

    Args:
        learner_input: 学习者输入数据

    Returns:
        DomainConfig 领域配置
    """
    # 1. 显式指定领域
    domain_code = learner_input.get("domain", "")
    if domain_code and domain_code in DOMAINS:
        return DOMAINS[domain_code]

    # 2. 从 goals 推断
    goals = learner_input.get("goals", [])
    if goals:
        goal_text = " ".join(goals).lower()
        for code, config in DOMAINS.items():
            # 检查 goals 中是否包含领域关键词
            if any(topic.lower() in goal_text for topic in config.core_topics[:5]):
                return config

    # 3. 返回默认领域
    return get_default_domain()


def build_domain_prompt(domain: DomainConfig, extra_context: str = "") -> str:
    """
    构建领域上下文 prompt

    Args:
        domain: 领域配置
        extra_context: 额外上下文

    Returns:
        领域上下文字符串
    """
    prompt = f"""你专精于{domain.prompt_context}

【核心主题】
{', '.join(domain.core_topics[:10])}

【禁止生成的内容】
{', '.join(domain.excluded_topics[:5])}"""

    if extra_context:
        prompt += f"\n\n【额外上下文】\n{extra_context}"

    return prompt
