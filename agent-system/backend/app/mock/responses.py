"""Mock 响应数据：所有 23 个 LLM 调用点的预设返回值。

组织结构：
- MOCK_RESPONSES_BY_LABEL：按 label 键索引的响应（9 个标记调用）
- _MATCHERS：按 prompt 子串匹配的 (substring, response_fn) 元组列表（14 个未标记调用）
"""

import json


# ══════════════════════════════════════════════════════════════════
# 辅助函数
# ══════════════════════════════════════════════════════════════════

def _j(obj) -> str:
    """将 Python 对象序列化为 JSON 字符串"""
    return json.dumps(obj, ensure_ascii=False)


# ══════════════════════════════════════════════════════════════════
# ① 学情诊断 Agent — build_profile()
# ══════════════════════════════════════════════════════════════════

def _mock_build_profile() -> str:
    return _j({
        "knowledge_points": [
            {"name": "G 代码基础指令", "level": "beginner", "score": 20, "confidence": 0.6},
            {"name": "数控车床编程", "level": "beginner", "score": 15, "confidence": 0.5},
            {"name": "数控铣床编程", "level": "beginner", "score": 10, "confidence": 0.4},
            {"name": "刀具选择与管理", "level": "beginner", "score": 25, "confidence": 0.6},
            {"name": "切削参数选择", "level": "beginner", "score": 30, "confidence": 0.7},
            {"name": "公差与配合", "level": "intermediate", "score": 50, "confidence": 0.8},
            {"name": "机械制图基础", "level": "intermediate", "score": 65, "confidence": 0.85},
            {"name": "CAM 软件应用", "level": "beginner", "score": 5, "confidence": 0.3},
        ],
        "blind_spots": ["G 代码编程", "CAM 软件应用", "数控铣床编程", "切削参数优化"],
        "overall_level": "beginner",
        "learning_style_analysis": "该学习者有机械制图基础，但 CNC 编程经验为零。建议从 G 代码基础入手，结合机械制图优势快速建立坐标系概念，通过大量实操练习巩固编程技能。",
        "recommended_difficulty": "beginner",
        "domain": "cnc",
    })


# ══════════════════════════════════════════════════════════════════
#  学情诊断 Agent — locate_blind_spots()
# ══════════════════════════════════════════════════════════════════

def _mock_locate_blind_spots() -> str:
    return _j([
        "G 代码编程",
        "数控车床操作",
        "CAM 软件应用",
        "切削参数优化",
        "刀具选择与管理",
    ])


# ══════════════════════════════════════════════════════════════════
# ② 路径规划 Agent — plan_path()
# ══════════════════════════════════════════════════════════════════

def _mock_plan_path() -> str:
    return _j({
        "path": [
            {
                "stage": 1,
                "title": "G 代码基础与坐标系",
                "topics": ["G 代码基础指令", "工件坐标系设置", "绝对/增量编程"],
                "estimated_hours": 8,
                "difficulty": "beginner",
                "prerequisites": [],
                "resources_type": ["lecture", "guide", "project"],
            },
            {
                "stage": 2,
                "title": "数控车床编程入门",
                "topics": ["车床对刀", "外圆切削循环 G90", "螺纹切削 G92", "刀具补偿 G41/G42"],
                "estimated_hours": 12,
                "difficulty": "beginner",
                "prerequisites": ["G 代码基础"],
                "resources_type": ["lecture", "guide", "project"],
            },
            {
                "stage": 3,
                "title": "切削参数与刀具管理",
                "topics": ["切削速度选择", "进给量计算", "刀具材料与寿命", "切削液使用"],
                "estimated_hours": 10,
                "difficulty": "intermediate",
                "prerequisites": ["数控车床编程入门"],
                "resources_type": ["lecture", "guide", "project"],
            },
        ],
        "total_estimated_hours": 30,
        "current_stage": 1,
        "recommended_order": "按阶段顺序学习，每个阶段完成后通过测试再进入下一阶段",
    })


