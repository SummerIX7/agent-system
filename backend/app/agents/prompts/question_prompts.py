"""试题生成使用的 Prompt 模板。"""
from __future__ import annotations

from app.agents.question_data.scenarios import COMPREHENSIVE_FORMAT_VERSION


def build_basic_prompt(
    *,
    track_name: str,
    track_code: str,
    track_prompt: str,
    topic: str,
    difficulty: str,
    context: str,
    scene: dict,
    avoid_text: str,
    count: int,
) -> str:
    """通用出题 prompt：三题型混合。"""
    return f"""你是一位{track_name}领域的出题专家。请根据以下信息生成 {count} 道试题。

{track_prompt}

[主题] {topic}
[难度] {difficulty}
[知识库参考] {context}

[本次随机业务场景]
- 机床：{scene["machines"]}
- 材料：{scene["materials"]}
- 工件尺寸：{scene["sizes"]}
- 公差/质量要求：{scene["tolerances"]}
- 可能报警：{scene["alarms"]}
- 检测任务：{scene["inspection_tasks"]}
- 刀具状态：{scene["tool_states"]}
- 装夹方式：{scene["clamping"]}
- 随机批次：{scene["seed"]}

[需要避开的历史题干]
{avoid_text}

[要求]
生成以下三种题型，每种至少 2 道：
1. 选择题（multiple_choice）：4 选 1，考察领域知识点
2. 判断题（true_false）：对/错，考察领域概念辨析
3. 实操题（practical）：描述领域操作步骤或编程思路
4. 每道题必须嵌入具体业务场景，避免抽象泛问。
5. 不得复用历史题干中的题型组合、数字、报警、材料、答案表达或解析结构。

输出 JSON 格式：
{{
    "topic": "{topic}",
    "difficulty": "{difficulty}",
    "track": "{track_code}",
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
            "correct_answer": "参考操作步骤",
            "explanation": "评分标准和要点"
        }}
    ]
}}

只输出 JSON，不要其他文字。"""


def build_node_practice_prompt(
    *,
    track_name: str,
    track_code: str,
    track_prompt: str,
    node_title: str,
    topic_text: str,
    difficulty: str,
    context: str,
    scene: dict,
    focus_rules: str,
    avoid_text: str,
    count: int,
) -> str:
    """单节点练习 prompt：固定 4 选 / 3 判 / 2 简答。"""
    return f"""你是一位{track_name}领域的试题设计专家。请为一个学习节点生成 {count} 道“节点练习”题。必须严格贴合当前节点，不再区分基础练习和提升练习。

{track_prompt}

[节点标题] {node_title}
[节点知识点] {topic_text}
[难度] {difficulty}
[知识库参考] {context}

[本次随机业务场景变量]
- 机床：{scene["machines"]}
- 材料：{scene["materials"]}
- 工件尺寸：{scene["sizes"]}
- 公差/质量要求：{scene["tolerances"]}
- 可能报警：{scene["alarms"]}
- 检测任务：{scene["inspection_tasks"]}
- 刀具状态：{scene["tool_states"]}
- 装夹方式：{scene["clamping"]}
- 随机批次：{scene["seed"]}

[当前节点主题边界]
{focus_rules}

[需要避开的历史题干]
{avoid_text}

[硬性要求]
1. 严格生成 9 道题，顺序为：前 4 道 multiple_choice，接着 3 道 true_false，最后 2 道 practical。
2. multiple_choice 必须是 4 选 1，correct_answer 只能是 A/B/C/D。
3. true_false 的 options 必须是 ["正确", "错误"]，correct_answer 只能是 "正确" 或 "错误"。
4. practical 在前端展示为“简答题”，题目应要求学员写出判断依据、操作步骤或风险处理，不要写成开放闲聊题。
5. 每道题的核心考点必须命中“节点标题”或“节点知识点”中的至少一个关键词；随机场景变量只作为背景，不能把题目带偏到其他节点。
6. 不得复用历史题干中的题型组合、数字、报警、材料、答案表达或解析结构。

输出 JSON 格式：
{{
    "topic": "{topic_text}",
    "difficulty": "{difficulty}",
    "track": "{track_code}",
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
            "question": "简答题内容",
            "question_type": "practical",
            "options": [],
            "correct_answer": "参考答案要点",
            "explanation": "评分标准和关键风险点"
        }}
    ]
}}

只输出 JSON，不要其他文字。"""


