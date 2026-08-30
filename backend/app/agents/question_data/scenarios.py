"""试题生成使用的场景/蓝图数据与工具。"""
from __future__ import annotations

import random
from datetime import datetime

COMPREHENSIVE_FORMAT_VERSION = "comprehensive_case_v2"

NODE_PRACTICE_DISTRIBUTION = {
    "multiple_choice": 4,
    "true_false": 3,
    "practical": 2,
}

CNC_SCENARIOS: dict[str, list[str]] = {
    "machines": ["立式加工中心 VMC850", "数控车床 CK6140", "卧式加工中心 HMC500", "三轴铣床", "带第四轴加工中心"],
    "materials": ["45钢", "6061铝合金", "Q235钢", "304不锈钢", "POM工程塑料"],
    "sizes": ["80mm x 60mm x 20mm", "Φ50mm x 120mm", "120mm x 80mm x 30mm", "Φ32mm x 75mm", "200mm x 100mm x 15mm"],
    "tolerances": ["±0.02mm", "±0.05mm", "H7孔公差", "平面度0.03mm", "同轴度0.02mm"],
    "alarms": ["主轴过载报警", "刀库换刀异常", "X轴伺服报警", "冷却液液位不足", "程序段格式报警"],
    "inspection_tasks": ["首件外径检测", "孔径千分尺复核", "卡尺测量台阶尺寸", "百分表找正", "粗糙度目测与记录"],
    "tool_states": ["刀尖轻微磨损", "刀具悬伸偏长", "钻头排屑不畅", "端铣刀刃口崩损", "新刀首次试切"],
    "clamping": ["平口钳装夹", "三爪卡盘夹持", "压板装夹", "V形块辅助定位", "软爪夹持"],
}

COMPREHENSIVE_BLUEPRINTS: list[dict] = [
    {
        "family": "milling",
        "machine": "VMC850 立式加工中心",
        "controller": "FANUC 0i-MF",
        "workpiece": "矩形板类、支架类或带孔腔体类零件",
        "materials": "6061-T6 铝合金、Q235 钢或 45 钢（三选一）",
        "clamping": "平口钳或压板装夹，与矩形毛坯和工序匹配",
        "coordinate": "G54，基准设在工件上表面角点或中心，全文保持一致",
        "program_rules": "使用 G17/G90/G54、Txx M06、G43 Hxx、S/M03、F、M08/M09；刀号 T 与刀长补偿 H 必须可核对",
        "risk_pattern": "唯一主要程序风险固定为：执行 T02 M06 后误写 G43 H01，正确值应为与 T02 对应的 H02；其他程序段不得再设置明显错误",
        "forbidden": "禁止出现 G96/G99 车削逻辑、T0101 车刀格式、三爪卡盘车削、外圆精车或 X 轴直径编程",
        "measurement": "卡尺、外径千分尺、百分表、内径量具按被测特征合理选用",
    },
    {
        "family": "turning",
        "machine": "CK6140 数控车床",
        "controller": "FANUC 0i-TF",
        "workpiece": "圆轴类、套类或台阶轴类零件",
        "materials": "45 钢、Q235 钢或 304 不锈钢（三选一）",
        "clamping": "三爪卡盘或软爪夹持圆棒料，夹持长度和悬伸量合理",
        "coordinate": "G54，Z0 设在工件端面、X0 为主轴中心线，全文保持一致",
        "program_rules": "使用 G18/G40/G90 或 G99、T0101 类车刀调用、G96/G97、S/M03、F、M08/M09；刀具号与补偿号可核对",
        "risk_pattern": "唯一主要程序风险固定为：使用 G96 恒线速前未设置 G50 Sxxxx 主轴最高转速限制；第 2 题必须识别缺少 G50 限速，其他程序段不得再设置明显错误",
        "forbidden": "禁止出现 Txx M06 加工中心换刀、G43/H 刀长补偿、平口钳装夹矩形板、G17 平面铣削或 XYZ 三轴铣削描述",
        "measurement": "外径优先使用外径千分尺，长度可使用卡尺或深度量具，形位误差使用百分表等合适量具",
    },
]


def build_scene() -> dict:
    """随机抽取一次业务场景变量。"""
    scene = {key: random.choice(values) for key, values in CNC_SCENARIOS.items()}
    scene["seed"] = f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
    return scene


def build_comprehensive_blueprint() -> dict:
    """随机抽取一份综合练习蓝图。"""
    blueprint = dict(random.choice(COMPREHENSIVE_BLUEPRINTS))
    blueprint["seed"] = f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
    return blueprint


def format_avoid_questions(avoid_questions: list[str] | None) -> str:
    items = [q.strip() for q in (avoid_questions or []) if q and q.strip()]
    if not items:
        return "无"
    return "\n".join(f"- {q[:160]}" for q in items[-20:])


def node_focus_rules(node_title: str, node_topics: list[str] | None) -> str:
    """根据节点标题/知识点关键词生成主题边界提示。"""
    text = f"{node_title} {' '.join(node_topics or [])}"
    rules: list[str] = []
    if any(k in text for k in ["安全", "机床", "启停", "急停", "5S", "点检"]):
        rules.append("安全与机床基础节点：题目主问题应围绕开机前点检、急停/复位、主轴启停、5S、防护门、机床坐标与安全操作边界。")
    if any(k in text for k in ["装夹", "校正", "找正", "基准", "坐标"]):
        rules.append("装夹与校正节点：题目主问题应围绕定位基准、平口钳/压板/三爪装夹、百分表找正、G54工件坐标系、夹紧变形风险。")
    if any(k in text for k in ["量具", "尺寸", "检测", "卡尺", "千分尺", "首件"]):
        rules.append("量具与尺寸检测节点：题目主问题应围绕卡尺/千分尺/百分表使用、首件检测、测量记录、合格判定和尺寸偏差分析。")
    if any(k in text for k in ["刀具", "切削液", "换刀", "刀补", "磨损"]):
        rules.append("刀具与切削液节点：题目主问题应围绕换刀流程、刀具装夹、刀具磨损识别、刀补修正、切削液浓度和冷却排屑。")
    if any(k in text for k in ["G代码", "M代码", "程序", "编程", "识读", "单段", "空运行"]):
        rules.append("G代码识读与基础编程节点：题目主问题必须围绕 G00/G01/G02/G03、G54、G90/G91、S/F/T、M03/M05/M08/M09、刀补、程序段含义、空运行和单段检查；换刀、切削液、装夹只能作为背景，不能成为题目核心。")
    if any(k in text for k in ["异常", "报警", "综合", "超差", "实践"]):
        rules.append("异常识别与综合实践节点：题目主问题应围绕报警判断、尺寸超差、刀具磨损、程序风险、首件复核和现场处置闭环。")
    if not rules:
        rules.append("题目主问题必须紧扣当前节点标题和知识点，不得泛化到其他学习节点。")
    return "\n".join(f"- {rule}" for rule in rules)