# ══════════════════════════════════════════════════════════════════
# ② 路径规划 Agent — adjust_path()
# ══════════════════════════════════════════════════════════════════

def _mock_adjust_path() -> str:
    return _j({
        "path": [
            {
                "stage": 0,
                "title": "G 代码基础（基础巩固）",
                "topics": ["G00 快速定位", "G01 直线插补", "坐标系概念"],
                "estimated_hours": 4,
                "difficulty": "beginner",
                "prerequisites": [],
                "resources_type": ["lecture", "guide"],
            },
            {
                "stage": 1,
                "title": "G 代码基础与坐标系",
                "topics": ["G 代码基础指令", "工件坐标系设置", "绝对/增量编程"],
                "estimated_hours": 8,
                "difficulty": "beginner",
                "prerequisites": [],
                "resources_type": ["lecture", "guide", "project"],
            },
            {
                "stage": 2,
                "title": "数控车床编程入门",
                "topics": ["车床对刀", "外圆切削循环 G90", "螺纹切削 G92"],
                "estimated_hours": 12,
                "difficulty": "beginner",
                "prerequisites": ["G 代码基础"],
                "resources_type": ["lecture", "guide", "project"],
            },
        ],
        "total_estimated_hours": 24,
        "current_stage": 0,
        "recommended_order": "当前阶段为基础巩固，完成后再进入正式学习阶段",
    })


# ══════════════════════════════════════════════════════════════════
# ③ 知识生成 Agent — generate_lecture_notes() [label: "生成讲义"]
# ══════════════════════════════════════════════════════════════════

def _mock_lecture_notes() -> str:
    return """# G 代码基础入门

## 概述

G 代码（G-code）是数控机床的核心编程语言，用于控制刀具的运动轨迹、速度、加工方式等。本节将介绍最常用的 G 代码指令：G00 快速定位、G01 直线插补、G02/G03 圆弧插补。

学习目标：能独立编写简单的数控车床/铣床程序，理解各指令的使用场景。

## 核心知识点

### 快速定位指令 G00

G00 用于刀具在非切削状态下快速移动到指定位置。

[知识点：G00 快速定位]
📚 来源：《数控编程与操作》(张明, 2022) 第3章
权威度：★★★★★

**格式**：
```gcode
G00 X100 Z50   ; 车床：快速移动到 X100 Z50
G00 X50 Y30 Z10 ; 铣床：快速移动到三维坐标点
```

**注意事项**：
- G00 速度由机床参数设定，不可用 F 指令控制
- 运动轨迹不一定是直线，可能是各轴独立运动的折线
- 使用时需确保安全高度，避免刀具碰撞工件或夹具

### 直线插补指令 G01

G01 用于刀具以指定进给速度进行直线切削运动。

[知识点：G01 直线插补]
📚 来源：《FANUC数控系统编程手册》(FANUC, 2021) 第5章
权威度：★★★★★

**格式**：
```gcode
G01 X50 Z-20 F0.2   ; 车床：直线切削到 X50 Z-20，进给速度 0.2mm/r
G01 Y30 F150         ; 铣床：直线切削到 Y30，进给速度 150mm/min
```

### 圆弧插补指令 G02/G03

- G02：顺时针圆弧插补
- G03：逆时针圆弧插补

[知识点：G02/G03 圆弧插补]
📚 来源：《数控编程与操作》(张明, 2022) 第3章
权威度：★★★★★

**格式（半径方式）**：
```gcode
G02 X100 Z-50 R30 F0.15   ; 顺时针圆弧，半径 R=30mm
G03 X80 Y60 R20 F100      ; 逆时针圆弧，半径 R=20mm
```

**格式（圆心增量 I/J/K）**：
```gcode
G02 X100 Z-50 I30 K0 F0.15
```

## 代码示例

以下是一个完整的数控车床外圆加工程序：

```gcode
O0001               ; 程序号
G21 G99             ; 公制单位，每转进给
G28 U0 W0           ; 返回参考点
T0101               ; 调用 1 号刀，1 号刀补
M03 S800            ; 主轴正转，800rpm
G00 X32 Z2          ; 快速定位到加工起点
G01 Z-30 F0.15      ; 车削外圆，长度 30mm
G01 X35             ; 退刀
G00 Z2              ; 快速返回
G28 U0 W0           ; 返回参考点
M30                 ; 程序结束
```

## 常见问题

1. **G02/G03 方向判断错误**：站在第三轴正方向观察加工平面
2. **G00 碰撞问题**：先 Z 轴退刀再 X/Y 轴移动，确保安全高度
3. **进给速度单位混淆**：车床 G99 为 mm/r，铣床 G94 为 mm/min

## 总结

- G00 快速定位（不切削）
- G01 直线切削（需指定 F）
- G02/G03 圆弧切削（R 或 I/J/K 方式）
- 掌握这三个指令即可编写大部分简单加工程序"""


