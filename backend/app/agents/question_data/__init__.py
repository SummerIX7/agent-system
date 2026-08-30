"""``app.agents.question_data`` —— 试题生成的数据与规则子包。"""
from app.agents.question_data.fallbacks import (
    fallback_comprehensive_case,
    fallback_node_question,
)
from app.agents.question_data.scenarios import (
    CNC_SCENARIOS,
    COMPREHENSIVE_BLUEPRINTS,
    COMPREHENSIVE_FORMAT_VERSION,
    NODE_PRACTICE_DISTRIBUTION,
    build_comprehensive_blueprint,
    build_scene,
    format_avoid_questions,
    node_focus_rules,
)
from app.agents.question_data.validators import (
    comprehensive_case_is_coherent,
    comprehensive_questions_are_coherent,
    normalize_comprehensive_case,
    normalize_node_practice_questions,
    parse_json_result,
)

__all__ = [
    "CNC_SCENARIOS",
    "COMPREHENSIVE_BLUEPRINTS",
    "COMPREHENSIVE_FORMAT_VERSION",
    "NODE_PRACTICE_DISTRIBUTION",
    "build_comprehensive_blueprint",
    "build_scene",
    "comprehensive_case_is_coherent",
    "comprehensive_questions_are_coherent",
    "fallback_comprehensive_case",
    "fallback_node_question",
    "format_avoid_questions",
    "node_focus_rules",
    "normalize_comprehensive_case",
    "normalize_node_practice_questions",
    "parse_json_result",
]
