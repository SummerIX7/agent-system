import json
import random
from datetime import datetime

from app.agents.base import BaseAgent
from app.core.career_tracks import get_career_track_from_input, build_career_prompt


class QuestionGeneratorAgent(BaseAgent):
    """试题生成 Agent：生成选择题、判断题、实操题"""

    COMPREHENSIVE_FORMAT_VERSION = "comprehensive_case_v2"

    NODE_PRACTICE_DISTRIBUTION = {
        "multiple_choice": 4,
        "true_false": 3,
        "practical": 2,
    }

    CNC_SCENARIOS = {
        "machines": ["立式加工中心 VMC850", "数控车床 CK6140", "卧式加工中心 HMC500", "三轴铣床", "带第四轴加工中心"],
        "materials": ["45钢", "6061铝合金", "Q235钢", "304不锈钢", "POM工程塑料"],
        "sizes": ["80mm x 60mm x 20mm", "Φ50mm x 120mm", "120mm x 80mm x 30mm", "Φ32mm x 75mm", "200mm x 100mm x 15mm"],
        "tolerances": ["±0.02mm", "±0.05mm", "H7孔公差", "平面度0.03mm", "同轴度0.02mm"],
        "alarms": ["主轴过载报警", "刀库换刀异常", "X轴伺服报警", "冷却液液位不足", "程序段格式报警"],
        "inspection_tasks": ["首件外径检测", "孔径千分尺复核", "卡尺测量台阶尺寸", "百分表找正", "粗糙度目测与记录"],
        "tool_states": ["刀尖轻微磨损", "刀具悬伸偏长", "钻头排屑不畅", "端铣刀刃口崩损", "新刀首次试切"],
        "clamping": ["平口钳装夹", "三爪卡盘夹持", "压板装夹", "V形块辅助定位", "软爪夹持"],
    }

    COMPREHENSIVE_BLUEPRINTS = [
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

    def _build_scene(self) -> dict:
        scene = {key: random.choice(values) for key, values in self.CNC_SCENARIOS.items()}
        scene["seed"] = f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
        return scene

    def _build_comprehensive_blueprint(self) -> dict:
        blueprint = dict(random.choice(self.COMPREHENSIVE_BLUEPRINTS))
        blueprint["seed"] = f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
        return blueprint

    def _format_avoid_questions(self, avoid_questions: list[str] | None) -> str:
        items = [q.strip() for q in (avoid_questions or []) if q and q.strip()]
        if not items:
            return "无"
        return "\n".join(f"- {q[:160]}" for q in items[-20:])

    def _parse_json_result(self, response: str, fallback: dict) -> dict:
        text = response.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            text = text[start:end + 1]
        try:
            result = json.loads(text)
            return {**fallback, **result}
        except json.JSONDecodeError:
            return fallback

    def _node_focus_rules(self, node_title: str, node_topics: list[str] | None) -> str:
        text = f"{node_title} {' '.join(node_topics or [])}"
        rules = []
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

    def _fallback_node_question(
        self,
        question_type: str,
        index: int,
        topic: str,
        node_title: str,
        node_topics: list[str] | None,
    ) -> dict:
        focus = (node_topics or [node_title or topic])[(index - 1) % max(len(node_topics or [node_title or topic]), 1)]
        title = node_title or topic
        if question_type == "multiple_choice":
            return {
                "question": f"围绕“{title}”中的“{focus}”，现场操作前最应优先确认哪一项？",
                "question_type": "multiple_choice",
                "options": [
                    f"A. 先确认{focus}相关的工艺要求、机床状态和安全条件",
                    "B. 直接启动加工，待出现问题后再调整",
                    "C. 只查看上一班记录，不复核当前工件状态",
                    "D. 为提高效率跳过首件或程序检查",
                ],
                "correct_answer": "A",
                "explanation": f"该题考查“{title}”节点的{focus}。操作前应先确认要求、状态和风险，再执行加工或检查。",
            }
        if question_type == "true_false":
            return {
                "question": f"判断：学习“{title}”时，只要最终尺寸合格，就可以忽略“{focus}”相关的过程检查。",
                "question_type": "true_false",
                "options": ["正确", "错误"],
                "correct_answer": "错误",
                "explanation": f"过程检查是保证稳定加工和可追溯性的关键，不能因为一次结果合格就忽略{focus}。",
            }
        return {
            "question": f"简答：请写出在“{title}”节点中处理“{focus}”任务时的关键步骤和检查要点。",
            "question_type": "practical",
            "options": [],
            "correct_answer": f"应说明任务确认、机床/工件状态检查、按规范执行{focus}、记录结果、发现异常及时停机或反馈。",
            "explanation": f"评分重点是步骤完整、风险识别清楚，并能紧扣{focus}给出可执行的检查或处理方法。",
        }

    def _normalize_node_practice_questions(
        self,
        result: dict,
        topic: str,
        difficulty: str,
        track_code: str,
        node_title: str,
        node_topics: list[str] | None,
    ) -> dict:
        questions = result.get("questions", [])
        if not isinstance(questions, list):
            questions = []

        grouped = {key: [] for key in self.NODE_PRACTICE_DISTRIBUTION}
        for raw in questions:
            if not isinstance(raw, dict):
                continue
            q = dict(raw)
            qtype = q.get("question_type")
            if qtype not in grouped:
                continue
            q["topic"] = q.get("topic") or node_title or topic
            if qtype == "true_false":
                q["options"] = ["正确", "错误"]
                answer = str(q.get("correct_answer", "")).strip()
                if answer in {"对", "是", "true", "True", "TRUE"}:
                    q["correct_answer"] = "正确"
                elif answer in {"错", "否", "false", "False", "FALSE"}:
                    q["correct_answer"] = "错误"
            elif qtype == "practical":
                q["options"] = []
            elif qtype == "multiple_choice":
                options = q.get("options") or []
                if not isinstance(options, list) or len(options) < 4:
                    continue
                q["options"] = options[:4]
            grouped[qtype].append(q)

        normalized: list[dict] = []
        for qtype, need in self.NODE_PRACTICE_DISTRIBUTION.items():
            selected = grouped[qtype][:need]
            while len(selected) < need:
                selected.append(self._fallback_node_question(
                    qtype,
                    len(selected) + 1,
                    topic,
                    node_title,
                    node_topics,
                ))
            normalized.extend(selected)

        return {
            **result,
            "topic": result.get("topic", topic),
            "difficulty": result.get("difficulty", difficulty),
            "track": result.get("track", track_code),
            "questions": normalized,
        }

    async def generate_questions(
        self,
        topic: str,
        difficulty: str,
        profile: dict = None,
        count: int = 6,
        avoid_questions: list[str] | None = None,
    ) -> dict:
        """生成三种题型的试题"""
        # 从 profile 推断领域配置
        track = get_career_track_from_input(profile or {})

        # 使用领域关键词检索，避免泛化 topic 导致检索偏移
        context = self.retrieve_context(f"{track.name} {topic}")

        # 构建领域上下文 prompt
        track_prompt = build_career_prompt(track)
        scene = self._build_scene()
        avoid_text = self._format_avoid_questions(avoid_questions)

        prompt = f"""你是一位{track.name}领域的出题专家。请根据以下信息生成 {count} 道试题。

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
    "track": "{track.code}",
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

        response = await self.call_llm(prompt)
        result = self._parse_json_result(
            response,
            {"topic": topic, "difficulty": difficulty, "track": track.code, "questions": []},
        )
        result["track"] = result.get("track", track.code)
        return result

    async def generate_node_practice_questions(
        self,
        topic: str,
        difficulty: str,
        profile: dict = None,
        count: int = 9,
        avoid_questions: list[str] | None = None,
        node_title: str = "",
        node_topics: list[str] | None = None,
    ) -> dict:
        """生成单个学习节点练习：4 道选择题、3 道判断题、2 道简答题。"""
        track = get_career_track_from_input(profile or {})
        node_title = node_title or topic
        node_topics = [str(t) for t in (node_topics or []) if t]
        topic_text = f"{node_title}（{'、'.join(node_topics)}）" if node_topics else node_title
        context = self.retrieve_context(f"{track.name} {topic_text}", k=8)
        track_prompt = build_career_prompt(track)
        scene = self._build_scene()
        avoid_text = self._format_avoid_questions(avoid_questions)
        focus_rules = self._node_focus_rules(node_title, node_topics)

        prompt = f"""你是一位{track.name}领域的试题设计专家。请为一个学习节点生成 {count} 道“节点练习”题。必须严格贴合当前节点，不再区分基础练习和提升练习。

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
    "track": "{track.code}",
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

        response = await self.call_llm(prompt)
        result = self._parse_json_result(
            response,
            {"topic": topic_text, "difficulty": difficulty, "track": track.code, "questions": []},
        )
        return self._normalize_node_practice_questions(
            result=result,
            topic=topic_text,
            difficulty=difficulty,
            track_code=track.code,
            node_title=node_title,
            node_topics=node_topics,
        )

    def _fallback_comprehensive_case(self, difficulty: str, track_code: str) -> dict:
        """当模型 JSON 不完整时，提供仍可作答的单场景综合练习。"""
        scenario = {
            "title": "6061 铝合金支架首件加工与异常处置",
            "role": "你是本批次的 CNC 操机工，负责开工检查、装夹找正、程序运行确认、首件检测、异常处置和记录上报。",
            "production_task": "使用 VMC850 立式加工中心完成 20 件铝合金支架加工；首件合格并完成记录后方可批量生产。",
            "machine": "VMC850 立式加工中心",
            "controller": "FANUC 0i-MF",
            "material": "6061-T6 铝合金",
            "blank_size": "125 mm x 85 mm x 22 mm",
            "batch_size": "20 件",
            "clamping": "平口钳装夹",
            "work_coordinate": "G54",
            "drawing_requirements": [
                {"item": "长度", "requirement": "120 +/- 0.05 mm"},
                {"item": "宽度", "requirement": "80 +/- 0.05 mm"},
                {"item": "厚度", "requirement": "20 +/- 0.02 mm"},
                {"item": "孔径", "requirement": "直径 10 +0.02/0 mm"},
                {"item": "孔位置偏差", "requirement": "不超过 0.05 mm"},
            ],
            "tools": [
                "T01：直径 50 面铣刀，刀长补偿 H01",
                "T02：直径 12 立铣刀，刀长补偿 H02",
                "T03：直径 9.8 钻头，刀长补偿 H03",
                "T04：直径 10 铰刀，刀长补偿 H04",
            ],
            "program_excerpt": (
                "G90 G17 G40 G49 G80\n"
                "G54\n"
                "T01 M06\n"
                "S3200 M03\n"
                "G43 H01 Z50.\n"
                "M08\n"
                "...\n"
                "T02 M06\n"
                "S4500 M03\n"
                "G00 X20. Y20.\n"
                "G43 H01 Z50.\n"
                "G00 Z3.\n"
                "G01 Z-5. F200"
            ),
            "site_conditions": [
                "切削液浓度实测 3%，工艺要求 5%～8%",
                "平口钳定位面残留少量铝屑",
                "T02 刀刃存在轻微崩口",
                "尚未确认程序中的刀具号与刀补号是否匹配",
            ],
            "first_article_results": [
                {"item": "长度", "requirement": "120 +/- 0.05 mm", "measured": "120.03 mm"},
                {"item": "宽度", "requirement": "80 +/- 0.05 mm", "measured": "79.98 mm"},
                {"item": "厚度", "requirement": "20 +/- 0.02 mm", "measured": "20.06 mm"},
                {"item": "孔径", "requirement": "直径 10 +0.02/0 mm", "measured": "直径 9.97 mm"},
                {"item": "孔位置偏差", "requirement": "不超过 0.05 mm", "measured": "0.08 mm"},
            ],
            "runtime_symptoms": [
                "主轴负载由 45% 持续上升到 78%",
                "切削声音逐渐尖锐",
                "刀具附近出现粘屑，但机床尚未报警",
            ],
        }
        questions = [
            {
                "question": "根据开工前发现的现场状态，最合理的第一步处置是什么？",
                "question_type": "multiple_choice",
                "options": [
                    "A. 降低进给速度后直接试切",
                    "B. 先完成首件，再根据检测结果处理",
                    "C. 暂停开工，清理定位面、检查或更换 T02、调整切削液并核对刀补",
                    "D. 只处理切削液，其他问题在加工中观察",
                ],
                "correct_answer": "C",
                "explanation": "定位污染、刀具损伤、切削液浓度不足和刀补未确认均会直接影响安全与首件质量，应在启动加工前形成闭环。",
            },
            {
                "question": "程序执行到 T02 工序前，最需要优先修正或确认的风险是什么？",
                "question_type": "multiple_choice",
                "options": [
                    "A. G54 必须改为 G55",
                    "B. T02 后使用了 H01，应核对并改为与 T02 对应的 H02",
                    "C. 主轴转速 4500 r/min 必须统一改为 3200 r/min",
                    "D. Z 轴安全高度必须固定为 100 mm",
                ],
                "correct_answer": "B",
                "explanation": "T02 的刀长补偿应与刀具表中的 H02 对应。错误调用 H01 可能造成 Z 向尺寸错误甚至碰撞。",
            },
            {
                "question": "请按实际生产顺序写出从班前检查到首件试切前的操作流程，必须包含安全检查、装夹找正、对刀和 G54 确认。",
                "question_type": "practical",
                "options": [],
                "correct_answer": "确认生产文件和机床状态；检查防护、急停、润滑、气压和切削液；清洁定位面并检查毛坯；检查并正确装夹刀具；按基准装夹找正工件；完成对刀并核对刀长补偿；建立和复核 G54；空运行、单段和低倍率检查程序后再试切。",
                "explanation": "评分点：生产文件与安全点检、定位面清洁、装夹找正、刀具与补偿核对、G54 复核、空运行/单段验证。安全红线：未确认刀补和安全高度不得直接自动运行。",
            },
            {
                "question": "根据首件实测数据判断合格项和超差项，分析厚度、孔径及孔位置偏差的可能原因，并给出调整与复检方法。",
                "question_type": "practical",
                "options": [],
                "correct_answer": "长度和宽度合格；厚度、孔径和孔位置偏差不合格。应分别复核量具与测量方法、装夹和基准、G54 坐标、刀具磨损及刀补调用。厚度应确认面铣刀补偿后按超差方向小量修正；孔径应检查钻铰刀状态、余量和刀具尺寸；孔位置应复核找正、G54 和程序坐标。调整后重新加工或按规定处置首件，并对全部关键尺寸复检记录。",
                "explanation": "评分点：上下限计算、合格判定、厚度原因与调整、孔径原因与处理、孔位置基准链分析、调整后的完整复检。安全红线：不得仅凭单项修正直接放行整批。",
            },
            {
                "question": "面对主轴负载持续升高、声音尖锐和粘屑现象，请说明停机处置、检查恢复、验证加工以及允许批量放行的条件。",
                "question_type": "practical",
                "options": [],
                "correct_answer": "立即暂停进给并安全停机，禁止徒手清屑；检查刀具崩损和粘刀、切削液浓度与流量、排屑、装夹和切削参数；排除原因并更换或修整刀具，重新确认刀补；采用单段或低倍率试运行；重新加工首件并完成全尺寸复检；只有异常消除、程序和补偿确认、首件合格且记录完成后才能批量放行。",
                "explanation": "评分点：安全停机、禁止徒手清屑、刀具/冷却/参数检查、恢复前补偿复核、低风险验证、首件全检与记录。安全红线：异常原因未查清或首件未合格不得继续批量加工。",
            },
        ]
        return {
            "format_version": self.COMPREHENSIVE_FORMAT_VERSION,
            "topic": "最终综合练习：真实业务场景",
            "difficulty": difficulty,
            "track": track_code,
            "scenario": scenario,
            "questions": questions,
        }

    def _normalize_comprehensive_case(self, result: dict, difficulty: str, track_code: str) -> dict:
        """强制综合练习为一个场景、2 道选择题和 3 道简答题。"""
        fallback = self._fallback_comprehensive_case(difficulty, track_code)
        scenario = result.get("scenario")
        if not self._comprehensive_case_is_coherent(scenario):
            return fallback

        raw_questions = result.get("questions", [])
        if not isinstance(raw_questions, list):
            raw_questions = []
        if not self._comprehensive_questions_are_coherent(raw_questions, scenario):
            return fallback
        grouped = {"multiple_choice": [], "practical": []}
        for raw in raw_questions:
            if not isinstance(raw, dict):
                continue
            question = dict(raw)
            qtype = question.get("question_type")
            if qtype not in grouped or not str(question.get("question", "")).strip():
                continue
            if qtype == "multiple_choice":
                options = question.get("options")
                answer = str(question.get("correct_answer", "")).strip().upper()
                if not isinstance(options, list) or len(options) < 4 or answer not in {"A", "B", "C", "D"}:
                    continue
                question["options"] = options[:4]
                question["correct_answer"] = answer
            else:
                question["options"] = []
            question["topic"] = "最终综合练习：真实业务场景"
            grouped[qtype].append(question)

        normalized = grouped["multiple_choice"][:2]
        while len(normalized) < 2:
            normalized.append(fallback["questions"][len(normalized)])

        practical = grouped["practical"][:3]
        while len(practical) < 3:
            practical.append(fallback["questions"][2 + len(practical)])
        normalized.extend(practical)

        return {
            **result,
            "format_version": self.COMPREHENSIVE_FORMAT_VERSION,
            "topic": "最终综合练习：真实业务场景",
            "difficulty": result.get("difficulty", difficulty),
            "track": result.get("track", track_code),
            "scenario": scenario,
            "questions": normalized,
        }

    def _comprehensive_case_is_coherent(self, scenario: object) -> bool:
        """拦截最常见的车/铣场景串线以及缺少关键资料的结果。"""
        if not isinstance(scenario, dict):
            return False
        required = [
            "title", "role", "production_task", "machine", "controller", "material",
            "blank_size", "batch_size", "clamping", "work_coordinate",
            "drawing_requirements", "tools", "program_excerpt", "site_conditions",
            "first_article_results", "runtime_symptoms",
        ]
        if any(not scenario.get(key) for key in required):
            return False
        if len(scenario.get("drawing_requirements", [])) < 3:
            return False
        if len(scenario.get("first_article_results", [])) < 3:
            return False

        machine = str(scenario.get("machine", ""))
        clamping = str(scenario.get("clamping", ""))
        program = str(scenario.get("program_excerpt", "")).upper()
        text = f"{machine} {clamping} {program}"
        is_milling = "加工中心" in machine or "铣" in machine
        is_turning = "车床" in machine
        if is_milling:
            if any(token in text for token in ["三爪卡盘", "G96", "T0101", "外圆精车"]):
                return False
            if "G43" not in program or "M06" not in program:
                return False
        elif is_turning:
            if any(token in text for token in ["平口钳", "G43", " M06", "H01", "H02"]):
                return False
            if "三爪" not in clamping and "软爪" not in clamping:
                return False
        else:
            return False
        return True

    def _comprehensive_questions_are_coherent(self, questions: list, scenario: dict) -> bool:
        """对模型容易犯的模式/补偿概念错误做最终拦截。"""
        if len(questions) < 5:
            return False
        types = [q.get("question_type") for q in questions if isinstance(q, dict)]
        if types[:5] != ["multiple_choice", "multiple_choice", "practical", "practical", "practical"]:
            return False
        answers = "\n".join(
            f"{q.get('question', '')}\n{q.get('correct_answer', '')}\n{q.get('explanation', '')}"
            for q in questions if isinstance(q, dict)
        )
        if "MDI" in answers and any(word in answers for word in ["图形模拟", "空运行", "单段运行", "运行当前程序段"]):
            return False

        machine = str(scenario.get("machine", ""))
        program = str(scenario.get("program_excerpt", "")).upper()
        q2 = questions[1] if len(questions) > 1 and isinstance(questions[1], dict) else {}
        q2_answer = str(q2.get("correct_answer", "")).strip().upper()
        q2_options = q2.get("options", []) if isinstance(q2.get("options"), list) else []
        q2_index = ord(q2_answer) - ord("A") if q2_answer in {"A", "B", "C", "D"} else -1
        q2_correct_text = q2_options[q2_index] if 0 <= q2_index < len(q2_options) else ""
        q2_evidence = f"{q2_correct_text} {q2.get('explanation', '')}".upper()
        if "加工中心" in machine or "铣" in machine:
            if not all(token in program for token in ["T02", "H01"]):
                return False
            if not all(token in q2_evidence for token in ["H01", "H02"]):
                return False
            # 刀长补偿 H 只控制刀轴方向，不能拿来修正 XY 外形宽度/孔位置。
            dimensional_answer = str(questions[3].get("correct_answer", "")) if len(questions) > 3 else ""
            if any(word in dimensional_answer for word in ["宽度", "长度", "孔位置"]):
                if any(token in dimensional_answer for token in ["H01", "H02", "H03", "刀长补偿"]):
                    return False
        elif "车床" in machine:
            if "G96" not in program or "G50" in program:
                return False
            if "G50" not in q2_evidence or not any(word in q2_evidence for word in ["最高", "限速", "限制"]):
                return False
        return True

    async def generate_comprehensive_questions(
        self,
        topics: list[str],
        difficulty: str,
        profile: dict = None,
        count: int = 5,
        avoid_questions: list[str] | None = None,
    ) -> dict:
        """生成最终综合练习：一个共享生产场景下的 2 道选择题和 3 道简答题。"""
        track = get_career_track_from_input(profile or {})
        topic_text = "、".join([t for t in topics if t]) or f"{track.name}综合实践"
        context = self.retrieve_context(f"{track.name} 综合实践 {topic_text}", k=8)
        track_prompt = build_career_prompt(track)
        blueprint = self._build_comprehensive_blueprint()
        avoid_text = self._format_avoid_questions(avoid_questions)

        prompt = f"""你是一位同时具备 CNC 车间生产经验、职业教育课程设计经验和实操考评经验的{track.name}训练专家。

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
2. 学员身份是“{track.name}”。内容必须在该岗位可观察、可判断、可执行或可上报的职责边界内，不要求其承担超出岗位权限的工艺审批或复杂程序开发。
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
    "format_version": "{self.COMPREHENSIVE_FORMAT_VERSION}",
    "topic": "最终综合练习：真实业务场景",
    "difficulty": "{difficulty}",
    "track": "{track.code}",
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

        response = await self.call_llm(prompt)
        fallback = self._fallback_comprehensive_case(difficulty, track.code)
        result = self._parse_json_result(
            response,
            fallback,
        )
        return self._normalize_comprehensive_case(result, difficulty, track.code)

    async def run(self, topic: str = "", difficulty: str = "beginner", profile: dict = None, **kwargs) -> dict:
        return await self.generate_questions(topic, difficulty, profile, **kwargs)