# ══════════════════════════════════════════════════════════════════
# ③ 知识生成 Agent — generate_practical_guide() [label: "生成实验指导"]
# ══════════════════════════════════════════════════════════════════

def _mock_practical_guide() -> str:
    return """# G 代码基础 实验指导

## 实验目标

1. 掌握 G00、G01、G02/G03 指令的格式和用法
2. 能在仿真环境中编写简单的车削加工程序
3. 理解绝对坐标与增量坐标的区别

## 前置知识

- 了解数控机床的基本组成和工作原理
- 理解笛卡尔坐标系的概念
- 了解切削加工的基本概念

## 操作步骤

### 步骤 1：启动仿真软件

打开数控仿真软件（如宇龙数控仿真、斯沃数控仿真），选择 FANUC 0i-T 车床系统。

### 步骤 2：编写简单外圆加工程序

在编辑模式下输入以下程序：

```gcode
O0002
G21 G99
G28 U0 W0
T0101
M03 S1000
G00 X25 Z2
G01 Z-20 F0.1
G01 X28
G00 Z2
G28 U0 W0
M30
```

### 步骤 3：模拟运行

1. 切换到自动模式（MEM）
2. 按"图形"键进入图形模拟界面
3. 按"循环启动"开始模拟
4. 观察刀具运动轨迹是否正确

### 步骤 4：修改练习

将程序中的 G01 Z-20 改为 G01 Z-30（增加切削长度），重新模拟观察变化。

## 常见错误与排查

| 错误现象 | 可能原因 | 排查方法 |
|---------|---------|---------|
| 刀具路径异常 | G00/G01 混淆 | 检查程序中使用了正确的 G 指令 |
| 圆弧方向错误 | G02/G03 用反 | 站在第三轴正方向观察 |
| 程序无法启动 | 缺少程序号 | 确保程序以 Oxxxx 开头 |

## 思考题

1. 如果将 F0.1 改为 F0.3，切削时间会如何变化？加工表面质量会受到什么影响？
2. 在什么情况下使用 G91 增量编程比 G90 绝对编程更方便？"""


# ══════════════════════════════════════════════════════════════════
# ③ 知识生成 Agent — generate_project_case() [label: "生成项目案例"]
# ══════════════════════════════════════════════════════════════════

