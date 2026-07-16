"""解析 LLM JSON 输出、规范化题目、拦截明显不一致的场景。"""
from __future__ import annotations

import json

from app.agents.question_data.fallbacks import (
    fallback_comprehensive_case,
    fallback_node_question,
)
from app.agents.question_data.scenarios import (
    COMPREHENSIVE_FORMAT_VERSION,
    NODE_PRACTICE_DISTRIBUTION,
)


def parse_json_result(response: str, fallback: dict) -> dict:
    """
    从 LLM 响应中抽取 JSON，剥去 ```json``` 包裹。
    解析失败则返回 fallback。
    """
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


def normalize_node_practice_questions(
    result: dict,
    topic: str,
    difficulty: str,
    track_code: str,
    node_title: str,
    node_topics: list[str] | None,
) -> dict:
    """强制节点练习为 4 选 / 3 判 / 2 简答；不合规部分用 fallback 补足。"""
    questions = result.get("questions", [])
    if not isinstance(questions, list):
        questions = []

    grouped: dict[str, list[dict]] = {key: [] for key in NODE_PRACTICE_DISTRIBUTION}
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
    for qtype, need in NODE_PRACTICE_DISTRIBUTION.items():
        selected = grouped[qtype][:need]
        while len(selected) < need:
            selected.append(fallback_node_question(
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


def comprehensive_case_is_coherent(scenario: object) -> bool:
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


def comprehensive_questions_are_coherent(questions: list, scenario: dict) -> bool:
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


def normalize_comprehensive_case(result: dict, difficulty: str, track_code: str) -> dict:
    """强制综合练习为一个场景、2 道选择题和 3 道简答题。"""
    fallback = fallback_comprehensive_case(difficulty, track_code)
    scenario = result.get("scenario")
    if not comprehensive_case_is_coherent(scenario):
        return fallback

    raw_questions = result.get("questions", [])
    if not isinstance(raw_questions, list):
        raw_questions = []
    if not comprehensive_questions_are_coherent(raw_questions, scenario):
        return fallback
    grouped: dict[str, list[dict]] = {"multiple_choice": [], "practical": []}
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
        "format_version": COMPREHENSIVE_FORMAT_VERSION,
        "topic": "最终综合练习：真实业务场景",
        "difficulty": result.get("difficulty", difficulty),
        "track": result.get("track", track_code),
        "scenario": scenario,
        "questions": normalized,
    }
