"""模型 JSON 不完整或不合规时的兜底题目。"""
from __future__ import annotations

from app.agents.question_data.scenarios import COMPREHENSIVE_FORMAT_VERSION


def fallback_node_question(
    question_type: str,
    index: int,
    topic: str,
    node_title: str,
    node_topics: list[str] | None,
) -> dict:
    """节点练习单题兜底：按题型返回一个可作答的默认题。"""
    focus_list = node_topics or [node_title or topic]
    focus = focus_list[(index - 1) % max(len(focus_list), 1)]
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


def fallback_comprehensive_case(difficulty: str, track_code: str) -> dict:
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
        "format_version": COMPREHENSIVE_FORMAT_VERSION,
        "topic": "最终综合练习：真实业务场景",
        "difficulty": difficulty,
        "track": track_code,
        "scenario": scenario,
        "questions": questions,
    }