def _mock_project_case() -> str:
    return """# G 代码基础 项目案例：阶梯轴加工

## 项目背景

某机械加工车间需要批量生产一种阶梯轴零件。该零件包含三个不同直径的轴段：
- φ20mm × 10mm（最右段）
- φ24mm × 15mm（中间段）
- φ28mm × 20mm（最左段）
毛坯为 φ30mm × 50mm 的圆钢。

## 需求分析与方案设计

加工方案：使用数控车床，一次装夹完成外圆车削。
工艺流程：
1. 粗车外圆至 φ28.5mm
2. 半精车阶梯各段至目标尺寸
3. 倒角 C1

## 实现步骤

### 步骤 1：工艺分析

[知识点：阶梯轴加工工艺]
📚 来源：《数控车床操作指南》(王伟, 2022) 第4章
权威度：★★★★★

### 步骤 2：编写加工程序

```gcode
O0100              ; 阶梯轴加工程序
G21 G99            ; 公制单位，每转进给
G28 U0 W0
T0101              ; 1 号外圆车刀
M03 S1200          ; 主轴正转 1200rpm
G00 X30 Z2         ; 快速定位
G01 Z-20 F0.2      ; 粗车 φ28 段
G01 X28
G00 X25 Z2
G01 Z-15 F0.15     ; 车削 φ24 段
G01 X24
G00 X21 Z2
G01 Z-10 F0.1      ; 车削 φ20 段
G01 X20
G00 Z2
G28 U0 W0
M30
```

### 步骤 3：质量验证

使用游标卡尺测量各段直径和长度，检查是否在公差范围内：
- φ20 段：公差 ±0.05mm
- φ24 段：公差 ±0.05mm
- φ28 段：公差 ±0.1mm

## 总结与扩展

本案例展示了使用 G00/G01 指令完成阶梯轴加工的方法。可以进一步学习：
- 使用 G71 粗车循环简化程序
- 使用 G42 刀具半径补偿提高精度
- 添加 G04 暂停指令进行倒角加工"""


# ══════════════════════════════════════════════════════════════════
# 审核纠偏 Agent — 学术审查 [label: "学术审查"]
#   （同时用于 debate_verify 和 corrective_review）
# ══════════════════════════════════════════════════════════════════

def _mock_empty_issues() -> str:
    """学术/工业审查：无问题通过"""
    return _j([])


def _mock_minor_issues() -> str:
    """学术审查：发现次要问题（用于 debate_verify.verify）"""
    return _j([
        {"issue": "建议补充 G01 进给速度单位的详细说明（车床 G99 与铣床 G94 的区别）", "severity": "suggestion"},
        {"issue": "圆弧插补部分缺少 I/J/K 圆心增量方式的参数说明", "severity": "minor"},
    ])


# ══════════════════════════════════════════════════════════════════
# 审核纠偏 Agent — 修正生成 [label: "修正生成"]
# ══════════════════════════════════════════════════════════════════

def _mock_corrected_content() -> str:
    """修正后的内容"""
    return """# G 代码基础入门（已修正）

## 概述

G 代码（G-code）是数控机床的核心编程语言。以下内容已根据审核意见修正。

## 核心知识点

### 快速定位指令 G00

G00 用于刀具在非切削状态下快速移动到指定位置。

[知识点：G00 快速定位]
📚 来源：《数控编程与操作》(张明, 2022) 第3章
权威度：★★★★★

**格式**：
```gcode
G00 X100 Z50   ; 车床
G00 X50 Y30 Z10 ; 铣床
```

**重要提示**：G00 运动速度由机床参数设定，不可以用 F 指令控制。定位路径可能是折线而非直线，编程时务必确保安全高度。

### 直线插补指令 G01

G01 用于刀具以指定进给速度进行直线切削运动。

[知识点：G01 直线插补]
📚 来源：《FANUC数控系统编程手册》(FANUC, 2021) 第5章
权威度：★★★★★

**格式**：
```gcode
G01 X50 Z-20 F0.2   ; 车床（G99 模式：mm/r）
G01 Y30 F150         ; 铣床（G94 模式：mm/min）
```

**进给速度单位说明**：
- 车床：G99 模式下 F 单位为 mm/r（每转进给），G98 模式下为 mm/min
- 铣床：G94 模式下 F 单位为 mm/min（每分钟进给），G95 模式下为 mm/r

### 圆弧插补指令 G02/G03

[知识点：G02/G03 圆弧插补]
📚 来源：《数控编程与操作》(张明, 2022) 第3章
权威度：★★★★★

**格式（半径方式 R）**：
```gcode
G02 X100 Z-50 R30 F0.15
```

**格式（圆心增量 I/J/K）**：
- I：圆心相对于起点的 X 方向增量
- J：圆心相对于起点的 Y 方向增量
- K：圆心相对于起点的 Z 方向增量

```gcode
G02 X100 Z-50 I30 K0 F0.15
```

## 总结
- G00 快速定位（非切削）
- G01 直线切削（F 指定进给速度，注意单位）
- G02/G03 圆弧切削（支持 R 和 I/J/K 两种方式）"""