def build_comprehensive_prompt(
    *,
    track_name: str,
    track_code: str,
    track_prompt: str,
    topic_text: str,
    difficulty: str,
    context: str,
    blueprint: dict,
    avoid_text: str,
) -> str:
    """最终综合练习 prompt：一个连续场景 + 2 选 3 简答。"""
    return f"""你是一位同时具备 CNC 车间生产经验、职业教育课程设计经验和实操考评经验的{track_name}训练专家。

请设计一套“最终综合练习”。它不是 5 个互不相关的小场景，而是一个完整、连续、可执行的真实生产任务。先给出一次性的生产场景资料，再基于同一场景生成严格 5 道关联题：前 2 道选择题，后 3 道简答题。

{track_prompt}

[覆盖主题]
{topic_text}

[难度] {difficulty}
[知识库参考] {context}

[本次场景蓝图：必须完整遵守，不得跨机床类型拼接]
- 场景家族：{blueprint["family"]}
- 机床：{blueprint["machine"]}
- 数控系统：{blueprint["controller"]}
- 合适工件：{blueprint["workpiece"]}
- 可选材料：{blueprint["materials"]}
- 装夹约束：{blueprint["clamping"]}
- 坐标系约束：{blueprint["coordinate"]}
- 程序约束：{blueprint["program_rules"]}
- 唯一程序风险：{blueprint["risk_pattern"]}
- 明确禁止：{blueprint["forbidden"]}
- 量具约束：{blueprint["measurement"]}
- 随机批次：{blueprint["seed"]}

[需要避开的历史题干]
{avoid_text}

[场景设计硬性要求]
1. 只设计一个生产订单、一个工件、同一台机床和一条连续时间线；5 道题必须全部依托这个场景，题干不得另起新场景。
2. 学员身份是“{track_name}”。内容必须在该岗位可观察、可判断、可执行或可上报的职责边界内，不要求其承担超出岗位权限的工艺审批或复杂程序开发。
3. 场景必须包含：生产任务、机床及系统、材料与毛坯、批量、装夹方式、工件坐标系、图纸/质量要求、刀具信息、关键程序片段、开工前现场状态、首件实测数据、加工中异常现象。
4. 所有数据必须内在一致：机床与装夹匹配，刀具与工序匹配，尺寸上下限可计算，实测数据中既有合格项也有超差项，程序片段至少包含一个能够被识别的真实风险点。
5. 异常必须形成因果链，不能堆砌互不相关的报警。应让学员完成“开工判断 → 装夹/坐标/程序确认 → 首件检测与偏差调整 → 运行异常处置 → 复检与批量放行”的闭环。
6. 不得在问题中补充场景没有提供的新机床、新材料、新尺寸或新故障。场景资料只展示一次，问题只引用资料。
7. 不得照抄知识库原文；不得复用历史题干中的数字组合、异常组合、答案表达或解析结构。
8. 每个尺寸要求必须同时写清“名义尺寸”和“允许区间”，例如“20 +/- 0.02 mm（合格区间 19.98～20.02 mm）”；生成首件实测值后必须先自行逐项验算，再在第 4 题参考答案中给出同样的合格判定，禁止把偏大写成偏小或混淆上下极限。
9. 程序风险点只能设置一个主要错误，且必须与场景家族一致。除该风险点外，其余程序段应基本可运行，避免让学员面对无法判断的错误堆叠。
   本次必须使用蓝图中指定的“唯一程序风险”，第 2 题正确选项和解析必须准确指出该风险，不得自行改成其他风险。
10. 安全处置必须符合现场层级：普通负载升高、异响或粘屑先使用进给保持/循环停止并受控停主轴；只有碰撞、人员危险或运动失控等紧急情况才使用急停。禁止要求徒手清屑。
11. 空运行应使用图形模拟、机床锁定、空运行、单段和进给倍率等受控方式，不得描述为“在 MDI 中运行整段自动程序”。
12. 补偿逻辑必须正确：加工中心的 H 刀长补偿主要影响刀轴/Z 向尺寸，D 半径/磨损补偿或经授权的刀路坐标影响 XY 轮廓；不得用 H 补偿修正宽度或孔位置。车床 X 向磨损补偿影响直径，Z 向补偿影响轴向尺寸。
13. G54 是共同基准，不得为了修正某一个局部特征随意改动整个坐标系；先复核测量、装夹、刀具、补偿和程序，再按岗位权限调整或上报。
14. “孔中心坐标偏差”和“位置度公差”必须区分。没有基准体系和位置度检测条件时，使用明确的孔中心坐标及允许区间，不要把线性坐标值写成位置度。
15. 第 4 题参考答案必须逐项列出：允许下限、允许上限、实测值、合格结论、偏差方向、可能原因、岗位权限内的调整动作、复检量具与方法。

[输出前强制自检]
- 逐行检查机床、系统、装夹、刀具格式和 G/M 指令是否属于同一车削或铣削体系。
- 重新计算所有尺寸上下限，确认场景表格与第 4 题答案完全一致。
- 检查程序风险只有一个主要风险点，且第 2 题正确答案准确命中该风险。
- 检查 5 道题没有引入场景外的新设备、新材料、新尺寸或新异常。
- 检查普通加工异常没有滥用急停，检查所有清屑动作都要求机床完全停止并使用工具。
- 检查答案没有使用 MDI 运行整段程序，也没有混淆 H、D、G54 和车床 X/Z 补偿作用。
- 任一项不通过时，先在内部修正，再输出最终 JSON；不要输出自检过程。

[5 道题结构]
1. 第 1 题必须是 multiple_choice：考查开工前面对多项现场状态时的优先处置，4 选 1。
2. 第 2 题必须是 multiple_choice：考查关键程序段、刀补号、坐标系或运行方式中的主要风险，4 选 1。
3. 第 3 题必须是 practical：要求写出开机检查、装夹找正、对刀和工件坐标确认的完整操作顺序。
4. 第 4 题必须是 practical：要求依据同一份首件数据判定合格/超差项目，分析原因并给出调整与复检方法。
5. 第 5 题必须是 practical：要求处置加工中异常，说明停机、检查、恢复、验证和批量放行条件。
6. 两道选择题必须只有一个明确正确答案，干扰项要像真实现场中的错误操作，不能使用明显荒谬的选项。
7. 三道简答题的 correct_answer 必须是可执行的分步参考答案；explanation 必须给出 4～6 个评分点及关键安全红线。
8. 最终必须严格输出 5 道题，顺序为 2 道 multiple_choice、3 道 practical，不生成判断题。

输出 JSON 格式：
{{
    "format_version": "{COMPREHENSIVE_FORMAT_VERSION}",
    "topic": "最终综合练习：真实业务场景",
    "difficulty": "{difficulty}",
    "track": "{track_code}",
    "scenario": {{
        "title": "生产任务标题",
        "role": "学员在本任务中的岗位身份与职责",
        "production_task": "订单背景和需要完成的生产目标",
        "machine": "机床型号",
        "controller": "数控系统",
        "material": "材料",
        "blank_size": "毛坯尺寸",
        "batch_size": "批量",
        "clamping": "装夹方式",
        "work_coordinate": "工件坐标系",
        "drawing_requirements": [
            {{"item": "检测项目", "requirement": "图纸或工艺要求"}}
        ],
        "tools": ["T01：刀具名称、用途和对应刀补号"],
        "program_excerpt": "关键 NC 程序片段，使用换行符组织",
        "site_conditions": ["开工前发现的现场状态"],
        "first_article_results": [
            {{"item": "检测项目", "requirement": "要求", "measured": "实测值"}}
        ],
        "runtime_symptoms": ["加工中观察到的连续异常现象"]
    }},
    "questions": [
        {{
            "question": "基于上述场景的第1个决策问题，不重复粘贴场景",
            "question_type": "multiple_choice",
            "options": ["A. 选项1", "B. 选项2", "C. 选项3", "D. 选项4"],
            "correct_answer": "A",
            "explanation": "解析说明"
        }},
        {{
            "question": "基于上述场景的简答任务，不另起新场景",
            "question_type": "practical",
            "options": [],
            "correct_answer": "分步骤参考操作方案",
            "explanation": "评分点：①...；②...；关键安全红线：..."
        }}
    ]
}}

只输出一个合法 JSON 对象，不要 Markdown 代码围栏，不要输出任何解释性文字。JSON 字符串中的程序换行必须正确转义。"""