# ══════════════════════════════════════════════════════════════════
# 审核纠偏 Agent — 修正验证 [label: "修正验证"]
# ══════════════════════════════════════════════════════════════════

def _mock_verification_passed() -> str:
    return _j({
        "verdict": "resolved",
        "reason": "修正后的内容已正确补充进给速度单位说明和 I/J/K 参数说明，与原审核意见一致",
    })


def _mock_verification_failed() -> str:
    return _j({
        "verdict": "unresolved",
        "reason": "修正后的内容仍未补充 G41/G42 刀具补偿相关内容",
    })


# ══════════════════════════════════════════════════════════════════
# 审核纠偏 Agent — 内容审核 (verify) [label: "内容审核"]
# ══════════════════════════════════════════════════════════════════

def _mock_content_review() -> str:
    return _j({
        "score": 0.88,
        "issues": [],
        "suggestions": ["建议补充更多实际加工案例"],
    })


# ══════════════════════════════════════════════════════════════════
# 辩论管理器 — challenge() + defend()
# ══════════════════════════════════════════════════════════════════

def _mock_challenge_issues() -> str:
    """审核方质疑（debate.challenge）"""
    return _j({
        "issues": [
            "G02/G03 方向判断部分缺少'I/J/K 圆心增量方式'的说明",
            "建议在代码示例中增加更多注释说明每行的作用",
        ],
        "confidence": 0.85,
    })


def _mock_defend_response() -> str:
    """生成方辩护/修正（debate.defend）"""
    return _j({
        "responses": [
            "已补充 I/J/K 参数说明：I 为 X 方向圆心增量，J 为 Y 方向，K 为 Z 方向",
            "已在代码示例中添加逐行注释",
        ],
        "revised_content": "G02 X100 Z-50 I30 K0 F0.15  ; I: X方向圆心增量, K: Z方向圆心增量",
        "has_revision": True,
    })


# ══════════════════════════════════════════════════════════════════
# 独立裁判 Agent — judge() + _regression_check()
# ══════════════════════════════════════════════════════════════════

def _mock_judge_verdict() -> str:
    """裁判判决通过"""
    return _j({
        "passed": True,
        "adopted_side": "defender",
        "reason": "辩护方已修正所有实质性问题，修正后的内容准确无误。审核方提出的问题主要是建议性而非实质性错误。",
        "quality_score": 0.92,
        "effective_issues": [],
        "overruled_issues": ["I/J/K 参数说明不完整（已补充）", "代码注释不足（已添加）"],
    })


def _mock_regression_check_passed() -> str:
    """回归验证通过"""
    return _j({
        "verified": True,
        "checks": [
            {"issue": "I/J/K 参数说明", "fixed": True, "reason": "修正后已正确补充圆心增量参数说明"},
            {"issue": "代码注释不足", "fixed": True, "reason": "代码中已添加逐行注释"},
        ],
        "reason": "所有问题均已正确修复，修正后的内容与知识库一致",
    })


# ══════════════════════════════════════════════════════════════════
# 试题生成 Agent — generate_questions()
# ══════════════════════════════════════════════════════════════════

def _mock_questions() -> str:
    return _j({
        "topic": "G 代码基础",
        "difficulty": "beginner",
        "domain": "cnc",
        "questions": [
            {
                "question": "G00 指令的作用是什么？",
                "question_type": "multiple_choice",
                "options": [
                    "A. 直线切削加工",
                    "B. 快速定位（非切削）",
                    "C. 圆弧切削加工",
                    "D. 程序暂停",
                ],
                "correct_answer": "B",
                "explanation": "G00 是快速定位指令，刀具以最大速度移动到指定位置，不进行切削加工。直线切削使用 G01，圆弧切削使用 G02/G03。",
            },
            {
                "question": "在数控车床中，G01 X50 Z-20 F0.2 中的 F0.2 表示什么？",
                "question_type": "multiple_choice",
                "options": [
                    "A. 主轴转速 0.2 rpm",
                    "B. 进给速度 0.2 mm/r（G99 模式）",
                    "C. 切削深度 0.2 mm",
                    "D. 刀具半径 0.2 mm",
                ],
                "correct_answer": "B",
                "explanation": "在 G99 模式（每转进给）下，F0.2 表示进给速度为 0.2mm/r。G98 模式下 F 的单位为 mm/min。",
            },
            {
                "question": "G02 是逆时针圆弧插补指令。",
                "question_type": "true_false",
                "options": ["正确", "错误"],
                "correct_answer": "错误",
                "explanation": "G02 是顺时针圆弧插补，G03 才是逆时针圆弧插补。判断方向时站在第三轴正方向观察加工平面。",
            },
            {
                "question": "G00 快速定位时的运动轨迹一定是直线。",
                "question_type": "true_false",
                "options": ["正确", "错误"],
                "correct_answer": "错误",
                "explanation": "G00 的运动轨迹不一定是直线，可能是各轴独立以最大速度运动的折线路径。编程时需注意避免碰撞。",
            },
            {
                "question": "请简述 G00 和 G01 指令的主要区别，并说明各自的使用场景。",
                "question_type": "practical",
                "options": [],
                "correct_answer": "G00 用于快速定位（非切削），速度由机床参数决定，轨迹不一定是直线，用于加工前的定位和加工后的退刀。G01 用于直线切削加工，需要指定进给速度 F，刀具以 F 速度沿直线运动，用于实际的切削加工。示例：先用 G00 快速定位到工件附近，再用 G01 进行切削。",
                "explanation": "评分标准：(1) 正确区分两者用途（40分）；(2) 说明 G00 轨迹不确定性（20分）；(3) 说明 G01 需要 F 参数（20分）；(4) 给出合理使用场景（20分）",
            },
            {
                "question": "编写一段数控车床程序，完成直径 30mm、长度 25mm 的圆柱外圆车削（毛坯直径 35mm）。",
                "question_type": "practical",
                "options": [],
                "correct_answer": "参考程序：\nO0001\nG21 G99\nG28 U0 W0\nT0101\nM03 S1000\nG00 X35 Z2\nG01 Z-25 F0.15\nG01 X36\nG00 Z2\nG28 U0 W0\nM30",
                "explanation": "评分标准：(1) 程序号 Oxxxx（10分）；(2) 正确使用 G00/G01 指令（30分）；(3) 合理选择切削参数（20分）；(4) 包含退刀和安全返回（20分）；(5) 整体逻辑完整合理（20分）",
            },
        ],
    })


# ══════════════════════════════════════════════════════════════════
# 谬误检测器 — _extract_assertions() + _verify_assertion()
# ══════════════════════════════════════════════════════════════════

def _mock_extract_assertions() -> str:
    return _j([
        {"assertion": "G00 是快速定位指令，用于非切削运动"},
        {"assertion": "G01 是直线插补指令，需要指定进给速度 F"},
        {"assertion": "G02 是顺时针圆弧插补指令"},
        {"assertion": "G03 是逆时针圆弧插补指令"},
        {"assertion": "车床 G99 模式下 F 单位为 mm/r"},
    ])


def _mock_verify_assertion() -> str:
    """断言验证：默认返回正确"""
    return _j({
        "verdict": "正确",
        "reason": "知识库中确认该断言与标准一致",
        "confidence": 0.9,
    })


# ══════════════════════════════════════════════════════════════════
# 交互反馈 — generate_heuristic_question() [feedback.py 直接调用]
# ══════════════════════════════════════════════════════════════════

def _mock_heuristic_question() -> str:
    return "可以想一想，G00 和 G01 指令最大的区别是什么？提示：考虑加工时是否有切屑产生，以及进给速度由谁控制。"


# ══════════════════════════════════════════════════════════════════
# 交互反馈 — grade_practical_answer() [feedback.py 直接调用]
# ══════════════════════════════════════════════════════════════════

def _mock_grade_practical() -> str:
    return _j({
        "score": 82,
        "feedback": "整体思路正确，G 代码使用基本准确。程序结构完整，包含了程序号、主轴启动、定位、切削、退刀和程序结束。建议改进：切削参数 F0.2 对于精加工偏大，可以降低到 F0.1；缺少 G28 返回参考点的安全操作。",
        "key_points": [
            "✅ 程序结构完整",
            "✅ G00/G01 使用正确",
            "⚠️ 进给速度可优化（F0.2→F0.1）",
            "⚠️ 缺少 G28 参考点返回",
        ],
    })


# ══════════════════════════════════════════════════════════════════
# 按 label 键索引的响应字典
# ══════════════════════════════════════════════════════════════════

MOCK_RESPONSES_BY_LABEL: dict[str, str] = {
    "生成讲义": _mock_lecture_notes(),
    "生成实验指导": _mock_practical_guide(),
    "生成项目案例": _mock_project_case(),
    "内容审核": _mock_content_review(),
    "学术审查": _mock_empty_issues(),
    "工业审查": _mock_empty_issues(),
    "修正生成": _mock_corrected_content(),
    "修正验证": _mock_verification_passed(),
}


# ══════════════════════════════════════════════════════════════════
# 按 prompt 子串匹配的调度表（顺序重要：越具体越靠前）
# ══════════════════════════════════════════════════════════════════

_MATCHERS: list[tuple[str, callable]] = [
    # ── Judge + Regression（必须在 challenge 之前匹配）──
    ("以下是一份关于学习内容的辩论记录", _mock_judge_verdict),
    ("验证之前发现的问题是否已被正确修复", _mock_regression_check_passed),

    # ── Debate ──
    ("审核专家对你的内容提出了以下质疑", _mock_defend_response),
    # challenge：审查专业准确性 + issues + confidence（区别于 verify 的 score）
    ("审查以下生成内容的专业准确性", _mock_challenge_issues),

    # ── Path Planner（先匹配调整后匹配规划）──
    ("调整学习路径", _mock_adjust_path),
    ("制定个性化的学习路径", _mock_plan_path),

    # ── Diagnosis ──
    ("构建详细的学习者画像", _mock_build_profile),
    ("找出学习者的知识盲区", _mock_locate_blind_spots),

    # ── Question Generator ──
    ("出题专家", _mock_questions),

    # ── Hallucination Checker ──
    ("提取所有可验证的'事实断言'", _mock_extract_assertions),
    ("验证以下断言是否与知识库内容一致", _mock_verify_assertion),

    # ── Feedback（直接 LLM 调用）──
    ("生成一个启发式追问", _mock_heuristic_question),
    ("对学习者的实操题答案进行批改评分", _mock_grade_practical),

    # ── Review.verify()（兜底：区别于 challenge 的关键词是 "逐条核验事实准确性"）──
    ("逐条核验事实准确性", _mock_content_review),
]


def match_response_by_prompt(prompt: str) -> str:
    """按 prompt 内容匹配 mock 响应。遍历 _MATCHERS，返回第一个匹配的结果。"""
    for substring, fn in _MATCHERS:
        if substring in prompt:
            return fn()
    # 兜底：返回通过的空 JSON
    return '{"passed": true, "score": 0.9, "message": "mock fallback"}'
